"""个人收藏、创作卡、榜单变化及采集状态。当前实例为单用户共享工作空间。"""

from datetime import UTC
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.knowledge_management import category_rules, resolve_category
from app.models import (
    CreationCard,
    KnowledgeSourceState,
    KnowledgeTopic,
    PersonalItem,
    Ranking,
    Run,
    Snapshot,
)
from app.time_utils import utcnow
from app.worker import next_collection_at

TargetKind = Literal["repository", "topic"]
Stage = Literal["待筛选", "待创作", "制作中", "已发布"]


def same_origin_writes(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and urlsplit(origin).netloc != request.headers.get("host")
    ):
        raise HTTPException(403, "仅允许同源页面修改工作空间")
    if request.method in {"PUT", "PATCH", "POST"} and not request.headers.get(
        "content-type", ""
    ).startswith("application/json"):
        raise HTTPException(415, "请使用 application/json")


router = APIRouter(
    prefix="/api/workspace", tags=["个人工作空间"], dependencies=[Depends(same_origin_writes)]
)


def iso(value):
    return value.replace(tzinfo=UTC).isoformat() if value else None


def target_data(db, kind, target_id):
    if kind == "repository":
        target = db.scalar(
            select(Snapshot)
            .where(Snapshot.repo_id == target_id)
            .order_by(Snapshot.observed_at.desc(), Snapshot.id.desc())
            .limit(1)
        )
        if target:
            return {
                "title": target.full_name,
                "url": f"https://github.com/{target.full_name}",
                "snapshot_id": target.id,
            }
    else:
        target = db.get(KnowledgeTopic, target_id)
        if target:
            return {"title": target.title, "url": target.source_url, "topic_id": target.id}
    raise HTTPException(404, "未找到原始项目或选题")


def personal_data(db, item):
    return {
        "id": item.id,
        "target_kind": item.target_kind,
        "target_id": item.target_id,
        "favorite": item.favorite,
        "note": item.note,
        "updated_at": iso(item.updated_at),
        **target_data(db, item.target_kind, item.target_id),
    }


class PersonalWrite(BaseModel):
    favorite: bool | None = None
    note: str | None = Field(None, max_length=10000)


@router.get("/items")
def personal_list(
    favorite: bool | None = True,
    all_records: bool = False,
    kind: TargetKind | None = None,
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    query = select(PersonalItem).order_by(PersonalItem.updated_at.desc(), PersonalItem.id.desc())
    if favorite is not None and not all_records:
        query = query.where(PersonalItem.favorite == favorite)
    if kind:
        query = query.where(PersonalItem.target_kind == kind)
    items = [personal_data(db, item) for item in db.scalars(query)]
    if q.strip():
        needle = q.strip().casefold()
        items = [item for item in items if needle in f"{item['title']} {item['note']}".casefold()]
    start = (page - 1) * page_size
    return {"total": len(items), "items": items[start : start + page_size]}


@router.get("/items/{kind}/{target_id}")
def personal_get(kind: TargetKind, target_id: int, db: Session = Depends(get_session)):
    data = target_data(db, kind, target_id)
    item = db.scalar(
        select(PersonalItem).where(
            PersonalItem.target_kind == kind, PersonalItem.target_id == target_id
        )
    )
    return (
        personal_data(db, item)
        if item
        else {"target_kind": kind, "target_id": target_id, "favorite": False, "note": "", **data}
    )


@router.put("/items/{kind}/{target_id}")
def personal_save(
    kind: TargetKind, target_id: int, body: PersonalWrite, db: Session = Depends(get_session)
):
    target_data(db, kind, target_id)
    query = select(PersonalItem).where(
        PersonalItem.target_kind == kind, PersonalItem.target_id == target_id
    )
    item = db.scalar(query)
    if item is None:
        item = PersonalItem(
            target_kind=kind, target_id=target_id, created_at=utcnow(), updated_at=utcnow()
        )
        db.add(item)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            item = db.scalar(query)
            if item is None:
                raise
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    item.updated_at = utcnow()
    db.commit()
    return personal_data(db, item)


@router.delete("/items/{kind}/{target_id}", status_code=204)
def personal_delete(kind: TargetKind, target_id: int, db: Session = Depends(get_session)):
    item = db.scalar(
        select(PersonalItem).where(
            PersonalItem.target_kind == kind, PersonalItem.target_id == target_id
        )
    )
    if item:
        db.delete(item)
        db.commit()
    return Response(status_code=204)


class CardCreate(BaseModel):
    topic_id: int = Field(gt=0)


class CardWrite(BaseModel):
    stage: Stage | None = None
    script: str | None = Field(None, max_length=100000)
    output_url: str | None = Field(None, max_length=2000)

    @field_validator("output_url")
    @classmethod
    def safe_url(cls, value):
        if value is None or not value.strip():
            return "" if value is not None else None
        value = value.strip()
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or any(c.isspace() for c in value)
        ):
            raise ValueError("成品链接必须是 http(s) URL")
        return value


def card_data(db, card):
    topic = db.get(KnowledgeTopic, card.topic_id)
    return {
        "id": card.id,
        "topic_id": card.topic_id,
        "title": topic.title,
        "category": resolve_category(topic.category, category_rules(db)),
        "source_url": topic.source_url,
        "stage": card.stage,
        "script": card.script,
        "output_url": card.output_url,
        "updated_at": iso(card.updated_at),
    }


