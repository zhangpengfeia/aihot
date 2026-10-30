"""知识分类合并与可见性管理。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import same_origin_writes
from app.core.database import get_session
from app.models import (
    KnowledgeCategoryRule,
    KnowledgeTopic,
    ManagedKnowledgeSource,
)
from app.schemas.knowledge import CategoryMerge, CategoryName, CategoryVisibility
from app.services.knowledge.categories import get_category_catalog
from app.services.knowledge.management import (
    category_hidden,
    category_rules,
    lock_category_edits,
    resolve_category,
)
from app.utils.time import iso

router = APIRouter(prefix="/api/knowledge/manage", dependencies=[Depends(same_origin_writes)])


@router.get("/categories")
def categories(db: Session = Depends(get_session), catalog: dict = Depends(get_category_catalog)):
    counts = dict(
        db.execute(
            select(KnowledgeTopic.category, func.count()).group_by(KnowledgeTopic.category)
        ).all()
    )
    rules = category_rules(db)
    names = (
        set(counts)
        | set(rules)
        | set(catalog["categories"])
        | set(db.scalars(select(ManagedKnowledgeSource.category)))
    )
    names |= {rule.canonical_name for rule in rules.values() if rule.canonical_name}
    totals = {}
    for name, count in counts.items():
        canonical = resolve_category(name, rules)
        totals[canonical] = totals.get(canonical, 0) + count
    return {
        "items": [
            {
                "name": name,
                "canonical_name": resolve_category(name, rules),
                "topic_count": counts.get(name, 0),
                "total_count": totals.get(resolve_category(name, rules), 0),
                "hidden": category_hidden(name, rules),
                "is_alias": resolve_category(name, rules) != name,
            }
            for name in sorted(names)
        ],
        "catalog": {
            **{key: value for key, value in catalog.items() if key != "categories"},
            "updated_at": iso(catalog["updated_at"]),
        },
    }


@router.post("/category-merge")
def merge_category(body: CategoryMerge, db: Session = Depends(get_session)):
    lock_category_edits(db)
    rules = {r.name: r for r in db.scalars(select(KnowledgeCategoryRule).with_for_update())}
    target = resolve_category(body.target, rules)
    if target == body.source:
        raise HTTPException(422, "分类不能合并到自身或形成循环")
    rule = rules.get(body.source) or KnowledgeCategoryRule(name=body.source)
    rule.canonical_name = target
    db.add(rule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "分类规则刚被修改，请刷新后重试") from exc
    return {"source": body.source, "canonical_name": target}


@router.post("/category-unmerge")
def unmerge_category(body: CategoryName, db: Session = Depends(get_session)):
    lock_category_edits(db)
    rule = db.get(KnowledgeCategoryRule, body.name)
    if rule:
        rule.canonical_name = None
        db.commit()
    return {"name": body.name}


@router.put("/category-visibility")
def category_visibility(body: CategoryVisibility, db: Session = Depends(get_session)):
    lock_category_edits(db)
    rules = category_rules(db)
    canonical = resolve_category(body.name, rules)
    rule = rules.get(canonical) or KnowledgeCategoryRule(name=canonical)
    rule.hidden = body.hidden
    db.add(rule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "分类规则刚被修改，请刷新后重试") from exc
    return {"name": canonical, "hidden": body.hidden}
