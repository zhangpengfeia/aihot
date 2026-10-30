"""批次、项目、观测快照及榜单分表，保证历史资料不会随仓库更新而改变。"""

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

from app.db import Base


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


class KnowledgeTopic(Base):
    """以规范化 URL 去重的知识资料；缺失发布日期时保留 NULL，不伪造时间。"""

    __tablename__ = "knowledge_topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(200))
    feed_source_key: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(50), index=True)
    topic_kind: Mapped[str] = mapped_column(String(30), index=True)
    region: Mapped[str | None] = mapped_column(String(20), index=True)
    region_basis: Mapped[str | None] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text)
    video_angle: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime)


class KnowledgeSourceState(Base):
    """每个来源独立记录状态；一个来源不可用时其他来源继续采集。"""

    __tablename__ = "knowledge_source_states"
    source_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    last_attempt: Mapped[datetime] = mapped_column(DateTime)
    last_success: Mapped[datetime | None] = mapped_column(DateTime)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(500))


class PersonalItem(Base):
    """实例共享的个人资料，收藏与备注独立于只读采集快照。"""

    __tablename__ = "personal_items"
    __table_args__ = (UniqueConstraint("target_kind", "target_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_kind: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(BigInteger)
    favorite: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class CreationCard(Base):
    __tablename__ = "creation_cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("knowledge_topics.id"), unique=True)
    stage: Mapped[str] = mapped_column(String(20), default="待筛选")
    script: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"), default="")
    output_url: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class ManagedKnowledgeSource(Base):
    """采集与管理页面共用的持久化订阅配置。URL 为稳定身份。"""

    __tablename__ = "managed_knowledge_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(2000))
    category: Mapped[str] = mapped_column(String(50))
    region: Mapped[str] = mapped_column(String(20))
    topic_kind: Mapped[str] = mapped_column(String(30))
    origin_key: Mapped[str | None] = mapped_column(String(64))
    adapter: Mapped[str | None] = mapped_column(String(30), default="rss")
    item_limit: Mapped[int | None] = mapped_column(Integer, default=100)
    options: Mapped[dict | None] = mapped_column(JSON)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_test_error: Mapped[str | None] = mapped_column(String(500))
    last_test_count: Mapped[int | None] = mapped_column(Integer)


class KnowledgeCategoryRule(Base):
    """分类别名与可见性规则；不重写原始选题分类。"""

    __tablename__ = "knowledge_category_rules"
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    canonical_name: Mapped[str | None] = mapped_column(String(50))
    hidden: Mapped[bool] = mapped_column(default=False)


class CategoryEditLock(Base):
    """单行锁让跨进程分类编辑串行，防止并发合并形成循环。"""

    __tablename__ = "category_edit_lock"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class KnowledgeCitation(Base):
    """同一选题的不同发现渠道，去重时仍保留各来源及社区热度。"""

    __tablename__ = "knowledge_citations"
    __table_args__ = (UniqueConstraint("topic_id", "source_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("knowledge_topics.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(64), index=True)
    source_name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(30))
    score: Mapped[int | None] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime)
