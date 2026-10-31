"""采集存储水位与最旧数据淘汰；不执行 OPTIMIZE TABLE 或修改服务器配额。"""

import json
import logging
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import DateTime, Integer, LargeBinary, cast, delete, func, select, text
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    CreationCard,
    KnowledgeCitation,
    KnowledgeTopic,
    PersonalItem,
    Ranking,
    Run,
    Snapshot,
)
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
LOCK_NAME = "aihot.storage"


class StorageLimitError(RuntimeError):
    pass


def table_size(session: Session, table, *conditions) -> int:
    row_bytes = 128 + 64 * (len(table.indexes) + len(table.constraints))
    for column in table.columns:
        if isinstance(column.type, (Integer, DateTime)):
            row_bytes += 8
        else:
            row_bytes += func.coalesce(func.length(cast(column, LargeBinary)), 0)
    query = select(func.coalesce(func.sum(row_bytes), 0)).select_from(table).where(*conditions)
    return int(session.scalar(query))


def estimated_size(session: Session) -> int:
    """按实际 UTF-8 字节及行/索引开销估算；DELETE 后立刻减少，避免统计延迟导致过度清理。"""
    return sum(table_size(session, table) for table in Base.metadata.sorted_tables)


def incoming_size(records) -> int:
    """为整批新增数据保守预留空间，覆盖 README、派生字段和索引；不记录内容。"""
    return (
        len(json.dumps(records, ensure_ascii=False, default=str).encode("utf-8")) * 3
        + len(records) * 4096
    )


def storage_status(session: Session, settings) -> dict:
    used = estimated_size(session)
    limit = int(settings.database_max_size_gb * 1_000_000_000)
    return {
        "used_bytes": used,
        "limit_bytes": limit,
        "cleanup_target_bytes": int(limit * settings.database_cleanup_target_ratio),
        "usage_percent": round(used / limit * 100, 2),
        "over_limit": used >= limit,
        "measurement": "estimated_live_data",
    }


def delete_oldest(session: Session) -> dict | None:
    """按采集时间比较最旧选题和完整批次；每次删除有界，外键按子表优先。"""
    # 保护每个项目最新资料，收藏时永远能找到原项目；保留最近两期榜单及增长基线。
    latest_snapshots = select(func.max(Snapshot.id)).group_by(Snapshot.repo_id)
    protected_runs = select(Snapshot.run_id).where(Snapshot.id.in_(latest_snapshots))
    recent_runs = list(
        session.scalars(
            select(Run.id)
            .where(Run.status == "success")
            .order_by(Run.slot.desc(), Run.id.desc())
            .limit(2)
        )
    )
    run = session.scalar(
        select(Run)
        .where(
            Run.status != "running",
            Run.started_at < utcnow() - timedelta(hours=26),
            Run.id.not_in(protected_runs),
            Run.id.not_in(recent_runs),
        )
        .order_by(Run.started_at, Run.id)
        .limit(1)
        .with_for_update()
    )
    from app.models import HotListSnapshot

    hot_topic_ids = [
        item["id"]
        for snapshot in session.scalars(select(HotListSnapshot))
        for item in snapshot.entries
        if item.get("id")
    ]
    protected_topics = select(PersonalItem.target_id).where(PersonalItem.target_kind == "topic")
    newest_topic = select(func.max(KnowledgeTopic.id))
    topic = session.scalar(
        select(KnowledgeTopic)
        .where(
            KnowledgeTopic.id.not_in(protected_topics),
            KnowledgeTopic.id.not_in(hot_topic_ids),
            KnowledgeTopic.id.not_in(select(CreationCard.topic_id)),
            KnowledgeTopic.id != newest_topic.scalar_subquery(),
        )
        .order_by(KnowledgeTopic.collected_at, KnowledgeTopic.id)
        .limit(1)
        .with_for_update()
    )
    if run and (not topic or run.started_at <= topic.collected_at):
        count = session.scalar(
            select(func.count()).select_from(Snapshot).where(Snapshot.run_id == run.id)
        )
        freed = sum(
            table_size(session, model.__table__, condition)
            for model, condition in (
                (Run, Run.id == run.id),
                (Snapshot, Snapshot.run_id == run.id),
                (Ranking, Ranking.run_id == run.id),
            )
        )
        session.execute(delete(Ranking).where(Ranking.run_id == run.id))
        session.execute(delete(Snapshot).where(Snapshot.run_id == run.id))
        session.delete(run)
        return {"runs": 1, "snapshots": count, "topics": 0, "bytes": freed}
    if topic:
        # 写备注/创建卡片也先锁定选题行；锁后用当前读重新检查，避免并发产生悬空引用。
        personal = session.scalar(
            select(PersonalItem.id)
            .where(
                PersonalItem.target_kind == "topic",
                PersonalItem.target_id == topic.id,
            )
            .with_for_update()
        )
        card = session.scalar(
            select(CreationCard.id).where(CreationCard.topic_id == topic.id).with_for_update()
        )
        if personal is not None or card is not None:
            return {"runs": 0, "snapshots": 0, "topics": 0, "bytes": 0}
        freed = table_size(session, KnowledgeTopic.__table__, KnowledgeTopic.id == topic.id)
        freed += table_size(
            session, KnowledgeCitation.__table__, KnowledgeCitation.topic_id == topic.id
        )
        session.execute(delete(KnowledgeCitation).where(KnowledgeCitation.topic_id == topic.id))
        session.delete(topic)
        return {"runs": 0, "snapshots": 0, "topics": 1, "bytes": freed}
    return None


