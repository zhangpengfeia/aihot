"""来源配置、采集行为与分类查询的完整路由验证。"""

from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_session
from app.core.sources import FeedSource
from app.infrastructure.feed_http import get_feed_fetcher
from app.main import app
from app.models import KnowledgeSourceState, KnowledgeTopic, ManagedKnowledgeSource
from app.runtime.migrations import migrate
from app.services.knowledge.categories import get_category_catalog
from app.services.knowledge.collector import collect_knowledge, save_topics
from app.services.knowledge.management import seed_sources
from app.services.knowledge.normalization import parse_feed

RSS = b"<rss><channel><item><title>Research</title><link>https://example.com/article</link><description>Summary</description></item></channel></rss>"
SOURCES = [
    FeedSource(name="A", url="https://example.com/feed", category="科技"),
    FeedSource(name="B", url="https://example.org/feed", category="技术"),
]


@pytest.fixture
def managed():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def locks(connection, record):
        connection.create_function("GET_LOCK", 2, lambda *args: 1)
        connection.create_function("RELEASE_LOCK", 1, lambda *args: 1)

    Base.metadata.create_all(engine)
    settings = Settings(knowledge_sources=SOURCES)
    with Session(engine) as db:
        seed_sources(db, settings)
        save_topics(db, parse_feed(RSS, SOURCES[0]), datetime(2026, 10, 30))
        save_topics(
            db, parse_feed(RSS.replace(b"/article", b"/other"), SOURCES[1]), datetime(2026, 10, 30)
        )
        db.commit()
        app.dependency_overrides[get_session] = lambda: db
        app.dependency_overrides[get_category_catalog] = lambda: {
            "categories": ["教育", "科技", "技术"],
            "status": "success",
            "source_name": "Test",
            "source_url": "https://example.com",
            "updated_at": None,
            "error": None,
        }
        app.dependency_overrides[get_feed_fetcher] = lambda: lambda url: RSS
        with TestClient(app) as client:
            yield client, db, engine, settings
        app.dependency_overrides.clear()
    engine.dispose()


def test_source_crud_count_and_seed_preserves_edits(managed):
    client, db, _, settings = managed
    items = client.get("/api/knowledge/manage/sources").json()["items"]
    assert [row["collected_count"] for row in items] == [1, 1]
    body = {"name": "New", "url": "https://example.net/rss", "category": "生活"}
    created = client.post("/api/knowledge/manage/sources", json=body)
    assert created.status_code == 201
    assert created.json()["enabled"] is True
    assert created.json()["status"] == "pending"
    assert client.post("/api/knowledge/manage/sources", json=body).status_code == 409
    updated = client.patch(
        "/api/knowledge/manage/sources/1", json={"enabled": False, "name": "A renamed"}
    )
    assert updated.status_code == 200
    seed_sources(db, settings)
    db.commit()
    db.expire_all()
    source = db.get(ManagedKnowledgeSource, 1)
    assert source.name == "A renamed"
    assert source.enabled is False
    assert client.get("/api/knowledge/meta").json()["sources"][0]["enabled"] is False
    assert (
        client.patch(
            "/api/knowledge/manage/sources/1", json={"url": "http://127.0.0.1/feed"}
        ).status_code
        == 422
    )
    assert client.patch("/api/knowledge/manage/sources/1", json={"name": " "}).status_code == 422
    assert (
        client.patch("/api/knowledge/manage/sources/99", json={"enabled": True}).status_code == 404
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/rss",
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/",
        "http://[::1]/",
        "http://user:pass@example.com/",
        "ftp://example.com/rss",
        "https://example.com:9000/rss",
        "http://224.0.0.1/",
    ],
)
def test_source_rejects_unsafe_urls(managed, url):
    client, _, _, _ = managed
    assert (
        client.post(
            "/api/knowledge/manage/sources", json={"name": "Bad", "url": url, "category": "科技"}
        ).status_code
        == 422
    )


def test_collector_reads_database_and_all_disabled_means_no_collection(managed):
    client, db, engine, settings = managed
    client.patch("/api/knowledge/manage/sources/1", json={"enabled": False})
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=RSS)

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        result = collect_knowledge(settings, engine, http)
        assert result["sources"] == 1
        assert calls == ["https://example.org/feed"]
        client.patch("/api/knowledge/manage/sources/2", json={"enabled": False})
        calls.clear()
        result = collect_knowledge(settings, engine, http)
        assert result == {"sources": 0, "failed": 0, "added": 0}
        assert calls == []
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(KnowledgeTopic)) == 2


def test_preview_never_ingests_and_throttles(managed):
    client, db, _, _ = managed
    before = db.scalar(select(func.count()).select_from(KnowledgeTopic))
    response = client.post("/api/knowledge/manage/sources/1/test", json={})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["item_count"] == 1
    assert response.json()["items"][0]["title"] == "Research"
    assert db.scalar(select(func.count()).select_from(KnowledgeTopic)) == before
    assert db.scalar(select(func.count()).select_from(KnowledgeSourceState)) == 0
    assert client.post("/api/knowledge/manage/sources/1/test", json={}).status_code == 429
    item = client.get("/api/knowledge/manage/sources").json()["items"][0]
    assert item["last_test_count"] == 1
    assert item["collected_count"] == 1


