"""来源初始化与分类映射的共享业务规则。"""

import hashlib

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CategoryEditLock, KnowledgeCategoryRule, ManagedKnowledgeSource
from app.services.knowledge.sources import FeedSource
from app.utils.time import utcnow


def source_key(url):
    return hashlib.sha256(str(url).encode()).hexdigest()


def seed_sources(session: Session, settings):
    """增量导入新默认来源，不覆盖编辑、停用或已删除的配置。"""
    existing_rows = list(session.scalars(select(ManagedKnowledgeSource)))
    existing = {r.source_key for r in existing_rows} | {r.origin_key for r in existing_rows}
    for source in {source_key(s.url): s for s in settings.knowledge_sources}.values():
        if source_key(source.url) in existing:
            continue
        session.add(
            ManagedKnowledgeSource(
                source_key=source_key(source.url),
                origin_key=source_key(source.url),
                name=source.name,
                url=str(source.url),
                category=source.category,
                region=source.region,
                topic_kind=source.topic_kind,
                adapter=source.adapter,
                item_limit=source.item_limit,
                options=source.options,
                enabled=source.enabled,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )


def managed_feed(source):
    return FeedSource(
        name=source.name,
        url=source.url,
        category=source.category,
        region=source.region,
        topic_kind=source.topic_kind,
        adapter=source.adapter or "rss",
        item_limit=source.item_limit or 100,
        options=source.options or {},
    )


def active_sources(session, settings):
    rows = list(
        session.scalars(
            select(ManagedKnowledgeSource)
            .where(ManagedKnowledgeSource.deleted_at.is_(None))
            .order_by(ManagedKnowledgeSource.id)
        )
    )
    has_config = session.scalar(select(ManagedKnowledgeSource.id).limit(1)) is not None
    return (
        [managed_feed(row) for row in rows if row.enabled]
        if has_config
        else [s for s in settings.knowledge_sources if s.enabled]
    )


def category_rules(session):
    return {rule.name: rule for rule in session.scalars(select(KnowledgeCategoryRule))}


def resolve_category(name, rules):
    seen = set()
    while name in rules and rules[name].canonical_name:
        if name in seen:
            raise ValueError("分类合并规则形成循环")
        seen.add(name)
        name = rules[name].canonical_name
    return name


def category_hidden(name, rules):
    canonical = resolve_category(name, rules)
    return bool(canonical in rules and rules[canonical].hidden)


def lock_category_edits(session):
    if session.get(CategoryEditLock, 1) is None:
        session.add(CategoryEditLock(id=1))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
    session.execute(
        select(CategoryEditLock).where(CategoryEditLock.id == 1).with_for_update()
    ).scalar_one()
