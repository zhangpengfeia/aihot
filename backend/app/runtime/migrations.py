"""v0.6 显式、可重复执行的增量迁移，MySQL DDL 不支持事务回滚。

先备份现有库，再执行；不重写或删除已有快照。旧快照没有分类时由接口兼容展示。
"""

from sqlalchemy import func, inspect, select, text, update
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
        if "is_latest" not in columns:
            connection.execute(
                text("ALTER TABLE snapshots ADD COLUMN is_latest BOOLEAN NOT NULL DEFAULT 1")
            )

    # 为既有快照回填「每个仓库最新」标志：先全量置假，再把每个仓库 id 最大的那条置真。
    # 分两条语句与分批更新，避免 MySQL 同表子查询限制及超大 IN 列表。
    from app.models import Snapshot

    with Session(engine) as session:
        session.execute(update(Snapshot).values(is_latest=False))
        max_ids = list(
            session.scalars(select(func.max(Snapshot.id)).group_by(Snapshot.repo_id))
        )
        for start in range(0, len(max_ids), 500):
            session.execute(
                update(Snapshot)
                .where(Snapshot.id.in_(max_ids[start : start + 500]))
                .values(is_latest=True)
            )
        session.commit()

    # 旧快照缺分类时一次性回填用途与安装摘录，避免资料库接口逐条懒加载 README 再计算。
    from app.services.skills.metadata import extract_metadata

    with Session(engine) as session:
        while True:
            batch = list(
                session.scalars(
                    select(Snapshot).where(Snapshot.categories.is_(None)).limit(200)
                )
            )
            if not batch:
                break
            for snapshot in batch:
                categories, installation = extract_metadata(
                    snapshot.full_name, snapshot.description or "", snapshot.readme or ""
                )
                snapshot.categories = categories
                snapshot.installation = installation
            session.commit()

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
    # 查询加速索引：批次筛选、快照排序、榜单关联与知识全文检索，重复迁移自动跳过。
    from app.models import Ranking, Run, Snapshot

    for index in (
        next(i for i in Run.__table__.indexes if i.name == "ix_run_status_scope_slot"),
        next(i for i in Snapshot.__table__.indexes if i.name == "ix_snapshot_stars"),
        next(i for i in Snapshot.__table__.indexes if i.name == "ix_snapshot_is_latest"),
        next(i for i in Ranking.__table__.indexes if i.name == "ix_ranking_snapshot"),
        next(i for i in KnowledgeTopic.__table__.indexes if i.name == "ix_knowledge_topics_ft"),
    ):
        index.create(engine, checkfirst=True)


if __name__ == "__main__":
    try:
        migrate(get_engine())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    print("数据库结构升级完成")
