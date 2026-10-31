"""验证进度计数与实际入库一致，中途失败不会输出成功。"""

import logging

import httpx
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base
from app.models import Run, Snapshot
from app.services.skills.collector import collect


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def register_locks(connection, _):
        connection.create_function("GET_LOCK", 2, lambda *args: 1)
        connection.create_function("RELEASE_LOCK", 1, lambda *args: 1)

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


class FakeGitHub:
    def __init__(self, fail=False):
        self.fail = fail
        self.repos = [
            {"id": index, "full_name": name, "stargazers_count": 100 - index, "forks_count": 0}
            for index, name in enumerate(
                ["example/ai-text-to-video", "example/other", "example/gone"], 1
            )
        ]

    def discover(self, queries):
        return self.repos

    def get(self, path):
        if path.endswith("/gone"):
            return None
        return next(repo for repo in self.repos if path == f"/repos/{repo['full_name']}")

    def readme(self, name):
        if self.fail and name.endswith("/other"):
            raise httpx.ReadTimeout("temporary failure")
        return ""


def test_progress_reports_counts_after_commit(engine, caplog):
    caplog.set_level(logging.INFO)
    assert collect(Settings(candidate_limit=100), engine, FakeGitHub())
    with Session(engine) as session:
        assert session.scalar(select(Run)).status == "success"
        assert len(list(session.scalars(select(Snapshot)))) == 1
    assert "待检查总数=3" in caplog.text
    assert "已检查=3/3，匹配=1，未匹配=1，跳过=1" in caplog.text
    assert "已入库=1" in caplog.text
    assert caplog.text.index("开始入库") < caplog.text.index("采集成功")


def test_failure_reports_partial_progress_without_success(engine, caplog):
    caplog.set_level(logging.INFO)
    with pytest.raises(httpx.ReadTimeout):
        collect(Settings(candidate_limit=100), engine, FakeGitHub(fail=True))
    with Session(engine) as session:
        assert session.scalar(select(Run)).status == "failed"
        assert session.scalar(select(Snapshot)) is None
    assert "已检查=1，已匹配=1" in caplog.text
    assert "本轮未发布" in caplog.text
    assert "采集成功" not in caplog.text


def test_weekly_dedup_preserves_legacy_history(engine, monkeypatch):
    from datetime import datetime, timedelta

    from app.services.skills import collector

    now = datetime(2026, 11, 1, 16)
    monkeypatch.setattr(collector, "utcnow", lambda: now)
    with Session(engine) as db:
        legacy = Run(slot=now, started_at=now, status="success")
        db.add(legacy)
        db.commit()
    assert collect(Settings(candidate_limit=100), engine, FakeGitHub())
    assert not collect(Settings(candidate_limit=100), engine, FakeGitHub())
    monkeypatch.setattr(collector, "utcnow", lambda: now + timedelta(days=7))
    assert collect(Settings(candidate_limit=100), engine, FakeGitHub())
    with Session(engine) as db:
        runs = list(db.scalars(select(Run).order_by(Run.id)))
        assert len(runs) == 3
        assert runs[0].scope is None
        assert runs[0].status == "success"
        assert all(run.scope == "ai-production-weekly-v1" for run in runs[1:])
