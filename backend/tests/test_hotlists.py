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


def test_complete_platform_catalog_and_region_filters(context):  # noqa: F811
    client, db, _ = context
    from app.core.hot_platforms import HOT_PLATFORM_CATALOG

    names = [platform["name"] for platform in HOT_PLATFORM_CATALOG]
    expected = "微博 知乎 微信 百度 哔哩哔哩 36氪 少数派 虎嗅网 IT之家 掘金 机器之心 量子位 Readhub 抖音 AcFun 吾爱破解 豆瓣社区 百度贴吧 腾讯新闻 虎扑社区 淘宝·天猫 什么值得买 今日热卖 淘宝 雪球 第一财经 华尔街见闻 新浪财经新闻 水木社区 北大未名 北邮人论坛 知乎日报 开眼视频 历史上的今天 高楼迷 宽带山 厦门小鱼 过早客 即将上映电影 豆瓣电影 微信读书 当当 七猫中文网 纵横中文网 TapTap 3DM游戏网 机核网 游研社 小黑盒 新浪体育新闻 懂球帝 人人都是产品经理 咖啡日报 即刻圈子 ProductHunt GitHub CSDN博客 开源中国 站酷 Dribbble 优设网 UI中国 AppStore 爱范儿 AppSo 汽车之家 懂车帝 易车网 太平洋汽车网 先知社区 安全客 FreeBuf 安全脉搏".split()
    normalized = [name.replace(" ", "") for name in names]
    for name in expected:
        assert any(name in value for value in normalized), name
    assert len(names) == len(set(names))
    assert len({platform["id"] for platform in HOT_PLATFORM_CATALOG}) == len(names)
    result = client.get("/api/knowledge/hotlists").json()
    assert result["platform_count"] == len(HOT_PLATFORM_CATALOG)
    assert all(p["connection_status"] == "reserved" for p in result["platforms"])
    overseas = client.get("/api/knowledge/hotlists?region=国外").json()["platforms"]
    assert all(p["region"] == "国外" for p in overseas)
    assert {"YouTube", "X（Twitter）", "Reddit", "TikTok", "Instagram"} <= {
        p["name"] for p in overseas
    }
    assert all(not p["items"] and p["source_id"] is None for p in overseas)
    domestic = client.get("/api/knowledge/hotlists?region=国内").json()["platforms"]
    assert all(p["region"] == "国内" for p in domestic)
    assert len(domestic) + len(overseas) == len(names)
    assert client.get("/api/knowledge/hotlists?region=invalid").status_code == 422


def test_platform_provider_grouping_and_uapi_parsing(context):  # noqa: F811
    from sqlalchemy import select

    from app.core.config import Settings
    from app.core.sources import DEFAULT_SOURCES
    from app.models import ManagedKnowledgeSource
    from app.services.knowledge.management import seed_sources

    client, db, _ = context
    sources = [FeedSource(**s) for s in DEFAULT_SOURCES if s["url"].startswith("https://uapis.cn/")]
    assert {s.options["platform_id"] for s in sources} == {"baidu", "xiaohongshu"}
    seed_sources(db, Settings(knowledge_sources=sources))
    for source in sources:
        payload = {
            "type": source.options["platform_id"],
            "list": [
                {
                    "index": 7,
                    "title": "公开热搜词",
                    "url": "https://example.com/" + source.options["platform_id"],
                    "hot_value": "12345",
                }
            ],
        }
        records = collect_source(source, lambda url, payload=payload: json.dumps(payload).encode())
        assert records[0]["score"] == 12345
        assert records[0]["hot_rank"] == 7
        save_topics(db, records, utcnow())
    db.commit()
    configured = db.scalar(
        select(ManagedKnowledgeSource).where(ManagedKnowledgeSource.name.contains("百度"))
    )
    configured.name = "管理员自定义百度来源名称"
    db.commit()
    platforms = {p["id"]: p for p in client.get("/api/knowledge/hotlists").json()["platforms"]}
    for key in ("baidu", "xiaohongshu"):
        assert platforms[key]["connection_status"] == "configured"
        assert len(platforms[key]["items"]) == 1
    assert platforms["youtube"]["connection_status"] == "reserved"
    assert client.get("/api/knowledge/hotlists?region=国外").json()["items"] == []
