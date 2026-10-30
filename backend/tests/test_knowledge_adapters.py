"""多 API、融合引用、分页和接口管理的行为验证。"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import KnowledgeCitation, KnowledgeTopic
from app.services.knowledge.adapters import collect_source
from app.services.knowledge.collector import save_topics
from app.services.knowledge.management import active_sources, seed_sources
from app.services.knowledge.normalization import parse_feed
from app.services.knowledge.sources import FeedSource

pytest_plugins = ["test_knowledge_management"]


def test_hackernews_bounded_and_community_score():
    source = FeedSource(
        name="HN",
        url="https://hacker-news.firebaseio.com/v0/topstories.json",
        category="科技",
        adapter="hackernews",
        item_limit=1,
    )
    calls = []

    def fetch(url):
        calls.append(url)
        if url.endswith("topstories.json"):
            return b"[1,2]"
        return json.dumps(
            {
                "id": 1,
                "type": "story",
                "title": "Demo",
                "url": "https://example.com/a",
                "score": 42,
                "time": 1700000000,
            }
        ).encode()

    rows = collect_source(source, fetch)
    assert len(calls) == 2 and rows[0]["score"] == 42
    assert "未提供文章摘要" in rows[0]["summary"]
    assert rows[0]["channel"] == "hackernews"


def test_json_nested_fields_and_limits():
    source = FeedSource(
        name="JSON",
        url="https://example.com/api",
        category="自然",
        adapter="json",
        item_limit=1,
        options={
            "items_path": "collection.items",
            "title_field": "data.0.title",
            "url_field": "data.0.id",
            "url_prefix": "https://example.com/article/",
            "summary_field": "data.0.summary",
        },
    )
    payload = {
        "collection": {
            "items": [
                {"data": [{"title": "Earth", "id": "A B", "summary": "Facts"}]},
                {"title": "Ignored"},
            ]
        }
    }
    rows = collect_source(source, lambda url: json.dumps(payload).encode())
    assert len(rows) == 1 and rows[0]["source_url"] == "https://example.com/article/A%20B"
    assert rows[0]["summary"] == "Facts"
    assert rows[0]["published_at"] is None


def test_wikipedia_event_year_not_publication_date():
    source = FeedSource(
        name="History",
        url="https://en.wikipedia.org/api/rest_v1/feed/onthisday/events",
        category="历史",
        adapter="wikipedia",
    )
    payload = {
        "events": [
            {
                "year": 1900,
                "text": "Historical event",
                "pages": [
                    {"content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Example"}}}
                ],
            }
        ]
    }
    rows = collect_source(source, lambda url: json.dumps(payload).encode())
    assert rows[0]["title"].startswith("1900") and rows[0]["published_at"] is None
    with pytest.raises(ValidationError):
        FeedSource(name="Bad", url="https://example.com/x", category="科技", adapter="hackernews")


def test_fusion_keeps_primary_source_and_citations(managed):
    _, db, _, settings = managed
    rss = b"<rss><channel><item><title>Same</title><link>https://example.com/shared</link><description>Original</description></item></channel></rss>"
    now = datetime(2026, 10, 30)
    for source in settings.knowledge_sources:
        save_topics(db, parse_feed(rss, source), now)
    db.commit()
    topic = db.scalar(
        select(KnowledgeTopic).where(KnowledgeTopic.source_url == "https://example.com/shared")
    )
    assert topic.source_name == "A"
    assert (
        db.scalar(
            select(func.count())
            .select_from(KnowledgeCitation)
            .where(KnowledgeCitation.topic_id == topic.id)
        )
        == 2
    )


def test_delete_url_edit_and_pagination(managed):
    client, db, _, settings = managed
    result = client.patch(
        "/api/knowledge/manage/sources/1", json={"url": "https://example.com/new"}
    )
    assert result.status_code == 200
    assert client.get("/api/knowledge/topics?source_id=1").json()["total"] == 1
    seed_sources(db, settings)
    db.commit()
    assert len(client.get("/api/knowledge/manage/sources").json()["items"]) == 2
    assert client.delete("/api/knowledge/manage/sources/1").status_code == 200
    seed_sources(db, settings)
    db.commit()
    assert len(client.get("/api/knowledge/manage/sources").json()["items"]) == 1
    assert len(active_sources(db, settings)) == 1
    assert client.get("/api/knowledge/topics").json()["total"] == 2
    first = client.get("/api/knowledge/topics?page=1&page_size=1").json()
    second = client.get("/api/knowledge/topics?page=2&page_size=1").json()
    assert first["total_pages"] == 2 and first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/knowledge/topics?page=3&page_size=1").json()["items"] == []
    assert client.get("/api/knowledge/topics?page=0").status_code == 422
    assert client.get("/api/knowledge/topics?page_size=201").status_code == 422
