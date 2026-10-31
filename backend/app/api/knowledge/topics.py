"""知识选题库查询接口，支持内容分类、选题类型、关键词和发布日期过滤。"""

from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.taxonomy import TAG_GROUPS, TAG_TERMS, topic_tags
from app.models import (
    KnowledgeCitation,
    KnowledgeSourceState,
    KnowledgeTopic,
    ManagedKnowledgeSource,
)
from app.services.knowledge.categories import get_category_catalog
from app.services.knowledge.management import category_hidden, category_rules, resolve_category
from app.utils.time import utcnow

router = APIRouter(prefix="/api/knowledge", tags=["知识选题库"])


def serialize(item: KnowledgeTopic, rules=None, citations=None):
    from app.utils.time import iso

    return {
        "id": item.id,
        "tags": topic_tags(item.title, item.summary, item.category),
        "channels": [
            {"name": row.source_name, "adapter": row.channel, "score": row.score}
            for row in (citations or [])
        ],
        "title": item.title,
        "category": resolve_category(item.category, rules or {}),
        "original_category": item.category,
        "region": item.region or "待分类",
        "region_basis": item.region_basis or "历史资料尚未判断地区",
        "topic_kind": item.topic_kind,
        "summary": item.summary,
        "video_angle": item.video_angle,
        "source_name": item.source_name,
        "source_url": item.source_url,
        "published_at": iso(item.published_at),
        "collected_at": iso(item.collected_at),
        "last_seen": iso(item.last_seen),
        "summary_method": "来源摘要摘录",
        "angle_method": "规则建议，待核实",
    }


