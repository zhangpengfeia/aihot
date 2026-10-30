"""收藏与创作卡的共用资料映射。"""

from fastapi import HTTPException
from sqlalchemy import select

from app.models import (
    KnowledgeTopic,
    Snapshot,
)
from app.services.knowledge.management import category_rules, resolve_category
from app.utils.time import iso


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
