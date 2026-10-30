"""默认知识来源及配置结构；首次初始化后由数据库来源管理维护。"""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class FeedSource(BaseModel):
    enabled: bool = True
    adapter: Literal["rss", "hackernews", "wikipedia", "json"] = "rss"
    item_limit: int = Field(default=100, ge=1, le=200)
    options: dict[str, str] = Field(default_factory=dict)
    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    category: str = Field(min_length=1, max_length=50)
    region: str = Field(default="国外", pattern="^(国内|国外)$")
    # 此标签描述选题用途，不声称掌握全网阅读量。
    topic_kind: str = Field(default="热点候选", pattern="^(热点候选|知识探索)$")

    @model_validator(mode="after")
    def validate_adapter(self):
        from urllib.parse import urlsplit

        parsed = urlsplit(str(self.url))
        if self.adapter == "hackernews" and (
            parsed.hostname != "hacker-news.firebaseio.com"
            or parsed.path
            not in {"/v0/topstories.json", "/v0/beststories.json", "/v0/newstories.json"}
        ):
            raise ValueError("Hacker News 请填写官方 topstories/beststories/newstories API 地址")
        if self.adapter == "wikipedia" and (
            parsed.hostname not in {"en.wikipedia.org", "zh.wikipedia.org"}
            or parsed.path.rstrip("/") != "/api/rest_v1/feed/onthisday/events"
        ):
            raise ValueError("百科接口请填写官方 /api/rest_v1/feed/onthisday/events 地址")
        allowed = {
            "items_path",
            "title_field",
            "url_field",
            "summary_field",
            "date_field",
            "score_field",
            "url_prefix",
        }
        if set(self.options) - allowed or any(len(value) > 500 for value in self.options.values()):
            raise ValueError("字段映射仅支持已列出的字段，单个映射长度不能超过 500")
        return self


DEFAULT_SOURCES = [
    {
        "name": "MIT 人工智能",
        "url": "https://news.mit.edu/rss/topic/artificial-intelligence2",
        "category": "科技",
    },
    {
        "name": "BBC 商业",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "category": "商业",
    },
    {
        "name": "Smithsonian 历史",
        "url": "https://www.smithsonianmag.com/rss/history/",
        "category": "历史",
        "topic_kind": "知识探索",
    },
    {
        "name": "NASA 科学与太空",
        "url": "https://www.nasa.gov/feed/",
        "category": "自然",
        "topic_kind": "知识探索",
    },
    {
        "name": "少数派 数字生活",
        "region": "国内",
        "url": "https://sspai.com/feed",
        "category": "生活",
    },
]


# 同一模型同时描述 RSS 和公开 API；各来源独立启停、测试和限量采集。
DEFAULT_SOURCES += [
    {
        "name": "Hacker News 热门 API",
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "category": "科技",
        "adapter": "hackernews",
        "item_limit": 30,
    },
    {
        "name": "Wikipedia 历史上的今天 API",
        "url": "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events",
        "category": "历史",
        "adapter": "wikipedia",
        "enabled": False,
        "topic_kind": "知识探索",
        "item_limit": 100,
    },
    {
        "name": "arXiv 人工智能 API",
        "url": "https://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=100&sortBy=submittedDate&sortOrder=descending",
        "category": "人工智能",
        "topic_kind": "知识探索",
        "item_limit": 100,
    },
]
for name, path, category in [
    ("财经", "finance", "商业"),
    ("文化", "culture", "文化"),
    ("教育", "edu", "教育"),
    ("健康", "jk", "健康"),
    ("生活", "life", "生活"),
    ("社会", "society", "社会"),
    ("体育", "sports", "体育"),
]:
    DEFAULT_SOURCES.append(
        {
            "name": f"中新网{name}",
            "url": f"https://www.chinanews.com.cn/rss/{path}.xml",
            "category": category,
            "region": "国内",
            "item_limit": 100,
        }
    )
for name, path, category in [
    ("健康医学", "health_medicine", "健康"),
    ("心理研究", "mind_brain/psychology", "心理"),
    ("环境科学", "earth_climate/environmental_science", "环境"),
]:
    DEFAULT_SOURCES.append(
        {
            "name": f"ScienceDaily {name}",
            "url": f"https://www.sciencedaily.com/rss/{path}.xml",
            "category": category,
            "topic_kind": "知识探索",
            "item_limit": 100,
        }
    )
DEFAULT_SOURCES += [
    {
        "name": "Smithsonian 文化艺术",
        "url": "https://www.smithsonianmag.com/rss/arts-culture/",
        "category": "文化",
        "topic_kind": "知识探索",
    },
    {
        "name": "Smithsonian 旅行地理",
        "url": "https://www.smithsonianmag.com/rss/travel/",
        "category": "旅行",
        "topic_kind": "知识探索",
    },
]

DEFAULT_SOURCES.append(
    {
        "name": "NASA 地球科学 API",
        "url": "https://images-api.nasa.gov/search?q=earth&media_type=image&page_size=100",
        "category": "自然",
        "adapter": "json",
        "topic_kind": "知识探索",
        "item_limit": 100,
        "options": {
            "items_path": "collection.items",
            "title_field": "data.0.title",
            "url_field": "data.0.nasa_id",
            "url_prefix": "https://images.nasa.gov/details/",
            "summary_field": "data.0.description",
            "date_field": "data.0.date_created",
        },
    }
)

DEFAULT_SOURCES.append(
    {
        "name": "Hacker News 搜索 API",
        "url": "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=100",
        "category": "科技",
        "adapter": "json",
        "item_limit": 100,
        "options": {
            "items_path": "hits",
            "title_field": "title",
            "url_field": "url",
            "summary_field": "story_text",
            "date_field": "created_at",
            "score_field": "points",
        },
    }
)
