"""工作空间creation接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import same_origin_writes
from app.core.database import get_session
from app.models import (
    CreationCard,
)
from app.schemas.workspace import CardCreate, CardWrite
from app.services.workspace.serialization import card_data, target_data
from app.utils.time import utcnow

router = APIRouter(prefix="/api/workspace", dependencies=[Depends(same_origin_writes)])


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
    target_data(db, "topic", body.topic_id, for_update=True)
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
