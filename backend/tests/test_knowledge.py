"""知识采集与 Skills 分类的业务测试；网络均由受控响应替代。"""

from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_session
from app.main import app
from app.models import KnowledgeSourceState, KnowledgeTopic
from app.services.knowledge.categories import get_category_catalog
from app.services.knowledge.collector import collect_knowledge, save_topics
from app.services.knowledge.normalization import (
    canonical_url,
    classify_region,
    parse_date,
    parse_feed,
)
from app.services.knowledge.sources import FeedSource
from app.services.skills.metadata import extract_metadata

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><item>
<title>A discovery</title><link>https://example.com/a?utm_source=rss</link>
<description>&lt;p&gt;Facts &amp;amp; evidence&lt;/p&gt;</description>
<pubDate>Thu, 29 Oct 2026 12:00:00 +0000</pubDate></item></channel></rss>"""
SOURCE = FeedSource(
    name="Test", url="https://example.com/feed", category="自然", topic_kind="知识探索"
)


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def locks(connection, record):
        # 仅替代锁函数，以便在单元测试中验证来源失败隔离；真实锁另有 MySQL 测试。
        connection.create_function("GET_LOCK", 2, lambda *args: 1)
        connection.create_function("RELEASE_LOCK", 1, lambda *args: 1)

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_metadata_multi_category_and_install_boundary():
    categories, install = extract_metadata(
        "sample/voice",
        "TTS and subtitle",
        "# Demo\n## Installation\n```sh\nnpm install demo\n```\n## Usage\nPrivate usage",
    )
    assert categories == ["配音", "字幕"]
    assert "npm install demo" in install
    assert "Private usage" not in install
    assert extract_metadata("math", "", "")[0] == ["其他"]


def test_rss_cleaning_dates_and_bad_links():
    data = parse_feed(RSS, SOURCE)[0]
    assert data["source_url"] == "https://example.com/a"
    assert data["summary"] == "Facts & evidence"
    assert data["published_at"] == datetime(2026, 10, 29, 12)
    assert "为什么" in data["video_angle"]
    assert canonical_url("javascript:alert(1)") is None
    assert canonical_url("https://user:secret@example.com") is None
    assert parse_date("bad") is None
    assert parse_date("2026-10-30T12:00:00") is None
    with pytest.raises(ValueError):
        parse_feed(b"<!DOCTYPE html><html/>", SOURCE)


def test_atom_preserves_missing_original_date():
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title>
    <link href="https://example.com/atom"/><updated>2026-10-30T12:00:00Z</updated>
    <summary>Summary</summary></entry></feed>"""
    assert parse_feed(atom, SOURCE)[0]["published_at"] is None


def test_source_failure_isolation_and_idempotence(engine):
    settings = Settings(
        knowledge_sources=[
            SOURCE,
            FeedSource(name="Broken", url="https://example.com/bad", category="商业"),
        ]
    )
    calls = []

    def respond(request):
        calls.append(request.url.path)
        return httpx.Response(200, content=RSS if request.url.path == "/feed" else b"<html/>")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = collect_knowledge(settings, engine, client)
        assert result == {"sources": 1, "failed": 1, "added": 1}
        again = collect_knowledge(settings, engine, client)
        assert again["added"] == 0
    assert calls.count("/feed") == 1
    with Session(engine) as db:
        assert len(list(db.scalars(select(KnowledgeTopic)))) == 1
        assert set(db.scalars(select(KnowledgeSourceState.status))) == {"success", "failed"}


def test_knowledge_api_and_upsert(engine):
    with Session(engine) as db:
        records = parse_feed(RSS, SOURCE)
        at = datetime(2026, 10, 30)
        assert save_topics(db, records, at) == 1
        assert save_topics(db, records, datetime(2026, 10, 31)) == 0
        db.commit()
        app.dependency_overrides[get_session] = lambda: db
        app.dependency_overrides[get_category_catalog] = lambda: {
            "categories": ["教育", "自然"],
            "status": "success",
            "source_name": "Test catalog",
            "source_url": "https://example.com",
            "updated_at": at,
            "error": None,
        }
        try:
            client = TestClient(app)
            meta = client.get("/api/knowledge/meta").json()
            assert meta["categories"] == ["自然"]  # 筛选仅显示已有内容的分类
            assert meta["categories"].count("自然") == 1
            assert meta["category_catalog"]["remote_count"] == 2
            assert meta["category_catalog"]["updated_at"].startswith("2026-10-30")
            app.dependency_overrides[get_category_catalog] = lambda: {
                "categories": [],
                "status": "fallback",
                "source_name": "Test catalog",
                "source_url": "https://example.com",
                "updated_at": None,
                "error": "offline",
            }
            fallback = client.get("/api/knowledge/meta").json()
            assert "自然" in fallback["categories"]
            assert fallback["category_catalog"]["status"] == "fallback"
            response = client.get(
                "/api/knowledge/topics?category=自然&q=discovery&day=2026-10-29"
            ).json()
            assert response["total"] == 1
            assert response["items"][0]["region"] == "国外"
            assert client.get("/api/knowledge/topics?region=国外").json()["total"] == 1
            assert client.get("/api/knowledge/topics?region=国内").json()["total"] == 0
            assert client.get("/api/knowledge/topics?region=invalid").status_code == 422
            assert response["items"][0]["collected_at"].startswith("2026-10-30")
            assert client.get("/api/knowledge/topics?q=%25").json()["total"] == 0
            assert client.get("/api/knowledge/topics?category=商业").json()["total"] == 0
            assert client.get("/api/knowledge/topics?topic_kind=wrong").status_code == 422
            topic_id = response["items"][0]["id"]
            assert "视频切入角度" in client.get(f"/api/knowledge/topics/{topic_id}/markdown").text
            assert client.get("/api/knowledge/topics/999/markdown").status_code == 404
        finally:
            app.dependency_overrides.clear()


def test_region_uses_topic_evidence_before_source_default():
    assert classify_region("中国机器人", "", SOURCE)[0] == "国内"
    domestic = FeedSource(
        name="国内源", url="https://example.com/rss", category="科技", region="国内"
    )
    assert classify_region("NASA observation", "", domestic)[0] == "国外"
    assert classify_region("日常生活小知识", "", domestic) == (
        "国内",
        "无明确地区关键词，使用来源默认地区",
    )


def test_migration_backfills_known_source_and_is_repeatable(engine):
    from app.runtime.migrations import migrate

    with Session(engine) as db:
        record = parse_feed(RSS, SOURCE)[0]
        record.update(region=None, region_basis=None, source_name="少数派 数字生活")
        save_topics(db, [record], datetime(2026, 10, 30))
        db.commit()
    migrate(engine)
    migrate(engine)
    with Session(engine) as db:
        assert db.scalar(select(KnowledgeTopic)).region == "国内"
