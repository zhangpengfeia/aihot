"""Skill 批次与快照的响应数据映射。"""

from app.models import Run, Snapshot
from app.utils.time import iso


def run_data(run: Run):
    return {
        "id": run.id,
        "slot": iso(run.slot),
        "scope": run.scope,
        "status": run.status,
        "started_at": iso(run.started_at),
        "finished_at": iso(run.finished_at),
        "candidate_count": run.candidate_count,
        "matched_count": run.matched_count,
        "error": run.error,
    }


def snapshot_data(s: Snapshot):
    """列表/榜单轻量映射，不含安装说明等大字段；详情用 snapshot_detail_data。"""
    return {
        "id": s.id,
        "repo_id": s.repo_id,
        "full_name": s.full_name,
        "url": f"https://github.com/{s.full_name}",
        "description": s.description,
        "stars": s.stars,
        "forks": s.forks,
        "delta_24h": s.delta_24h,
        "delta_7d": s.delta_7d,
        "baseline_7d_at": iso(s.baseline_7d_at),
        "analysis": s.analysis,
        "baseline_at": iso(s.baseline_at),
        "observed_at": iso(s.observed_at),
        "language": s.language,
        "license": s.license,
        "pushed_at": s.pushed_at,
        "evidence": s.evidence,
        "categories": s.categories or ["其他"],
    }


def snapshot_detail_data(s: Snapshot):
    """详情映射，追加安装方式；README 由调用方按需附带。"""
    return {
        **snapshot_data(s),
        "installation": s.installation or "历史资料未提取安装方式，请查看 README。",
    }

