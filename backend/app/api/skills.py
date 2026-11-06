"""Skill 项目资料、榜单与快照导出接口。"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, defer

from app.core.database import get_session
from app.models import Ranking, Run, Snapshot
from app.services.skills.serialization import run_data, snapshot_data
from app.utils.time import SHANGHAI, iso

router = APIRouter()


@router.get("/api/runs")
def runs(
    day: date | None = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """按北京时间日期查询历史批次，包含失败状态，支持分页。"""
    query = select(Run)
    if day:
        start = datetime.combine(day, time.min, SHANGHAI).astimezone(UTC)
        query = query.where(
            Run.slot >= start.replace(tzinfo=None),
            Run.slot < (start + timedelta(days=1)).replace(tzinfo=None),
        )
    return [
        run_data(r)
        for r in session.scalars(query.order_by(Run.slot.desc()).offset(offset).limit(limit))
    ]


@router.get("/api/rankings")
def rankings(
    kind: Literal["stars", "growth"] = "stars",
    run_id: int | None = None,
    session: Session = Depends(get_session),
):
    """未指定批次时返回最近成功榜单，采集失败不会覆盖此前数据。"""
    run = (
        session.get(Run, run_id)
        if run_id
        else session.scalar(
            select(Run)
            .where(Run.status == "success", Run.scope == "ai-video-weekly-v2")
            .order_by(Run.slot.desc())
            .limit(1)
        )
    )
    if run is None:
        return {"run": None, "items": []}
    if run.status != "success":
        raise HTTPException(409, "该批次未成功完成，请选择其他批次")
    rows = session.execute(
        select(Ranking, Snapshot)
        .join(Snapshot, Ranking.snapshot_id == Snapshot.id)
        .where(Ranking.run_id == run.id, Ranking.kind == kind)
        .order_by(Ranking.position)
        .options(defer(Snapshot.readme), defer(Snapshot.installation))
    )
    return {
        "run": run_data(run),
        "items": [{"rank": r.position, **snapshot_data(s)} for r, s in rows],
    }


def find_snapshot(session: Session, snapshot_id: int) -> Snapshot:
    snapshot = session.get(Snapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(404, "未找到项目快照")
    return snapshot


@router.get("/api/snapshots/{snapshot_id}")
def detail(snapshot_id: int, session: Session = Depends(get_session)):
    s = find_snapshot(session, snapshot_id)
    return {**snapshot_data(s), "readme": s.readme}


@router.get("/api/snapshots/{snapshot_id}/markdown", response_class=PlainTextResponse)
def markdown(snapshot_id: int, session: Session = Depends(get_session)):
    s = find_snapshot(session, snapshot_id)
    analysis = s.analysis or {}
    analysis_label = "大模型分析" if analysis.get("source") == "llm" else "资料规则初判"
    content = (
        f"# {s.full_name}\n\n{s.description}\n\n"
        f"- 来源：https://github.com/{s.full_name}\n"
        f"- 观测时间：{iso(s.observed_at)}\n- Stars：{s.stars}\n"
        f"- 7 天增长：{s.delta_7d if s.delta_7d is not None else '基线不足'}\n"
        f"- 增长基线：{iso(s.baseline_7d_at) or '无'}\n"
        f"- 识别依据：{s.evidence}\n- 许可证：{s.license or '未声明'}\n\n"
        f"## 核心功能（{analysis_label}）\n\n{chr(10).join(analysis.get('core_features', [])) or '待分析'}\n\n"
        f"## 适用场景\n\n{chr(10).join(analysis.get('use_cases', [])) or '待分析'}\n\n"
        f"## 知识内容方向建议\n\n{chr(10).join(analysis.get('knowledge_suggestions', [])) or '待分析'}\n\n"
        f"## 安装方式（原文摘录，未经执行验证）\n\n{s.installation or '请查看 README'}\n\n"
        f"## 仓库 README（作者原文，未经实测）\n\n{s.readme}\n"
    )
    return PlainTextResponse(
        content, headers={"Content-Disposition": f'attachment; filename="skill-{s.repo_id}.md"'}
    )


@router.get("/api/skills")
def skills(
    category: str | None = None,
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """每个仓库展示最近一次有效快照，掉出本期热榜的历史项目仍可搜索。"""
    from sqlalchemy import or_

    from app.services.skills.metadata import extract_metadata

    # 通过「最新」标志直接过滤，避免 MAX(id) GROUP BY repo_id 全表扫描。
    query = (
        select(Snapshot)
        .where(Snapshot.is_latest.is_(True))
        .order_by(Snapshot.stars.desc(), Snapshot.repo_id)
        .options(defer(Snapshot.readme))
    )
    if q.strip():
        query = query.where(
            or_(
                Snapshot.full_name.contains(q.strip(), autoescape=True),
                Snapshot.description.contains(q.strip(), autoescape=True),
            )
        )
    # 多标签分类数量较小，在已缩小到「每个仓库最新快照」的集合上应用层精确匹配，
    # 避免不同数据库 JSON 比较语义不一致。
    found = []
    for snapshot in session.scalars(query):
        item = snapshot_data(snapshot)
        if not snapshot.categories:
            # 旧快照缺分类时按需回填，迁移后正常不会走到这里。
            categories, installation = extract_metadata(
                snapshot.full_name, snapshot.description or "", snapshot.readme or ""
            )
            item["categories"], item["installation"] = categories, installation
        if category and category not in item["categories"] + (item.get("analysis") or {}).get(
            "domains", []
        ):
            continue
        found.append(item)
    start = (page - 1) * page_size
    return {"total": len(found), "items": found[start : start + page_size]}