@router.get("/topics")
def topics(
    category: str | None = None,
    labels: list[str] = Query(default=[], max_length=50),
    tag: str | None = Query(None, max_length=50),
    hot_only: bool = False,
    region: Literal["国内", "国外"] | None = None,
    topic_kind: Literal["热点候选", "知识探索"] | None = None,
    q: str = Query("", max_length=100),
    day: date | None = None,
    source_id: int | None = None,
    sort_by: Literal["published", "collected"] = "published",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    from app.utils.time import SHANGHAI

    rules = category_rules(session)
    filters = []
    if labels:
        choices = []
        for label in set(labels):
            if not label.strip() or len(label) > 50:
                raise HTTPException(422, "内容分类或标签长度应在 1–50 字之间")
            canonical = resolve_category(label, rules)
            aliases = {name for name in rules if resolve_category(name, rules) == canonical} | {
                canonical
            }
            choices.append(KnowledgeTopic.category.in_(aliases))
            for term in TAG_TERMS.get(label, []):
                choices.extend(
                    column.contains(term, autoescape=True)
                    for column in (KnowledgeTopic.title, KnowledgeTopic.summary)
                )
        filters.append(or_(*choices))

    if tag:
        terms = TAG_TERMS.get(tag, [tag])
        filters.append(
            or_(
                KnowledgeTopic.category == tag,
                *[
                    column.contains(term, autoescape=True)
                    for term in terms
                    for column in (KnowledgeTopic.title, KnowledgeTopic.summary)
                ],
            )
        )
    if hot_only:
        filters.append(
            KnowledgeTopic.id.in_(
                select(KnowledgeCitation.topic_id).where(KnowledgeCitation.channel == "hotlist")
            )
        )

    if source_id is not None:
        source = session.get(ManagedKnowledgeSource, source_id)
        if source is None or source.deleted_at is not None:
            raise HTTPException(404, "采集接口不存在")
        cited = select(KnowledgeCitation.topic_id).where(
            KnowledgeCitation.source_key == source.source_key
        )
        filters.append(
            or_(KnowledgeTopic.feed_source_key == source.source_key, KnowledgeTopic.id.in_(cited))
        )
    if region:
        filters.append(KnowledgeTopic.region == region)
    if category:
        canonical = resolve_category(category, rules)
        aliases = {name for name in rules if resolve_category(name, rules) == canonical} | {
            canonical
        }
        filters.append(KnowledgeTopic.category.in_(aliases))
    if topic_kind:
        filters.append(KnowledgeTopic.topic_kind == topic_kind)
    if q.strip():
        filters.append(
            or_(
                KnowledgeTopic.title.contains(q.strip(), autoescape=True),
                KnowledgeTopic.summary.contains(q.strip(), autoescape=True),
            )
        )
    if day:
        start = datetime.combine(day, time.min, SHANGHAI).replace(tzinfo=SHANGHAI)
        from datetime import UTC

        start = start.astimezone(UTC).replace(tzinfo=None)
        filters.extend(
            [
                KnowledgeTopic.published_at >= start,
                KnowledgeTopic.published_at < start + timedelta(days=1),
            ]
        )
    total = session.scalar(select(func.count()).select_from(KnowledgeTopic).where(*filters))
    items = list(
        session.scalars(
            select(KnowledgeTopic)
            .where(*filters)
            .order_by(
                (
                    KnowledgeTopic.collected_at
                    if sort_by == "collected"
                    else func.coalesce(KnowledgeTopic.published_at, KnowledgeTopic.collected_at)
                ).desc(),
                KnowledgeTopic.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    citations = {}
    for row in session.scalars(
        select(KnowledgeCitation).where(KnowledgeCitation.topic_id.in_([i.id for i in items]))
    ):
        citations.setdefault(row.topic_id, []).append(row)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "items": [serialize(item, rules, citations.get(item.id)) for item in items],
    }


@router.get("/meta")
def meta(
    session: Session = Depends(get_session),
    catalog: dict = Depends(get_category_catalog),
):
    from app.utils.time import iso

    rules = category_rules(session)
    categories = list(session.scalars(select(KnowledgeTopic.category).distinct()))
    sources = list(
        session.scalars(select(KnowledgeSourceState).order_by(KnowledgeSourceState.name))
    )
    from app.api.knowledge.sources import source_data

    configured = list(
        session.scalars(
            select(ManagedKnowledgeSource)
            .where(ManagedKnowledgeSource.deleted_at.is_(None))
            .order_by(ManagedKnowledgeSource.id)
        )
    )
    source_items = (
        [source_data(session, source, rules=rules) for source in configured]
        if configured
        else [
            {
                "name": s.name,
                "category": resolve_category(s.category, rules),
                "url": s.url,
                "status": s.status,
                "enabled": True,
                "last_attempt": iso(s.last_attempt),
                "last_success": iso(s.last_success),
                "item_count": s.item_count,
                "error": s.error,
            }
            for s in sources
        ]
    )
    return {
        "categories": sorted(
            {
                resolve_category(name, rules)
                for name in categories
                if not category_hidden(name, rules)
            }
        ),
        "tag_groups": {
            group: sorted(
                {
                    resolve_category(name, rules)
                    for name in names
                    if not category_hidden(name, rules)
                }
            )
            for group, names in TAG_GROUPS.items()
        },
        "tag_count": len(TAG_TERMS),
        "category_catalog": {
            **{key: value for key, value in catalog.items() if key != "categories"},
            "updated_at": iso(catalog["updated_at"]),
            "remote_count": len(catalog["categories"]),
        },
        "total": session.scalar(select(func.count()).select_from(KnowledgeTopic)),
        "sources": source_items,
        "server_time": iso(utcnow()),
    }


@router.get("/topics/{topic_id}/markdown", response_class=PlainTextResponse)
def export(topic_id: int, session: Session = Depends(get_session)):
    entity = session.get(KnowledgeTopic, topic_id)
    if entity is None:
        raise HTTPException(404, "未找到选题")
    item = serialize(entity, category_rules(session))
    content = (
        f"# {item['title']}\n\n- 内容分类：{item['category']}\n- 类型：{item['topic_kind']}\n"
        f"- 题材地区：{item['region']}\n- 地区判断：{item['region_basis']}\n"
        f"- 来源：{item['source_name']}\n- 链接：{item['source_url']}\n"
        f"- 发布日期：{item['published_at'] or '原来源未提供'}\n\n"
        f"## 摘要（来源摘录）\n\n{item['summary']}\n\n"
        f"## 视频切入角度（规则建议）\n\n{item['video_angle']}\n"
    )
    return PlainTextResponse(
        content, headers={"Content-Disposition": f'attachment; filename="topic-{topic_id}.md"'}
    )


@router.get("/hotlists")
def hotlists(
    region: Literal["国内", "国外"] | None = None, session: Session = Depends(get_session)
):
    from app.api.knowledge.sources import source_data
    from app.models import HotListSnapshot
    from app.utils.time import iso

    result = []
    for source in session.scalars(
        select(ManagedKnowledgeSource)
        .where(
            ManagedKnowledgeSource.adapter == "hotlist", ManagedKnowledgeSource.deleted_at.is_(None)
        )
        .order_by(ManagedKnowledgeSource.id)
    ):
        snapshot = session.get(HotListSnapshot, source.source_key)
        result.append(
            {
                **source_data(session, source),
                "observed_at": iso(snapshot.observed_at) if snapshot else None,
                "items": snapshot.entries if snapshot else [],
            }
        )
    from app.core.hot_platforms import HOT_PLATFORM_CATALOG, platform_for_source

    configured = list(
        session.scalars(
            select(ManagedKnowledgeSource)
            .where(
                ManagedKnowledgeSource.adapter == "hotlist",
                ManagedKnowledgeSource.deleted_at.is_(None),
            )
            .order_by(ManagedKnowledgeSource.id)
        )
    )
    by_id = {source.id: source for source in configured}
    grouped = {}
    custom = []
    for item in result:
        key = platform_for_source(by_id[item["id"]])
        if key:
            grouped.setdefault(key, []).append(item)
        else:
            custom.append(item)
    platforms = []
    for platform in HOT_PLATFORM_CATALOG:
        if region and platform["region"] != region:
            continue
        candidates = grouped.get(platform["id"], [])
        # 优先显示有榜单的可用来源，同一平台不因备用接口重复出现。
        selected = (
            max(
                candidates,
                key=lambda source: (
                    bool(source["items"]),
                    source["enabled"],
                    source["observed_at"] or "",
                ),
            )
            if candidates
            else None
        )
        platforms.append(
            {
                **{key: value for key, value in platform.items() if key != "aliases"},
                "connection_status": "configured" if selected else "reserved",
                "source_id": selected["id"] if selected else None,
                "source_name": selected["name"] if selected else None,
                "source_count": len(candidates),
                "enabled": selected["enabled"] if selected else False,
                "status": selected["status"] if selected else "reserved",
                "error": selected["error"] if selected else None,
                "observed_at": selected["observed_at"] if selected else None,
                "items": selected["items"] if selected else [],
            }
        )
    # 管理员自建且未关联目录的平台也继续可见，不因预置目录覆盖而丢失。
    for item in custom:
        source = by_id[item["id"]]
        if region and source.region != region:
            continue
        platforms.append(
            {
                **item,
                "id": f"custom:{source.id}",
                "region": source.region,
                "category": source.category,
                "source_id": source.id,
                "source_name": source.name,
                "source_count": 1,
                "connection_status": "configured",
            }
        )
    return {
        "items": [item for item in result if not region or by_id[item["id"]].region == region],
        "platforms": platforms,
        "platform_count": len(platforms),
        "reserved_count": sum(p["connection_status"] == "reserved" for p in platforms),
    }
