"""采集服务：网络请求在事务外执行，完整榜单在单个事务内提交。"""

import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.infrastructure.github import GitHubClient, classify
from app.models import Ranking, Repository, Run, Snapshot
from app.services.skills.analysis import analyze_project
from app.services.skills.metadata import extract_metadata
from app.services.storage import incoming_size, storage_guard
from app.utils.time import utcnow, week_slot

logger = logging.getLogger(__name__)


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


def calculate_week_growth(session, repo_id, stars, observed):
    target = observed - timedelta(days=7)
    baseline = session.scalar(
        select(Snapshot)
        .where(
            Snapshot.repo_id == repo_id,
            Snapshot.observed_at <= target,
            Snapshot.observed_at >= target - timedelta(days=1),
        )
        .order_by(Snapshot.observed_at.desc())
        .limit(1)
    )
    return (stars - baseline.stars, baseline.observed_at) if baseline else (None, None)


def persist(session: Session, run_id: int, candidates: int, records: list[tuple], analyzer=None):
    """保存观测及两种 Top 100，所有历史标题、README、指标随快照一起冻结。"""
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
        weekly_delta, weekly_baseline = calculate_week_growth(
            session, repo["id"], repo["stargazers_count"], observed
        )
        analysis = analyze_project(repo, readme, analyzer)
        snapshot = Snapshot(
            analysis=analysis,
            delta_7d=weekly_delta,
            baseline_7d_at=weekly_baseline,
            categories=analysis["tags"] or categories,
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
            [s for s in snapshots if s.delta_7d is not None],
            key=lambda s: (-s.delta_7d, -s.stars, s.repo_id),
        ),
    }
    for kind, items in orders.items():
        for position, snapshot in enumerate(items[:100], 1):
            session.add(
                Ranking(run_id=run_id, snapshot_id=snapshot.id, kind=kind, position=position)
            )
    run = session.get(Run, run_id)
    run.status, run.finished_at = "success", utcnow()
    run.candidate_count, run.matched_count = candidates, len(snapshots)
    run.error = None


def collect(settings: Settings, engine=None, client=None, progress=None, analyzer=None) -> bool:
    """MySQL 连接级互斥锁跨进程防重；相同周的成功批次不会重复写入。"""
    from app.core.database import get_engine

    progress = progress or (lambda percent, message: None)
    engine = engine or get_engine()
    with engine.connect() as lock_connection:
        locked = lock_connection.scalar(text("SELECT GET_LOCK('aihot.collect', 0)"))
        if locked != 1:
            logger.info("跳过 GitHub 采集：已有任务正在执行")
            return False
        github = None
        try:
            factory = sessionmaker(engine, expire_on_commit=False)
            now = utcnow()
            slot = week_slot(now)
            with factory.begin() as session:
                run = session.scalar(
                    select(Run).where(
                        Run.scope == "ai-production-weekly-v1",
                        Run.slot >= slot,
                        Run.slot < slot + timedelta(days=7),
                    )
                )
                if run and run.status == "success":
                    logger.info("跳过 GitHub 采集：当前周已有成功批次，批次=%s", run.id)
                    return False
                if not run:
                    run_slot = now.replace(microsecond=0)
                    while session.scalar(select(Run.id).where(Run.slot == run_slot)) is not None:
                        run_slot += timedelta(seconds=1)
                    run = Run(slot=run_slot, scope="ai-production-weekly-v1", started_at=now)
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
            started = time.monotonic()
            processed = skipped = unmatched = 0
            records = []
            logger.info(
                "GitHub 采集开始：批次=%s，搜索关键词=%s，候选上限=%s，历史跟踪=%s",
                run_id,
                len(settings.search_queries),
                settings.candidate_limit,
                len(tracked),
            )
            github = client or GitHubClient(settings)
            try:
                with storage_guard(engine, settings):
                    pass
                progress(0, "正在搜索 GitHub 项目")
                discovered = github.discover(settings.search_queries)
                # 按累计 Star 选候选，榜单只代表已采集且通过规则识别的范围。
                popular = sorted(discovered, key=lambda r: (-r["stargazers_count"], r["id"]))[
                    : settings.candidate_limit
                ]
                pool = {r["id"]: r for r in popular}
                selected_count = len(pool)
                # 继续观察历史项目，避免仓库掉出搜索窗口后失去增长基线。
                # 候选也重新获取统计，避免以搜索索引的缓存值计算增长。
                for repo in tracked:
                    pool.setdefault(repo.id, {"full_name": repo.full_name})
                logger.info(
                    "GitHub 搜索完成：发现=%s，选中候选=%s，历史补充=%s，待检查总数=%s",
                    len(discovered),
                    selected_count,
                    len(pool) - selected_count,
                    len(pool),
                )
                for index, candidate in enumerate(pool.values(), 1):
                    logger.info(
                        "GitHub 正在采集 %s/%s：%s", index, len(pool), candidate["full_name"]
                    )
                    repo = github.get(f"/repos/{candidate['full_name']}")
                    if not repo or repo.get("archived") or repo.get("fork"):
                        skipped += 1
                    else:
                        observed = utcnow()
                        readme = github.readme(repo["full_name"])
                        evidence = classify(repo, readme)
                        if evidence:
                            records.append((repo, readme, evidence, observed))
                        else:
                            unmatched += 1
                    processed += 1
                    progress(
                        int(processed / len(pool) * 95),
                        f"已检查 {processed}/{len(pool)}：{candidate['full_name']}，匹配 {len(records)}，跳过 {skipped}",
                    )
                    logger.info(
                        "GitHub 采集进度：已检查=%s/%s，匹配=%s，未匹配=%s，跳过=%s，耗时=%.1f秒",
                        processed,
                        len(pool),
                        len(records),
                        unmatched,
                        skipped,
                        time.monotonic() - started,
                    )
                if not records:
                    raise RuntimeError("本轮未找到匹配项目，保留上一期成功榜单")
                logger.info("GitHub 开始入库：批次=%s，待保存项目=%s", run_id, len(records))
                progress(95, f"正在入库：{len(records)} 个项目")
                with storage_guard(engine, settings, incoming_size(records)):
                    with factory.begin() as session:
                        persist(session, run_id, len(pool), records, analyzer)
                logger.info(
                    "GitHub 采集成功：批次=%s，候选=%s，已检查=%s，已入库=%s，未匹配=%s，跳过=%s，耗时=%.1f秒",
                    run_id,
                    len(pool),
                    processed,
                    len(records),
                    unmatched,
                    skipped,
                    time.monotonic() - started,
                )
                return True
            except Exception as exc:
                logger.error(
                    "GitHub 采集失败：批次=%s，已检查=%s，已匹配=%s，未匹配=%s，跳过=%s，耗时=%.1f秒，错误=%s，本轮未发布",
                    run_id,
                    processed,
                    len(records),
                    unmatched,
                    skipped,
                    time.monotonic() - started,
                    type(exc).__name__,
                )
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