def ensure_capacity(engine, settings, reserve_bytes=0):
    """调用方持有跨进程存储锁；分次提交清理，单次写入前确认空间充足。"""
    limit = int(settings.database_max_size_gb * 1_000_000_000)
    if reserve_bytes >= limit:
        raise StorageLimitError(
            "本次采集数据超过数据库存储上限，请提高 DATABASE_MAX_SIZE_GB 或缩小采集量"
        )
    with Session(engine) as session:
        before = estimated_size(session)
    if before + reserve_bytes < limit:
        return
    target = min(int(limit * settings.database_cleanup_target_ratio), limit - reserve_bytes - 1)
    deleted = {"runs": 0, "snapshots": 0, "topics": 0, "bytes": 0}
    used = before
    logger.warning(
        "数据库达到清理阈值：估算=%s字节，上限=%s字节，预留=%s字节，目标=%s字节",
        before,
        limit,
        reserve_bytes,
        target,
    )
    # 有界执行：一轮最多清理 1000 个批次/选题，避免长时间占用数据库。
    for _ in range(1000):
        with Session(engine) as session, session.begin():
            counts = delete_oldest(session)
        if counts is None:
            break
        for key, value in counts.items():
            deleted[key] += value
        used -= counts["bytes"]
        if used <= target:
            break
    with Session(engine) as session:
        used = estimated_size(session)
    logger.warning(
        "存储清理结束：清理前=%s字节，清理后=%s字节，删除批次=%s，快照=%s，选题=%s",
        before,
        used,
        deleted["runs"],
        deleted["snapshots"],
        deleted["topics"],
    )
    if used + reserve_bytes >= limit:
        raise StorageLimitError(
            "自动清理后空间仍不足：已保护个人资料和近期榜单，或已达到单轮清理上限；本轮停止采集，下次任务继续检查，也可提高 DATABASE_MAX_SIZE_GB"
        )


@contextmanager
def storage_guard(engine, settings, reserve_bytes=0):
    """两个 worker 的容量检查、清理与写入串行；只锁写入阶段，不锁网络请求。"""
    with engine.connect() as connection:
        mysql = engine.dialect.name == "mysql"
        if (
            mysql
            and connection.scalar(text("SELECT GET_LOCK(:name, 30)"), {"name": LOCK_NAME}) != 1
        ):
            raise StorageLimitError("等待存储管理锁超时，本轮停止写入")
        try:
            ensure_capacity(engine, settings, reserve_bytes)
            yield
        finally:
            if mysql:
                connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK_NAME})
