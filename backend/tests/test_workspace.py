"""真实路由与数据库验证个人资料、创作流转、榜单差异和采集面板。"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.main import app
from app.models import CreationCard, PersonalItem, Run, Snapshot
from app.runtime.migrations import migrate
from app.services.knowledge.collector import save_topics
from app.services.knowledge.normalization import parse_feed
from app.services.knowledge.sources import FeedSource
from app.services.skills.collector import persist

AT = datetime(2026, 10, 28, 18)


def make_run(db, at, repositories):
    run = Run(slot=at, started_at=at)
    db.add(run)
    db.flush()
    records = [
        (
            {"id": repo_id, "full_name": name, "stargazers_count": stars, "forks_count": 1},
            "# SKILL.md",
            "test",
            at,
        )
        for repo_id, name, stars in repositories
    ]
    persist(db, run.id, len(records), records)
    db.commit()
    return run


@pytest.fixture
def context():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        make_run(db, AT, [(1, "owner/one", 100), (2, "owner/two", 50)])
        save_topics(
            db,
            parse_feed(
                b"<rss><channel><item><title>Science</title><link>https://example.com/article</link></item></channel></rss>",
                FeedSource(name="Test", url="https://example.com/feed", category="自然"),
            ),
            AT,
        )
        db.commit()
        app.dependency_overrides[get_session] = lambda: db
        with TestClient(app) as client:
            yield client, db, engine
        app.dependency_overrides.clear()
    engine.dispose()


def test_favorite_note_survive_unfavorite_and_repo_rename(context):
    client, db, _ = context
    path = "/api/workspace/items/repository/1"
    assert client.get(path).json()["favorite"] is False
    assert client.put(path, json={"favorite": True, "note": "体验与创作思路"}).status_code == 200
    assert client.put(path, json={"favorite": True}).json()["note"] == "体验与创作思路"
    assert db.scalar(select(func.count()).select_from(PersonalItem)) == 1
    make_run(db, AT + timedelta(days=1), [(1, "new-owner/renamed", 130)])
    item = client.get(path).json()
    assert item["title"] == "new-owner/renamed"
    assert item["note"] == "体验与创作思路"
    assert client.get("/api/workspace/items?q=创作").json()["total"] == 1
    client.put(path, json={"favorite": False})
    assert client.get("/api/workspace/items").json()["total"] == 0
    all_records = client.get("/api/workspace/items?all_records=true").json()
    assert all_records["items"][0]["note"] == "体验与创作思路"
    db.expire_all()
    assert client.get(path).json()["note"] == "体验与创作思路"
    assert client.delete(path).status_code == 204
    assert client.get(path).json()["note"] == ""
    assert db.scalar(select(func.count()).select_from(Snapshot)) == 3


def test_topic_favorite_filter_pagination_and_validation(context):
    client, _, _ = context
    client.put("/api/workspace/items/repository/1", json={"favorite": True})
    client.put("/api/workspace/items/topic/1", json={"favorite": True, "note": "a"})
    assert client.get("/api/workspace/items?kind=topic").json()["total"] == 1
    assert len(client.get("/api/workspace/items?page_size=1").json()["items"]) == 1
    assert len(client.get("/api/workspace/items?page=3&page_size=1").json()["items"]) == 0
    assert client.put("/api/workspace/items/topic/99", json={"favorite": True}).status_code == 404
    assert client.put("/api/workspace/items/topic/1", json={"note": "x" * 10001}).status_code == 422
    assert client.get("/api/workspace/items?kind=invalid").status_code == 422


def test_cards_idempotent_and_all_stages_preserve_script(context):
    client, db, _ = context
    path = "/api/workspace/cards"
    first = client.post(path, json={"topic_id": 1}).json()
    again = client.post(path, json={"topic_id": 1}).json()
    assert first["id"] == again["id"]
    assert db.scalar(select(func.count()).select_from(CreationCard)) == 1
    url = f"{path}/{first['id']}"
    assert (
        client.patch(
            url, json={"script": "开场\n事实与证据", "output_url": "https://example.com/video"}
        ).status_code
        == 200
    )
    for stage in ["待创作", "制作中", "已发布", "待筛选"]:
        item = client.patch(url, json={"stage": stage}).json()
        assert item["stage"] == stage
        assert item["script"] == "开场\n事实与证据"
        assert item["output_url"] == "https://example.com/video"
    client.post(path, json={"topic_id": 1})
    db.expire_all()
    assert client.get(path).json()["items"][0]["script"] == "开场\n事实与证据"
    assert client.get(path + "?q=no-match").json()["items"] == []
    assert client.patch(url, json={"output_url": ""}).json()["output_url"] == ""
    assert client.delete(url).status_code == 204
    assert client.get(path).json()["items"] == []
    assert client.get("/api/knowledge/topics").json()["total"] == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"stage": "invalid"},
        {"script": "a" * 100001},
        {"output_url": "javascript:alert(1)"},
        {"output_url": "file:///tmp/video"},
        {"output_url": "https://user:pass@example.com"},
        {"output_url": "https://exa mple.com"},
    ],
)
def test_bad_card_inputs(context, fields):
    client, _, _ = context
    item = client.post("/api/workspace/cards", json={"topic_id": 1}).json()
    assert client.patch(f"/api/workspace/cards/{item['id']}", json=fields).status_code == 422
    assert client.post("/api/workspace/cards", json={"topic_id": 999}).status_code == 404
    assert client.patch("/api/workspace/cards/999", json={"stage": "已发布"}).status_code == 404


def test_summary_ignores_failed_runs_and_uses_stable_ids(context):
    client, db, _ = context
    first = client.get("/api/workspace/daily-summary").json()
    assert first["previous"] is None
    assert first["new_entries"] == []
    assert first["growth"] == []
    make_run(
        db,
        AT + timedelta(days=1),
        [(1, "renamed/one", 110), (2, "owner/two", 300), (3, "owner/new", 150)],
    )
    db.add(
        Run(
            slot=AT + timedelta(days=2),
            started_at=AT + timedelta(days=2),
            status="failed",
            error="rate limit",
        )
    )
    db.commit()
    data = client.get("/api/workspace/daily-summary").json()
    assert [item["repo_id"] for item in data["new_entries"]] == [3]
    assert data["risers"][0]["repo_id"] == 2
    assert data["risers"][0]["previous_rank"] == 2
    assert data["risers"][0]["rank_change"] == 1
    assert [item["repo_id"] for item in data["growth"]] == [2, 1]
    assert data["growth"][0]["delta_24h"] == 250
    assert data["current"]["status"] == "success"


def test_status_and_empty_summary(context, monkeypatch):
    from app.api.workspace import reports as workspace_api

    client, db, _ = context
    monkeypatch.setattr(workspace_api, "utcnow", lambda: datetime(2026, 10, 30, 18, 1))
    db.add(
        Run(
            slot=AT + timedelta(days=1),
            started_at=AT + timedelta(days=1),
            status="failed",
            error="rate limit",
        )
    )
    db.commit()
    status = client.get("/api/workspace/collection-status").json()
    assert status["latest"]["status"] == "failed"
    assert status["last_success"]["status"] == "success"
    assert status["last_failure"]["error"] == "rate limit"
    assert status["next_scheduled_at"] == "2026-10-31T18:00:00+00:00"
    assert status["total_successful_runs"] == 1
    for run in db.scalars(select(Run)):
        run.status = "failed"
    db.commit()
    data = client.get("/api/workspace/daily-summary").json()
    assert data["current"] is None
    assert data["new_entries"] == []


def test_migration_creates_new_tables_repeatedly(context):
    client, _, engine = context
    CreationCard.__table__.drop(engine)
    PersonalItem.__table__.drop(engine)
    migrate(engine)
    assert client.put("/api/workspace/items/topic/1", json={"favorite": True}).status_code == 200
    card = client.post("/api/workspace/cards", json={"topic_id": 1}).json()
    client.patch(f"/api/workspace/cards/{card['id']}", json={"script": "迁移保留脚本"})
    migrate(engine)
    assert client.get("/api/workspace/items").json()["total"] == 1
    assert client.get("/api/workspace/cards").json()["items"][0]["script"] == "迁移保留脚本"


def test_cross_origin_writes_rejected(context):
    client, _, _ = context
    path = "/api/workspace/items/topic/1"
    assert (
        client.put(
            path, json={"favorite": True}, headers={"Origin": "https://other.example"}
        ).status_code
        == 403
    )
    assert (
        client.put(
            path, json={"favorite": True}, headers={"Origin": "http://testserver"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/workspace/cards", content='{"topic_id":1}', headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )
