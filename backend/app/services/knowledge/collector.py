"""知识采集编排、事务提交和多渠道引用持久化。"""

import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.feed_http import feed_client, fetch_feed
from app.models import (
    KnowledgeCitation,
    KnowledgeSourceState,
    KnowledgeTopic,
    ManagedKnowledgeSource,
)
from app.services.knowledge.management import active_sources
from app.services.storage import StorageLimitError, incoming_size, storage_guard
from app.utils.time import time_slot, utcnow
from app.utils.urls import source_key

logger = logging.getLogger(__name__)


def save_topics(session: Session, records: list[dict], now: datetime) -> int:
    """批量查询减少云数据库往返；原文链接去重，同时保留每个发现渠道。"""
    if not records:
        return 0
    hashes = {row["url_hash"] for row in records}
    entities = {
        item.url_hash: item
        for item in session.scalars(
            select(KnowledgeTopic).where(KnowledgeTopic.url_hash.in_(hashes))
        )
    }
    added = 0
    for raw in records:
        record = {
            k: v for k, v in raw.items() if k not in {"channel", "score", "hot_rank", "score_label"}
        }
        entity = entities.get(record["url_hash"])
        if entity is None:
            entity = KnowledgeTopic(**record, collected_at=now, last_seen=now)
            entities[record["url_hash"]] = entity
            session.add(entity)
            added += 1
        elif entity.feed_source_key in (None, record.get("feed_source_key")):
            for key, value in record.items():
                if key != "published_at" or value is not None:
                    setattr(entity, key, value)
        entity.last_seen = now
    session.flush()
    citations = {
        (row.topic_id, row.source_key): row
        for row in session.scalars(
            select(KnowledgeCitation).where(
                KnowledgeCitation.topic_id.in_([e.id for e in entities.values()])
            )
        )
    }
    for raw in records:
        key = raw.get("feed_source_key")
        if not key:
            continue
        entity = entities[raw["url_hash"]]
        citation = citations.get((entity.id, key))
        if citation is None:
            citation = KnowledgeCitation(topic_id=entity.id, source_key=key)
            citations[(entity.id, key)] = citation
            session.add(citation)
        citation.source_name, citation.channel = raw["source_name"], raw.get("channel", "rss")
        citation.score, citation.observed_at = raw.get("score"), now
    session.flush()
    from app.models import HotListSnapshot

    groups = {}
    for row in records:
        if row.get("channel") == "hotlist":
            groups.setdefault(row["feed_source_key"], []).append(row)
    for key, rows in groups.items():
        snapshot = session.get(HotListSnapshot, key)
        if snapshot is None:
            snapshot = HotListSnapshot(source_key=key)
            session.add(snapshot)
        snapshot.observed_at = now
        snapshot.entries = [
            {
                "id": entities[row["url_hash"]].id,
                "title": row["title"],
                "source_url": row["source_url"],
                "score": row.get("score"),
                "rank": row.get("hot_rank", index + 1),
                "score_label": row.get("score_label"),
            }
            for index, row in enumerate(rows)
        ]
    return added


def collect_knowledge(settings, engine=None, client=None, progress=None) -> dict:
    from app.core.database import get_engine

    progress = progress or (lambda percent, message: None)
    engine = engine or get_engine()
    stats = {"sources": 0, "failed": 0, "added": 0}
    factory = sessionmaker(engine, expire_on_commit=False)
    with engine.connect() as lock:
        if lock.scalar(text("SELECT GET_LOCK('aihot.knowledge', 0)")) != 1:
            stats["skipped"] = True
            progress(0, "跳过：已有知识采集任务正在执行")
            return stats
        http = client or feed_client()
        try:
            with storage_guard(engine, settings):
                pass
            with factory() as session:
                sources = active_sources(session, settings)
            for index, source in enumerate(sources):
                progress(
                    int(index / len(sources) * 95),
                    f"正在处理 {index + 1}/{len(sources)}：{source.name}",
                )
                key = source_key(source.url)
                now = utcnow()
                with factory() as session:
                    configured = session.scalar(
                        select(ManagedKnowledgeSource).where(
                            ManagedKnowledgeSource.source_key == key
                        )
                    )
                    if configured is not None and not configured.enabled:
                        progress(
                            int((index + 1) / len(sources) * 95),
                            f"跳过：{source.name}（停用或当前窗口已完成）",
                        )
                        continue
                    state = session.get(KnowledgeSourceState, key)
                    if (
                        state
                        and state.last_success
                        and time_slot(state.last_success) == time_slot(now)
                    ):
                        progress(
                            int((index + 1) / len(sources) * 95),
                            f"跳过：{source.name}（停用或当前窗口已完成）",
                        )
                        continue
                try:
                    from app.services.knowledge.adapters import collect_source

                    records = collect_source(source, lambda url: fetch_feed(url, http))
                    if not records:
                        raise ValueError("订阅源中没有有效条目")
                    with (
                        storage_guard(engine, settings, incoming_size(records)),
                        factory.begin() as session,
                    ):
                        added = save_topics(session, records, now)
                        state = session.get(KnowledgeSourceState, key) or KnowledgeSourceState(
                            source_key=key
                        )
                        state.name, state.url, state.category = (
                            source.name,
                            str(source.url),
                            source.category,
                        )
                        state.status, state.last_attempt, state.last_success = (
                            "success",
                            now,
                            utcnow(),
                        )
                        state.item_count, state.error = len(records), None
                        session.add(state)
                    stats["sources"] += 1
                    stats["added"] += added
                    progress(
                        int((index + 1) / len(sources) * 95),
                        f"完成：{source.name}，读取 {len(records)} 条，新增 {added} 条",
                    )
                    logger.info(
                        "接口采集完成：%s，读取 %s 条，新增 %s 条", source.name, len(records), added
                    )
                except (SQLAlchemyError, StorageLimitError):
                    # 数据库故障不算来源故障；事务已回滚，停止本轮等待下次重连。
                    raise
                except Exception as exc:
                    logger.warning("知识来源采集失败：%s (%s)", source.name, type(exc).__name__)
                    with factory.begin() as session:
                        state = session.get(KnowledgeSourceState, key) or KnowledgeSourceState(
                            source_key=key
                        )
                        state.name, state.url, state.category = (
                            source.name,
                            str(source.url),
                            source.category,
                        )
                        state.status, state.last_attempt, state.error = (
                            "failed",
                            now,
                            type(exc).__name__,
                        )
                        session.add(state)
                    stats["failed"] += 1
                    progress(
                        int((index + 1) / len(sources) * 95),
                        f"失败：{source.name}（{type(exc).__name__}）",
                    )
        finally:
            if client is None:
                http.close()
            try:
                lock.execute(text("SELECT RELEASE_LOCK('aihot.knowledge')"))
            except SQLAlchemyError:
                logger.warning("数据库连接失效，服务端会在连接关闭后释放采集锁")
    return stats
