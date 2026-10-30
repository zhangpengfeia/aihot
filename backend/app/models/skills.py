"""skills 领域的数据表定义。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Run(Base):
    __tablename__ = "collection_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 同一半小时窗口只有一个批次，失败批次允许重试。
    slot: Mapped[datetime] = mapped_column(DateTime, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(500))


class Repository(Base):
    __tablename__ = "repositories"
    # GitHub 稳定 ID 用于去重，仓库更名不会产生第二个项目。
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String(255), unique=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime)


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint("run_id", "repo_id"),
        Index("ix_snapshot_repo_time", "repo_id", "observed_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("collection_runs.id"))
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    full_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    stars: Mapped[int] = mapped_column(Integer)
    forks: Mapped[int] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(100))
    license: Mapped[str | None] = mapped_column(String(100))
    pushed_at: Mapped[str | None] = mapped_column(String(50))
    readme: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"))
    evidence: Mapped[str] = mapped_column(String(500))
    delta_24h: Mapped[int | None] = mapped_column(Integer)
    baseline_at: Mapped[datetime | None] = mapped_column(DateTime)
    categories: Mapped[list[str] | None] = mapped_column(JSON)
    installation: Mapped[str | None] = mapped_column(Text)


class Ranking(Base):
    __tablename__ = "rankings"
    __table_args__ = (UniqueConstraint("run_id", "kind", "position"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("collection_runs.id"))
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    kind: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
