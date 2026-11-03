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
    from app.core.hot_platforms import PLATFORMS_BY_ID
    from app.core.sources import DEFAULT_SOURCES
    from app.models import ManagedKnowledgeSource
    from app.services.knowledge.management import seed_sources

    client, db, _ = context
    sources = [FeedSource(**s) for s in DEFAULT_SOURCES if s["url"].startswith("https://uapis.cn/")]
    assert {"baidu", "xiaohongshu"} <= {s.options["platform_id"] for s in sources}
    # 新增的 UAPI 来源必须能关联到目录平台，且不虚构目录之外的平台。
    assert {s.options["platform_id"] for s in sources} <= set(PLATFORMS_BY_ID)
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
        assert records[0]["score"] == (12345 if source.options.get("score_field") else None)
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


def test_wallstreetcn_success_code_and_search_prefix():
    source = SOURCE.model_copy(
        update={
            "options": {
                "items_path": "data.day_items",
                "title_field": "title",
                "url_field": "uri",
                "score_field": "pageviews",
                "success_code": "20000",
                "platform_id": "wallstreetcn",
            }
        }
    )
    payload = {
        "code": 20000,
        "data": {
            "day_items": [
                {
                    "title": "芯片股拖累美股指",
                    "uri": "https://wallstreetcn.com/articles/3784983",
                    "pageviews": 199332,
                }
            ]
        },
    }
    rows = collect_source(source, lambda url: json.dumps(payload).encode())
    assert rows[0]["score"] == 199332
    assert rows[0]["source_url"] == "https://wallstreetcn.com/articles/3784983"
    # 未配置 success_code 时，非 200 的状态码仍然视为失败。
    with pytest.raises(ValueError):
        collect_source(
            SOURCE.model_copy(update={"options": {"items_path": "data"}}),
            lambda url: json.dumps({"code": 20000, "data": payload["data"]["day_items"]}).encode(),
        )


def test_official_api_hotlist_sources():
    """新浪财经 7x24、开眼每日精选、猫眼即将上映榜的字段映射与平台关联。"""
    from types import SimpleNamespace

    from app.core.hot_platforms import platform_for_source
    from app.core.sources import DEFAULT_SOURCES

    definitions = [
        s
        for s in DEFAULT_SOURCES
        if any(
            host in s["url"] for host in ("zhibo.sina.com.cn", "kaiyanapp.com", "maoyan.com/ajax")
        )
    ]
    assert {s["options"]["platform_id"] for s in definitions} == {
        "sina-finance",
        "eyepetizer",
        "coming-movies",
    }
    payloads = {
        "sina-finance": {
            "result": {
                "status": {"code": 0},
                "data": {
                    "feed": {
                        "list": [
                            {
                                "rich_text": "高盛上调欧洲天然气价格预测",
                                "docurl": "https://finance.sina.cn/7x24/detail-inixmnpy9976924.d.html",
                            }
                        ]
                    }
                },
            }
        },
        "eyepetizer": {
            "issueList": [
                {
                    "itemList": [
                        {
                            "data": {
                                "title": "获奖手绘动画精选",
                                "webUrl": {
                                    "raw": "http://www.eyepetizer.net/detail.html?vid=225919"
                                },
                            }
                        }
                    ]
                }
            ]
        },
        "coming-movies": {
            "coming": [{"nm": "白衣逆行者", "id": 1500853, "wish": 20715}],
        },
    }
    expectations = {
        "sina-finance": (
            "高盛上调欧洲天然气价格预测",
            "https://finance.sina.cn/7x24/detail-inixmnpy9976924.d.html",
            None,
        ),
        "eyepetizer": (
            "获奖手绘动画精选",
            "http://www.eyepetizer.net/detail.html?vid=225919",
            None,
        ),
        "coming-movies": ("白衣逆行者", "https://www.maoyan.com/films/1500853", 20715),
    }
    for definition in definitions:
        source = FeedSource(**definition)
        rows = collect_source(
            source,
            lambda url, definition=definition: json.dumps(
                payloads[definition["options"]["platform_id"]]
            ).encode(),
        )
        title, url, score = expectations[definition["options"]["platform_id"]]
        assert rows[0]["title"] == title
        assert rows[0]["source_url"] == url
        assert rows[0]["score"] == score
        assert (
            platform_for_source(
                SimpleNamespace(
                    name=source.name,
                    options=source.options,
                    origin_key=None,
                    source_key=None,
                    url=str(source.url),
                )
            )
            == definition["options"]["platform_id"]
        )


def test_hotlists_success_first_and_failed_last(context):  # noqa: F811
    from app.core.config import Settings
    from app.core.hot_platforms import HOT_PLATFORM_CATALOG
    from app.models import KnowledgeSourceState
    from app.services.knowledge.management import seed_sources

    client, db, _ = context
    definitions = [
        FeedSource(
            name="热搜 · 知乎日报（测试）",
            url="https://example.com/hot/zhihu-daily",
            adapter="hotlist",
            category="文化",
            region="国内",
        ),
        FeedSource(
            name="热搜 · 吾爱破解（测试）",
            url="https://example.com/hot/52pojie",
            adapter="hotlist",
            category="网络安全",
            region="国内",
        ),
        FeedSource(
            name="热搜 · 腾讯新闻（测试）",
            url="https://example.com/hot/qq-news",
            adapter="hotlist",
            category="社会",
            region="国内",
        ),
        FeedSource(
            name="热搜 · 虎扑社区（测试）",
            url="https://example.com/hot/hupu",
            adapter="hotlist",
            category="体育",
            region="国内",
        ),
    ]
    now = utcnow()
    # (来源, 采集状态, 是否有历史榜单快照)：依次对应 采集完成 / 采集失败（有历史记录）/
    # 采集失败 / 配置未采集。
    plan = list(
        zip(
            definitions,
            ["success", "failed", "failed", "pending"],
            [True, True, False, False],
            strict=True,
        )
    )
    for source, status, has_snapshot in plan:
        records = collect_source(
            source,
            lambda url, name=source.name: json.dumps(
                {
                    "code": 200,
                    "data": [
                        {
                            "title": f"{name}公开热搜词",
                            "url": "https://example.com/entry",
                        }
                    ],
                }
            ).encode(),
        )
        if status != "pending":
            if has_snapshot:
                save_topics(db, records, now)
            db.add(
                KnowledgeSourceState(
                    source_key=source_key(source.url),
                    name=source.name,
                    url=str(source.url),
                    category=source.category,
                    status=status,
                    last_attempt=now,
                    last_success=now if status == "success" else None,
                    item_count=1 if has_snapshot else 0,
                    error="HTTPStatusError" if status == "failed" else None,
                )
            )
    seed_sources(db, Settings(knowledge_sources=definitions))
    db.commit()
    platforms = client.get("/api/knowledge/hotlists").json()["platforms"]
    ids = [p["id"] for p in platforms]
    assert len(ids) == len(HOT_PLATFORM_CATALOG)
    # 采集完成 > 采集失败（有历史采集记录）> 采集失败 > 配置未采集 > 未配置。
    assert ids[:4] == ["zhihu-daily", "52pojie", "qq-news", "hupu"]
    assert all(p["connection_status"] == "reserved" for p in platforms[4:])
    by_id = {p["id"]: p for p in platforms}
    assert by_id["52pojie"]["error"] == "HTTPStatusError"
    assert len(by_id["52pojie"]["items"]) == 1
    assert by_id["qq-news"]["items"] == []
    assert by_id["zhihu-daily"]["items"][0]["title"] == "热搜 · 知乎日报（测试）公开热搜词"
