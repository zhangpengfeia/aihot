"""验证识别、增长基线、历史不可变及 API 边界，不依赖真实 GitHub。"""

from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable

from app.core.config import Settings
from app.core.database import Base, get_session
from app.infrastructure.github import GitHubClient, classify
from app.main import app
from app.models import Run, Snapshot
from app.services.skills.collector import persist
from app.utils.time import time_slot


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def repo(stars=100):
    return {
        "id": 1,
        "full_name": "example/agent-skills",
        "description": "Skill examples",
        "stargazers_count": stars,
        "forks_count": 10,
        "language": "Python",
    }


def add_run(db, at, stars=100, name=None):
    run = Run(slot=time_slot(at), started_at=at)
    db.add(run)
    db.flush()
    data = repo(stars)
    if name:
        data["full_name"] = name
    persist(db, run.id, 1, [(data, f"README {stars}", "测试依据", at)])
    db.commit()
    return run


def test_classifier_excludes_unrelated_and_forks():
    assert classify({"full_name": "school/math-skills"}, "Learning mathematics") is None
    assert classify(repo(), "Use SKILL.md") == "README 提及 SKILL.md"
    assert classify({**repo(), "fork": True}, "SKILL.md") is None
    assert classify({**repo(), "archived": True}, "SKILL.md") is None


def test_history_growth_and_name_change(db):
    start = datetime(2026, 10, 1, 0)
    first = add_run(db, start)
    add_run(db, start + timedelta(hours=1), 110)
    latest = add_run(db, start + timedelta(hours=24), 90, "new-owner/skills")
    early = db.scalar(select(Snapshot).where(Snapshot.run_id == first.id))
    current = db.scalar(select(Snapshot).where(Snapshot.run_id == latest.id))
    assert early.delta_24h is None
    assert current.delta_24h == -10  # 不把负增长截断为零。
    assert current.baseline_at == start
    assert early.full_name == "example/agent-skills"
    assert early.readme == "README 100"
    add_run(db, start + timedelta(hours=60), 200)
    assert db.scalar(select(Snapshot).order_by(Snapshot.id.desc())).delta_24h is None


def test_api_history_date_and_failed_run(db):
    at = datetime(2026, 10, 1, 18)  # 北京时间 10 月 2 日。
    good = add_run(db, at)
    failed = Run(slot=at + timedelta(minutes=30), started_at=at, status="failed")
    db.add(failed)
    db.commit()
    app.dependency_overrides[get_session] = lambda: db
    try:
        client = TestClient(app)
        assert client.get("/api/rankings").json()["run"]["id"] == good.id
        assert client.get("/api/skills?category=其他").json()["total"] == 1
        assert client.get("/api/skills?category=字幕").json()["total"] == 0
        assert client.get("/api/skills?q=example").json()["total"] == 1
        assert client.get("/api/rankings?kind=wrong").status_code == 422
        assert client.get(f"/api/rankings?run_id={failed.id}").status_code == 409
        assert len(client.get("/api/runs?day=2026-10-02").json()) == 2
        assert client.get("/api/runs?day=2026-10-01").json() == []
        assert client.get("/api/snapshots/9999").status_code == 404
        snapshot_id = client.get("/api/rankings").json()["items"][0]["id"]
        response = client.get(f"/api/snapshots/{snapshot_id}/markdown")
        assert "README 100" in response.text
        assert "attachment;" in response.headers["content-disposition"]
    finally:
        app.dependency_overrides.clear()


def test_atomic_rollback(db):
    run = Run(slot=datetime(2026, 10, 3), started_at=datetime(2026, 10, 3))
    db.add(run)
    db.commit()
    run_id = run.id
    with pytest.raises(KeyError):
        persist(
            db, run_id, 2, [(repo(), "one", "test", run.slot), ({"id": 2}, "bad", "test", run.slot)]
        )
    db.rollback()
    assert db.scalar(select(Snapshot)) is None
    assert db.get(Run, run_id).status == "running"


def test_mysql_schema_compiles():
    statements = [
        str(CreateTable(t).compile(dialect=mysql.dialect())) for t in Base.metadata.sorted_tables
    ]
    assert any("MEDIUMTEXT" in sql for sql in statements)


def test_github_limit_and_not_found():
    client = GitHubClient(Settings(request_interval=0))
    client.client.close()
    client.client = httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429 if request.url.path == "/limited" else 404)
        ),
    )
    assert client.get("/missing") is None
    with pytest.raises(RuntimeError, match="限流"):
        client.get("/limited")
    client.close()


def test_half_hour_slot():
    assert time_slot(datetime(2026, 10, 30, 10, 59, 12)).minute == 30
    assert time_slot(datetime(2026, 10, 30, 10, 2)).minute == 0
