"""工作空间personal接口。"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import same_origin_writes
from app.core.database import get_session
from app.models import (
    PersonalItem,
)
from app.schemas.workspace import PersonalWrite, TargetKind
from app.services.workspace.serialization import personal_data, target_data
from app.utils.time import utcnow

router = APIRouter(prefix="/api/workspace", dependencies=[Depends(same_origin_writes)])


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
    target_data(db, kind, target_id, for_update=True)
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
