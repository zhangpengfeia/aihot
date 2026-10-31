"""所有时间以 UTC 无时区值存储；接口输出时显式补充 UTC。"""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 5,
            "read_timeout": 20,
            "write_timeout": 20,
            # 先由服务端终止元数据锁等待，避免客户端超时后留下排队 DDL。
            "init_command": "SET SESSION lock_wait_timeout=10",
        },
    )


def session_factory():
    return sessionmaker(get_engine(), expire_on_commit=False)


def get_session():
    with session_factory()() as session:
        yield session
