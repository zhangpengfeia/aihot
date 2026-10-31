"""v0.6 显式、可重复执行的增量迁移，MySQL DDL 不支持事务回滚。

先备份现有库，再执行；不重写或删除已有快照。旧快照没有分类时由接口兼容展示。
"""

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.database import Base, get_engine


def migrate(engine):
    from app.runtime.schema_changes import run_schema_change

    return run_schema_change(engine, lambda: _migrate(engine))


def _migrate(engine):
    # checkfirst 默认开启；新增配置与规则表，重复迁移不覆盖用户资料。
    from app.runtime.schema_changes import create_missing_tables

    create_missing_tables(engine, Base.metadata)
    from app.core.auth import seed_admin
    from app.core.config import get_settings

    with Session(engine) as db:
        seed_admin(db, get_settings())
    # 旧共享资料只归属首个管理员；新账号不会看到历史共享收藏和脚本。
    from app.models.users import User

    with Session(engine) as db:
        owner = db.scalar(select(User.id).where(User.role == "admin").order_by(User.id).limit(1))
    for table, key_columns, index_name in (
        ("personal_items", ["user_id", "target_kind", "target_id"], "uq_personal_user_target"),
        ("creation_cards", ["user_id", "topic_id"], "uq_creation_user_topic"),
    ):
        existing = inspect(engine)
        with engine.begin() as connection:
            if "user_id" not in {col["name"] for col in existing.get_columns(table)}:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NULL"))
            connection.execute(
                text(f"UPDATE {table} SET user_id = :owner WHERE user_id IS NULL"), {"owner": owner}
            )
            constraints = existing.get_unique_constraints(table)
            for constraint in constraints:
                if "user_id" not in constraint["column_names"]:
                    if engine.dialect.name != "mysql":
                        raise RuntimeError("旧共享表的唯一约束升级需要 MySQL")
                    # MySQL 外键可能复用旧 topic_id 唯一索引，先保留独立索引再移除唯一性。
                    if table == "creation_cards" and not any(
                        index["name"] == "ix_creation_topic_owner_migration"
                        for index in existing.get_indexes(table)
                    ):
                        connection.execute(
                            text(
                                "CREATE INDEX ix_creation_topic_owner_migration ON creation_cards (topic_id)"
                            )
                        )
                    name = engine.dialect.identifier_preparer.quote(constraint["name"])
                    connection.execute(text(f"ALTER TABLE {table} DROP INDEX {name}"))
            if not any(set(c["column_names"]) == set(key_columns) for c in constraints):
                connection.execute(
                    text(f"CREATE UNIQUE INDEX {index_name} ON {table} ({', '.join(key_columns)})")
                )
    with engine.begin() as connection:
        if "scope" not in {col["name"] for col in inspect(engine).get_columns("collection_runs")}:
            connection.execute(
                text("ALTER TABLE collection_runs ADD COLUMN scope VARCHAR(40) NULL")
            )
        snapshot_columns = {col["name"] for col in inspect(engine).get_columns("snapshots")}
        for name, ddl in {
            "analysis": "JSON NULL",
            "delta_7d": "INTEGER NULL",
            "baseline_7d_at": "DATETIME NULL",
        }.items():
            if name not in snapshot_columns:
                connection.execute(text(f"ALTER TABLE snapshots ADD COLUMN {name} {ddl}"))
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
    from app.core.config import get_settings
    from app.models import KnowledgeTopic
    from app.services.knowledge.normalization import classify_region

    sources = {source.name: source for source in get_settings().knowledge_sources}
    from app.models import ManagedKnowledgeSource
    from app.services.knowledge.management import seed_sources

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
    try:
        migrate(get_engine())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    print("数据库结构升级完成")