def test_preview_failure_is_saved_without_disabling_source(managed):
    client, db, _, _ = managed
    app.dependency_overrides[get_feed_fetcher] = lambda: lambda url: b"<html>not rss</html>"
    result = client.post("/api/knowledge/manage/sources/1/test", json={}).json()
    assert result["ok"] is False
    assert result["error"]
    db.expire_all()
    source = db.get(ManagedKnowledgeSource, 1)
    assert source.enabled is True
    assert source.last_test_error


def test_merge_filter_export_and_unmerge_preserve_originals(managed):
    client, db, _, _ = managed
    path = "/api/knowledge/manage"
    assert client.get("/api/knowledge/meta").json()["categories"] == ["技术", "科技"]
    response = client.post(path + "/category-merge", json={"source": "技术", "target": "科技"})
    assert response.status_code == 200
    assert client.get("/api/knowledge/meta").json()["categories"] == ["科技"]
    for name in ["科技", "技术"]:
        result = client.get(
            "/api/knowledge/topics", params={"category": name, "page_size": 1}
        ).json()
        assert result["total"] == 2
        assert len(result["items"]) == 1
        assert result["items"][0]["category"] == "科技"
    assert set(db.scalars(select(KnowledgeTopic.category))) == {"科技", "技术"}
    assert "内容分类：科技" in client.get("/api/knowledge/topics/2/markdown").text
    card = client.post("/api/workspace/cards", json={"topic_id": 2}).json()
    assert card["category"] == "科技"
    rows = client.get(path + "/categories").json()["items"]
    assert next(row for row in rows if row["name"] == "科技")["total_count"] == 2
    assert next(row for row in rows if row["name"] == "教育")["total_count"] == 0
    assert client.post(path + "/category-unmerge", json={"name": "技术"}).status_code == 200
    assert client.get("/api/knowledge/topics?category=科技").json()["total"] == 1
    assert client.get("/api/knowledge/meta").json()["categories"] == ["技术", "科技"]


def test_hidden_only_affects_dropdown_and_restores(managed):
    client, _, _, _ = managed
    path = "/api/knowledge/manage/category-visibility"
    assert client.put(path, json={"name": "技术", "hidden": True}).status_code == 200
    assert client.get("/api/knowledge/meta").json()["categories"] == ["科技"]
    assert client.get("/api/knowledge/topics").json()["total"] == 2
    assert client.get("/api/knowledge/topics?category=技术").json()["total"] == 1
    client.put(path, json={"name": "技术", "hidden": False})
    assert client.get("/api/knowledge/meta").json()["categories"] == ["技术", "科技"]


def test_chained_merge_refuses_cycles_and_hides_canonical(managed):
    client, _, _, _ = managed
    path = "/api/knowledge/manage"
    client.post(path + "/category-merge", json={"source": "技术", "target": "科技"})
    client.post(path + "/category-merge", json={"source": "科技", "target": "科学"})
    assert client.get("/api/knowledge/meta").json()["categories"] == ["科学"]
    assert client.get("/api/knowledge/topics?category=科学").json()["total"] == 2
    assert (
        client.post(path + "/category-merge", json={"source": "科学", "target": "技术"}).status_code
        == 422
    )
    assert (
        client.post(path + "/category-merge", json={"source": "科学", "target": "科学"}).status_code
        == 422
    )
    client.put(path + "/category-visibility", json={"name": "技术", "hidden": True})
    assert client.get("/api/knowledge/meta").json()["categories"] == []
    assert client.get("/api/knowledge/topics").json()["total"] == 2
    assert (
        client.post(path + "/category-merge", json={"source": " ", "target": "a"}).status_code
        == 422
    )


def test_legacy_column_migration_and_user_config_survive(managed):
    client, db, engine, _ = managed
    client.patch("/api/knowledge/manage/sources/1", json={"enabled": False})
    db.commit()
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_knowledge_topics_feed_source_key"))
        connection.execute(text("ALTER TABLE knowledge_topics DROP COLUMN feed_source_key"))
    migrate(engine)
    migrate(engine)
    db.expire_all()
    assert db.get(ManagedKnowledgeSource, 1).enabled is False
    assert all(db.scalars(select(KnowledgeTopic.feed_source_key)))
    assert [
        row["collected_count"]
        for row in client.get("/api/knowledge/manage/sources").json()["items"][:2]
    ] == [1, 1]


def test_management_rejects_cross_origin_writes(managed):
    client, _, _, _ = managed
    assert (
        client.patch(
            "/api/knowledge/manage/sources/1",
            json={"enabled": False},
            headers={"Origin": "https://other.example"},
        ).status_code
        == 403
    )


def test_seed_respects_disabled_source_defaults():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        source = FeedSource(
            name="Disabled", url="https://example.net/feed", category="自然", enabled=False
        )
        seed_sources(db, Settings(knowledge_sources=[source]))
        db.commit()
        assert db.scalar(select(ManagedKnowledgeSource)).enabled is False
    engine.dispose()
