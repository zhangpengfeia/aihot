"""采集服务：网络请求在事务外执行，完整榜单在单个事务内提交。"""

from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.github import GitHubClient, classify
from app.models import Ranking, Repository, Run, Snapshot
from app.skill_metadata import extract_metadata
from app.time_utils import time_slot, utcnow


def calculate_growth(session: Session, repo_id: int, stars: int, observed: datetime):
    """选择 24 小时前、最多再早 2 小时的基线，缺失时不捏造增量。

    保留负增长，避免把取消 Star 的真实情况变成零增长。
    """
    target = observed - timedelta(hours=24)
    baseline = session.scalar(
        select(Snapshot)
        .where(
            Snapshot.repo_id == repo_id,
            Snapshot.observed_at <= target,
            Snapshot.observed_at >= target - timedelta(hours=2),
        )
        .order_by(Snapshot.observed_at.desc())
        .limit(1)
    )
    if baseline is None:
        return None, None
    return stars - baseline.stars, baseline.observed_at


def persist(session: Session, run_id: int, candidates: int, records: list[tuple]):
    """保存观测及两种 Top 20，所有历史标题、README、指标随快照一起冻结。"""
    snapshots = []
    for repo, readme, evidence, observed in records:
        entity = session.get(Repository, repo["id"])
        if entity is None:
            entity = Repository(id=repo["id"], full_name=repo["full_name"], last_seen=observed)
            session.add(entity)
        entity.full_name, entity.last_seen = repo["full_name"], observed
        session.flush()
        delta, baseline = calculate_growth(session, repo["id"], repo["stargazers_count"], observed)
        categories, installation = extract_metadata(
            repo["full_name"], repo.get("description") or "", readme
        )
        snapshot = Snapshot(
            categories=categories,
            installation=installation,
            run_id=run_id,
            repo_id=repo["id"],
            observed_at=observed,
            full_name=repo["full_name"],
            description=repo.get("description") or "",
            stars=repo["stargazers_count"],
            forks=repo["forks_count"],
            language=repo.get("language"),
            license=(repo.get("license") or {}).get("spdx_id"),
            pushed_at=repo.get("pushed_at"),
            readme=readme,
            evidence=evidence,
            delta_24h=delta,
            baseline_at=baseline,
        )
        session.add(snapshot)
        snapshots.append(snapshot)
    session.flush()
    orders = {
        "stars": sorted(snapshots, key=lambda s: (-s.stars, s.repo_id)),
        "growth": sorted(
            [s for s in snapshots if s.delta_24h is not None],
            key=lambda s: (-s.delta_24h, -s.stars, s.repo_id),
        ),
    }
    for kind, items in orders.items():
        for position, snapshot in enumerate(items[:20], 1):
            session.add(
                Ranking(run_id=run_id, snapshot_id=snapshot.id, kind=kind, position=position)
            )
    run = session.get(Run, run_id)
    run.status, run.finished_at = "success", utcnow()
    run.candidate_count, run.matched_count = candidates, len(snapshots)
    run.error = None


def collect(settings: Settings, engine=None, client=None) -> bool:
    """MySQL 连接级互斥锁跨进程防重；相同半小时的成功批次不会重复写入。"""
    from app.db import get_engine

    engine = engine or get_engine()
    with engine.connect() as lock_connection:
        locked = lock_connection.scalar(text("SELECT GET_LOCK('aihot.collect', 0)"))
        if locked != 1:
            return False
        github = None
        try:
            factory = sessionmaker(engine, expire_on_commit=False)
            slot = time_slot(utcnow())
            with factory.begin() as session:
                run = session.scalar(select(Run).where(Run.slot == slot))
                if run and run.status == "success":
                    return False
                if not run:
                    run = Run(slot=slot, started_at=utcnow())
                    session.add(run)
                    session.flush()
                run.status, run.started_at, run.error = "running", utcnow(), None
                run_id = run.id
                tracked = list(
                    session.scalars(
                        select(Repository)
                        .order_by(Repository.last_seen.desc(), Repository.id)
                        .limit(settings.tracked_limit)
                    )
                )
            github = client or GitHubClient(settings)
            try:
                discovered = github.discover(settings.search_queries)
                # 选择累计热度候选及最近更新候选，二者各占一半后去重。
                half = settings.candidate_limit // 2
                popular = sorted(discovered, key=lambda r: -r["stargazers_count"])[:half]
                recent = sorted(discovered, key=lambda r: r.get("pushed_at") or "", reverse=True)[
                    : settings.candidate_limit - half
                ]
                pool = {r["id"]: r for r in popular + recent}
                # 继续观察历史项目，避免仓库掉出搜索窗口后失去增长基线。
                # 候选也重新获取统计，避免以搜索索引的缓存值计算增长。
                for repo in tracked:
                    pool.setdefault(repo.id, {"full_name": repo.full_name})
                records = []
                for candidate in pool.values():
                    repo = github.get(f"/repos/{candidate['full_name']}")
                    if not repo or repo.get("archived") or repo.get("fork"):
                        continue
                    observed = utcnow()
                    readme = github.readme(repo["full_name"])
                    evidence = classify(repo, readme)
                    if evidence:
                        records.append((repo, readme, evidence, observed))
                if not records:
                    raise RuntimeError("本轮未找到匹配项目，保留上一期成功榜单")
                with factory.begin() as session:
                    persist(session, run_id, len(pool), records)
                return True
            except Exception as exc:
                with factory.begin() as session:
                    run = session.get(Run, run_id)
                    run.status, run.finished_at = "failed", utcnow()
                    # 只存错误类别及我们自己的错误信息，避免外部异常 URL 暴露凭证。
                    run.error = (
                        str(exc)[:450] if isinstance(exc, RuntimeError) else type(exc).__name__
                    )
                raise
        finally:
            if github and client is None:
                github.close()
            lock_connection.execute(text("SELECT RELEASE_LOCK('aihot.collect')"))
