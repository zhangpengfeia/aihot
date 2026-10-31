"""热搜数据规范化、真实返回顺序、标签匹配与失败响应。"""

import json

import pytest
from test_workspace import context  # noqa: F401

from app.core.sources import FeedSource
from app.core.taxonomy import TAG_TERMS, topic_tags
from app.models import HotListSnapshot
from app.services.knowledge.adapters import collect_source
from app.services.knowledge.collector import save_topics
from app.utils.time import utcnow
from app.utils.urls import source_key

SOURCE = FeedSource(
    name="热搜 · 测试",
    url="https://example.com/hot",
    adapter="hotlist",
    category="科技",
    region="国内",
)


def test_hotlist_order_and_empty_errors(context):  # noqa: F811
    client, db, _ = context
    payload = {
        "code": 200,
        "data": [
            {"title": "智能体与古代工程", "url": "https://example.com/agent", "hot": "1234"},
            {"title": "机器人与深海生物", "url": "https://example.com/robot", "hot": 50},
        ],
    }
    rows = collect_source(SOURCE, lambda url: json.dumps(payload).encode())
    assert len(rows) == 2 and rows[0]["score"] == 1234
    save_topics(db, rows, utcnow())
    db.commit()
    snapshot = db.get(HotListSnapshot, source_key(SOURCE.url))
    assert [i["title"] for i in snapshot.entries] == ["智能体与古代工程", "机器人与深海生物"]
    assert all(i["id"] for i in snapshot.entries)
    from app.core.config import Settings
    from app.services.knowledge.management import seed_sources

    seed_sources(db, Settings(knowledge_sources=[SOURCE]))
    db.commit()
    result = client.get("/api/knowledge/hotlists").json()["items"]
    assert len(result) == 1
    assert result[0]["items"][0]["title"] == "智能体与古代工程"
    assert result[0]["items"][0]["score_label"] == "1234"
    assert result[0]["observed_at"]

    assert client.get("/api/knowledge/topics?tag=深海生物").json()["total"] == 1
    assert client.get("/api/knowledge/topics?hot_only=true").json()["total"] == 2
    for invalid in (
        {"code": 500, "data": []},
        {"code": 200, "data": []},
        {"data": [{"title": "missing url"}]},
    ):
        with pytest.raises(ValueError):
            collect_source(SOURCE, lambda url, payload=invalid: json.dumps(payload).encode())
    assert (
        client.get(
            "/api/knowledge/topics", params=[("labels", "自然"), ("labels", "深海生物")]
        ).json()["total"]
        == 2
    )
    assert (
        client.get(
            "/api/knowledge/topics", params=[("labels", "科技"), ("labels", "深海生物")]
        ).json()["total"]
        == 2
    )
    assert (
        client.get("/api/knowledge/topics", params=[("labels", "科技"), ("labels", "科技")]).json()[
            "total"
        ]
        == 2
    )
    assert client.get("/api/knowledge/topics", params=[("labels", "不存在")]).json()["total"] == 0
    assert (
        client.get(
            "/api/knowledge/topics",
            params=[("labels", "自然"), ("labels", "深海生物"), ("q", "机器人")],
        ).json()["total"]
        == 1
    )
    assert client.get("/api/knowledge/topics", params={"labels": "x" * 51}).status_code == 422
    assert len(TAG_TERMS) > 250
    assert "声音景观" in topic_tags("声音景观研究", "", "文化")


def test_xhs_mapping_without_fabricated_links():
    source = SOURCE.model_copy(
        update={
            "options": {
                "items_path": "data.items",
                "title_field": "word",
                "url_field": "word",
                "url_prefix": "https://www.xiaohongshu.com/search_result?keyword=",
            }
        }
    )
    rows = collect_source(
        source, lambda url: json.dumps({"data": {"items": [{"word": "古建筑"}]}}).encode()
    )
    assert rows[0]["source_url"].endswith("%E5%8F%A4%E5%BB%BA%E7%AD%91")


def test_60s_preserves_original_metric_and_rank():
    payload = {
        "code": 200,
        "data": [
            {
                "rank": 7,
                "title": "建筑",
                "link": "https://www.xiaohongshu.com/search_result?keyword=architecture",
                "score": "947.5w",
            }
        ],
    }
    rows = collect_source(SOURCE, lambda url: json.dumps(payload).encode())
    assert rows[0]["hot_rank"] == 7
    assert rows[0]["score_label"] == "947.5w"
    assert rows[0]["score"] is None