@router.get("/cards")
def cards(q: str = Query("", max_length=100), db: Session = Depends(get_session)):
    items = [
        card_data(db, card)
        for card in db.scalars(
            select(CreationCard).order_by(CreationCard.updated_at.desc(), CreationCard.id.desc())
        )
    ]
    if q.strip():
        items = [item for item in items if q.strip().casefold() in item["title"].casefold()]
    return {"items": items}


@router.post("/cards")
def card_create(body: CardCreate, db: Session = Depends(get_session)):
    target_data(db, "topic", body.topic_id)
    query = select(CreationCard).where(CreationCard.topic_id == body.topic_id)
    card = db.scalar(query)
    if not card:
        card = CreationCard(topic_id=body.topic_id, created_at=utcnow(), updated_at=utcnow())
        db.add(card)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            card = db.scalar(query)
            if card is None:
                raise
    return card_data(db, card)


@router.patch("/cards/{card_id}")
def card_update(card_id: int, body: CardWrite, db: Session = Depends(get_session)):
    card = db.get(CreationCard, card_id)
    if card is None:
        raise HTTPException(404, "未找到创作卡片")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(card, key, value)
    card.updated_at = utcnow()
    db.commit()
    return card_data(db, card)


@router.delete("/cards/{card_id}", status_code=204)
def card_delete(card_id: int, db: Session = Depends(get_session)):
    card = db.get(CreationCard, card_id)
    if card:
        db.delete(card)
        db.commit()
    return Response(status_code=204)


@router.get("/daily-summary")
def daily_summary(db: Session = Depends(get_session)):
    from app.main import run_data, snapshot_data

    runs = list(
        db.scalars(
            select(Run)
            .where(Run.status == "success")
            .order_by(Run.slot.desc(), Run.id.desc())
            .limit(2)
        )
    )
    if not runs:
        return {"current": None, "previous": None, "new_entries": [], "risers": [], "growth": []}

    def board(run):
        rows = db.execute(
            select(Ranking, Snapshot)
            .join(Snapshot, Ranking.snapshot_id == Snapshot.id)
            .where(Ranking.run_id == run.id, Ranking.kind == "stars")
            .order_by(Ranking.position)
        )
        return {s.repo_id: {"rank": r.position, **snapshot_data(s)} for r, s in rows}

    current = board(runs[0])
    previous = board(runs[1]) if len(runs) > 1 else {}
    new = [item for key, item in current.items() if key not in previous] if len(runs) > 1 else []
    risers = [
        {
            **item,
            "previous_rank": previous[key]["rank"],
            "rank_change": previous[key]["rank"] - item["rank"],
        }
        for key, item in current.items()
        if key in previous and previous[key]["rank"] > item["rank"]
    ]
    growth = list(
        db.scalars(
            select(Snapshot)
            .where(Snapshot.run_id == runs[0].id, Snapshot.delta_24h > 0)
            .order_by(Snapshot.delta_24h.desc(), Snapshot.repo_id)
            .limit(10)
        )
    )
    return {
        "current": run_data(runs[0]),
        "previous": run_data(runs[1]) if len(runs) > 1 else None,
        "new_entries": new,
        "risers": sorted(risers, key=lambda item: (-item["rank_change"], item["rank"])),
        "growth": [snapshot_data(item) for item in growth],
    }


@router.get("/collection-status")
def collection_status(db: Session = Depends(get_session)):
    from app.main import run_data

    now = utcnow()
    recent = list(db.scalars(select(Run).order_by(Run.started_at.desc(), Run.id.desc()).limit(10)))
    success = db.scalar(
        select(Run)
        .where(Run.status == "success")
        .order_by(Run.finished_at.desc(), Run.id.desc())
        .limit(1)
    )
    failure = db.scalar(
        select(Run)
        .where(Run.status == "failed")
        .order_by(Run.started_at.desc(), Run.id.desc())
        .limit(1)
    )
    from app.knowledge_management_api import sources as managed_sources
    from app.models import ManagedKnowledgeSource

    knowledge_sources = (
        managed_sources(db)["items"]
        if db.scalar(select(ManagedKnowledgeSource.id).limit(1)) is not None
        else [
            {
                "name": s.name,
                "status": s.status,
                "last_attempt": iso(s.last_attempt),
                "last_success": iso(s.last_success),
                "error": s.error,
            }
            for s in db.scalars(select(KnowledgeSourceState).order_by(KnowledgeSourceState.name))
        ]
    )
    for source in knowledge_sources:
        if source.get("enabled") is False:
            source["status"] = "disabled"
    return {
        "server_time": iso(now),
        "timezone": "Asia/Shanghai",
        "schedule": "每天 02:00",
        "next_scheduled_at": iso(next_collection_at(now)),
        "latest": run_data(recent[0]) if recent else None,
        "last_success": run_data(success) if success else None,
        "last_failure": run_data(failure) if failure else None,
        "recent_runs": [run_data(run) for run in recent],
        "knowledge_sources": knowledge_sources,
        "total_successful_runs": db.scalar(
            select(func.count()).select_from(Run).where(Run.status == "success")
        ),
    }
