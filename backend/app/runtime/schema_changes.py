"""串行化初始化与迁移，并仅重试已知的并发 DDL 元数据错误。"""

import hashlib
import logging
import time

from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

logger = logging.getLogger(__name__)


def _run_with_retry(operation):
    for attempt in range(4):
        try:
            return operation()
        except DBAPIError as exc:
            code = exc.orig.args[0] if exc.orig.args else None
            if code == 1205:
                raise RuntimeError(
                    "数据库锁等待超过会话上限，迁移已停止，避免继续阻塞线上请求。"
                    "请先结束持有锁的旧事务（提交、回滚或关闭对应连接），再执行 make migrate；"
                    "仅重复迁移不会释放其它连接持有的锁。"
                ) from exc
            if code != 1684 or attempt == 3:
                raise
            delay = 2**attempt
            logger.warning("检测到并发 DDL（1684），%s 秒后重试数据库升级", delay)
            time.sleep(delay)


def run_schema_change(engine, operation):
    """同一数据库的所有项目 DDL 入口使用同名连接级锁；其它错误原样抛出。"""
    if engine.dialect.name != "mysql":
        return operation()
    database = engine.url.database or ""
    lock_name = "aihot.schema." + hashlib.sha256(database.encode()).hexdigest()[:32]
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT GET_LOCK(:name, 10)"), {"name": lock_name})
        if acquired != 1:
            raise RuntimeError("另一个数据库初始化或迁移正在执行，请等待完成后重试 make migrate。")
        try:
            return _run_with_retry(operation)
        finally:
            try:
                connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})
            except DBAPIError:
                # 不能把仍持有命名锁的连接放回池；断开连接由 MySQL 释放锁。
                connection.invalidate()
                logger.warning("迁移锁连接失效，已丢弃连接")


def create_missing_tables(engine, metadata):
    """项目只使用持久表；枚举表名避免 DESCRIBE 在排队 DDL 上失败。"""
    if engine.dialect.name != "mysql":
        return metadata.create_all(engine)
    inspector = inspect(engine)
    existing = set(inspector.get_table_names()) | set(inspector.get_view_names())
    missing = [table for table in metadata.sorted_tables if table.name not in existing]
    if missing:
        metadata.create_all(engine, tables=missing, checkfirst=False)
