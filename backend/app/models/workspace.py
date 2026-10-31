"""workspace 领域的数据表定义。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PersonalItem(Base):
    """用户独立的个人资料，收藏与备注独立于只读采集快照。"""

    __tablename__ = "personal_items"
    __table_args__ = (
        UniqueConstraint("user_id", "target_kind", "target_id", name="uq_personal_user_target"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    target_kind: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(BigInteger)
    favorite: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class CreationCard(Base):
    __tablename__ = "creation_cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_creation_user_topic"),)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("knowledge_topics.id"))
    stage: Mapped[str] = mapped_column(String(20), default="待筛选")
    script: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), "mysql"), default="")
    output_url: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
