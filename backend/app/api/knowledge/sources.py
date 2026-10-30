"""知识采集接口配置、测试与启停。"""

from datetime import timedelta
from xml.etree.ElementTree import ParseError

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import same_origin_writes
from app.core.database import get_session
from app.infrastructure.feed_http import get_feed_fetcher
from app.models import (
    KnowledgeSourceState,
    KnowledgeTopic,
    ManagedKnowledgeSource,
)
from app.schemas.knowledge import (
    SourceCreate,
    SourceUpdate,
)
from app.services.knowledge.adapters import collect_source
from app.services.knowledge.management import category_rules, managed_feed, resolve_category
from app.utils.time import iso, utcnow
from app.utils.urls import source_key

router = APIRouter(prefix="/api/knowledge/manage", dependencies=[Depends(same_origin_writes)])


def source_data(db, source, counts=None, rules=None):
    state = db.get(KnowledgeSourceState, source.source_key)
    count = (
        counts.get(source.source_key, 0)
        if counts is not None
        else db.scalar(
            select(func.count())
            .select_from(KnowledgeTopic)
            .where(KnowledgeTopic.feed_source_key == source.source_key)
        )
    )
    return {
        "id": source.id,
        "adapter": source.adapter or "rss",
        "item_limit": source.item_limit or 100,
        "options": source.options or {},
        "name": source.name,
        "url": source.url,
        "category": source.category,
        "display_category": resolve_category(
            source.category, rules if rules is not None else category_rules(db)
        ),
        "region": source.region,
        "topic_kind": source.topic_kind,
        "enabled": source.enabled,
        "collected_count": count,
        "status": state.status if state else "pending",
        "last_success": iso(state.last_success) if state else None,
        "last_attempt": iso(state.last_attempt) if state else None,
        "error": state.error if state else None,
        "last_test_at": iso(source.last_test_at),
        "last_test_error": source.last_test_error,
        "last_test_count": source.last_test_count,
    }


@router.get("/sources")
def sources(db: Session = Depends(get_session)):
    counts = dict(
        db.execute(
            select(KnowledgeTopic.feed_source_key, func.count()).group_by(
                KnowledgeTopic.feed_source_key
            )
        ).all()
    )
    rules = category_rules(db)
    return {
        "items": [
            source_data(db, source, counts, rules)
            for source in db.scalars(
                select(ManagedKnowledgeSource)
                .where(ManagedKnowledgeSource.deleted_at.is_(None))
                .order_by(ManagedKnowledgeSource.id)
            )
        ]
    }


@router.post("/sources", status_code=201)
def create_source(body: SourceCreate, db: Session = Depends(get_session)):
    previous = db.scalar(
        select(ManagedKnowledgeSource).where(
            ManagedKnowledgeSource.source_key == source_key(body.url)
        )
    )
    if previous and previous.deleted_at is not None:
        for name, value in body.model_dump(exclude={"url"}).items():
            setattr(previous, name, value)
        previous.deleted_at, previous.updated_at = None, utcnow()
        db.commit()
        return source_data(db, previous)
    source = ManagedKnowledgeSource(
        **body.model_dump(exclude={"url"}),
        url=str(body.url),
        source_key=source_key(body.url),
        origin_key=source_key(body.url),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(source)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "此订阅地址已存在，请编辑或重新启用已有来源") from exc
    return source_data(db, source)


def find_source(db, source_id):
    source = db.get(ManagedKnowledgeSource, source_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(404, "未找到订阅来源")
    return source


@router.patch("/sources/{source_id}")
def edit_source(source_id: int, body: SourceUpdate, db: Session = Depends(get_session)):
    source = find_source(db, source_id)
    values = body.model_dump(exclude_none=True)
    if "url" in values and str(values["url"]) != source.url:
        new_key = source_key(values["url"])
        duplicate = db.scalar(
            select(ManagedKnowledgeSource).where(ManagedKnowledgeSource.source_key == new_key)
        )
        if duplicate and duplicate.id != source.id:
            raise HTTPException(409, "此接口地址已存在（含已删除配置），请使用其他地址")
        from app.models import KnowledgeCitation

        old_key = source.source_key
        db.execute(
            update(KnowledgeTopic)
            .where(KnowledgeTopic.feed_source_key == old_key)
            .values(feed_source_key=new_key)
        )
        db.execute(
            update(KnowledgeCitation)
            .where(KnowledgeCitation.source_key == old_key)
            .values(source_key=new_key)
        )
        state = db.get(KnowledgeSourceState, old_key)
        if state:
            state.source_key, state.status, state.last_success = new_key, "pending", None
        source.source_key = new_key
        values["url"] = str(values["url"])
    for name, value in values.items():
        setattr(source, name, value)
    try:
        managed_feed(source)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, "接口类型、地址或字段映射不匹配，请检查配置") from exc
    source.updated_at = utcnow()
    db.commit()
    return source_data(db, source)


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_session)):
    """软删除配置并停用采集，保留所有已采集知识和个人收藏。"""
    source = find_source(db, source_id)
    source.deleted_at, source.enabled = utcnow(), False
    db.commit()
    return {"deleted": True, "id": source_id}


@router.post("/sources/{source_id}/test")
def test_source(
    source_id: int, db: Session = Depends(get_session), fetch=Depends(get_feed_fetcher)
):
    source = find_source(db, source_id)
    feed = managed_feed(source)
    now = utcnow()
    claimed = db.execute(
        update(ManagedKnowledgeSource)
        .where(
            ManagedKnowledgeSource.id == source_id,
            or_(
                ManagedKnowledgeSource.last_test_at.is_(None),
                ManagedKnowledgeSource.last_test_at < now - timedelta(seconds=30),
            ),
        )
        .values(last_test_at=now, last_test_error=None, last_test_count=None)
    )
    if not claimed.rowcount:
        db.rollback()
        raise HTTPException(429, "同一来源每 30 秒可测试一次，请稍后再试")
    db.commit()
    error = None
    records = []
    try:
        records = collect_source(feed, fetch)
        if not records:
            raise ValueError("订阅源中没有可用条目")
    except httpx.HTTPStatusError as exc:
        error = f"来源返回 HTTP {exc.response.status_code}"
    except (ValueError, ParseError) as exc:
        error = str(exc)[:400]
    except httpx.HTTPError as exc:
        error = f"网络请求失败（{type(exc).__name__}）"
    db.execute(
        update(ManagedKnowledgeSource)
        .where(ManagedKnowledgeSource.id == source_id)
        .values(
            last_test_error=error,
            last_test_count=len(records) if error is None else 0,
        )
    )
    db.commit()
    return {
        "ok": error is None,
        "error": error,
        "checked_at": iso(now),
        "item_count": len(records),
        "items": [
            {
                "title": row["title"],
                "url": row["source_url"],
                "published_at": iso(row["published_at"]),
            }
            for row in records[:5]
        ],
    }
