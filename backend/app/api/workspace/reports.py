"""工作空间reports接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import same_origin_writes
from app.core.auth import require_admin
from app.core.config import get_settings
from app.core.database import get_session
from app.models import (
    KnowledgeSourceState,
    Ranking,
    Run,
    Snapshot,
)
from app.runtime.github_worker import next_collection_at
from app.services.storage import storage_status
from app.utils.time import iso, utcnow

router = APIRouter(prefix="/api/workspace", dependencies=[Depends(same_origin_writes)])


@router.get("/daily-summary")
def daily_summary(db: Session = Depends(get_session)):
    from app.services.skills.serialization import run_data, snapshot_data

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
            .where(Snapshot.run_id == runs[0].id, Snapshot.delta_7d > 0)
            .order_by(Snapshot.delta_7d.desc(), Snapshot.repo_id)
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


@router.get("/collection-status", dependencies=[Depends(require_admin)])
def collection_status(db: Session = Depends(get_session)):
    from app.services.skills.serialization import run_data

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
    from app.api.knowledge.sources import sources as managed_sources
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
        "storage": storage_status(db, get_settings()),
        "schedule": "每天 00:00",
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
