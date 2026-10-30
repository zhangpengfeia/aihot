"""v0.6 显式、可重复执行的增量迁移，MySQL DDL 不支持事务回滚。

先备份现有库，再执行；不重写或删除已有快照。旧快照没有分类时由接口兼容展示。
"""

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base, get_engine


def migrate(engine):
    # checkfirst 默认开启；新增配置与规则表，重复迁移不覆盖用户资料。
    Base.metadata.create_all(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("snapshots")}
    topic_columns = {column["name"] for column in inspect(engine).get_columns("knowledge_topics")}
    managed_columns = {
        column["name"] for column in inspect(engine).get_columns("managed_knowledge_sources")
    }
    with engine.begin() as connection:
        for name, ddl in {
            "origin_key": "VARCHAR(64) NULL",
            "adapter": "VARCHAR(30) NULL",
            "item_limit": "INTEGER NULL",
            "options": "JSON NULL",
            "deleted_at": "DATETIME NULL",
        }.items():
            if name not in managed_columns:
                connection.execute(
                    text(f"ALTER TABLE managed_knowledge_sources ADD COLUMN {name} {ddl}")
                )
        if "feed_source_key" not in topic_columns:
            connection.execute(
                text("ALTER TABLE knowledge_topics ADD COLUMN feed_source_key VARCHAR(64) NULL")
            )
        if "region" not in topic_columns:
            connection.execute(
                text("ALTER TABLE knowledge_topics ADD COLUMN region VARCHAR(20) NULL")
            )
        if "region_basis" not in topic_columns:
            connection.execute(
                text("ALTER TABLE knowledge_topics ADD COLUMN region_basis VARCHAR(100) NULL")
            )
        if "categories" not in columns:
            connection.execute(text("ALTER TABLE snapshots ADD COLUMN categories JSON NULL"))
        if "installation" not in columns:
            connection.execute(text("ALTER TABLE snapshots ADD COLUMN installation TEXT NULL"))

    # 为已有知识资料补地区；只处理能对应当前来源配置的记录，未知来源保留待分类。
    from app.config import get_settings
    from app.knowledge import classify_region
    from app.models import KnowledgeTopic

    sources = {source.name: source for source in get_settings().knowledge_sources}
    from app.knowledge_management import seed_sources
    from app.models import ManagedKnowledgeSource

    with Session(engine) as session:
        for config in session.scalars(
            select(ManagedKnowledgeSource).where(ManagedKnowledgeSource.origin_key.is_(None))
        ):
            config.origin_key = config.source_key
        session.flush()
        seed_sources(session, get_settings())
        session.flush()
        by_name = {}
        for source in session.scalars(select(ManagedKnowledgeSource)):
            by_name.setdefault(source.name, []).append(source.source_key)
        for topic in session.scalars(
            select(KnowledgeTopic).where(KnowledgeTopic.feed_source_key.is_(None))
        ):
            keys = by_name.get(topic.source_name, [])
            if len(keys) == 1:
                topic.feed_source_key = keys[0]
        for topic in session.scalars(select(KnowledgeTopic).where(KnowledgeTopic.region.is_(None))):
            source = sources.get(topic.source_name)
            if source:
                topic.region, topic.region_basis = classify_region(
                    topic.title, topic.summary, source
                )
        session.commit()
    region_index = next(
        index
        for index in KnowledgeTopic.__table__.indexes
        if index.name == "ix_knowledge_topics_region"
    )
    region_index.create(engine, checkfirst=True)
    next(
        index
        for index in KnowledgeTopic.__table__.indexes
        if index.name == "ix_knowledge_topics_feed_source_key"
    ).create(engine, checkfirst=True)


if __name__ == "__main__":
    migrate(get_engine())
    print("数据库结构升级完成")
