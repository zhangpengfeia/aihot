"""默认知识来源及配置结构；首次初始化后由数据库来源管理维护。"""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class FeedSource(BaseModel):
    enabled: bool = True
    adapter: Literal["rss", "hackernews", "wikipedia", "json", "hotlist"] = "rss"
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
            "platform_id",
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

# 社区聚合 API，非平台官方服务。每个端点独立配置，失败沿用已有状态记录。
HOT_PLATFORMS = [
    ("百度", "baidu", "社会"),
    ("微博", "weibo", "社会"),
    ("知乎", "zhihu", "社会"),
    ("知乎日报", "zhihu-daily", "文化"),
    ("哔哩哔哩", "bilibili", "文化"),
    ("抖音", "douyin", "社会"),
    ("快手", "kuaishou", "社会"),
    ("今日头条", "toutiao", "社会"),
    ("百度贴吧", "tieba", "社会"),
    ("腾讯新闻", "qq-news", "社会"),
    ("澎湃新闻", "thepaper", "社会"),
    ("网易新闻", "netease-news", "社会"),
    ("36氪", "36kr", "商业"),
    ("虎嗅", "huxiu", "商业"),
    ("IT之家", "ithome", "科技"),
    ("少数派", "sspai", "数字生活"),
    ("掘金", "juejin", "编程语言"),
    ("CSDN", "csdn", "编程语言"),
    ("51CTO", "51cto", "科技"),
    ("V2EX", "v2ex", "科技"),
    ("吾爱破解", "52pojie", "网络安全"),
    ("爱范儿", "ifanr", "科技"),
    ("果壳", "guokr", "自然"),
    ("豆瓣电影", "douban-movie", "电影"),
    ("豆瓣小组", "douban-group", "生活"),
    ("微信读书", "weread", "阅读"),
    ("虎扑", "hupu", "体育"),
    ("NGA", "ngabbs", "电竞"),
    ("AcFun", "acfun", "动画"),
    ("HelloGitHub", "hellogithub", "开源软件"),
]
# 60s 的公开接口由项目维护者提供；公共实例有限流，生产可改为自托管公网实例。
for name, endpoint, category in [
    ("百度", "baidu/hot", "社会"),
    ("微博", "weibo", "社会"),
    ("小红书", "rednote", "生活"),
    ("知乎", "zhihu", "社会"),
    ("哔哩哔哩", "bili", "文化"),
    ("抖音", "douyin", "社会"),
    ("今日头条", "toutiao", "社会"),
    ("百度贴吧", "baidu/tieba", "社会"),
    ("IT之家", "it-news/rank", "科技"),
    ("懂车帝", "dongchedi", "汽车"),
]:
    DEFAULT_SOURCES.append(
        {
            "name": f"热搜 · {name}（60s 聚合）",
            "url": f"https://60s.viki.moe/v2/{endpoint}",
            "category": category,
            "region": "国内",
            "adapter": "hotlist",
            "item_limit": 50,
        }
    )

for name, endpoint, category in HOT_PLATFORMS:
    DEFAULT_SOURCES.append(
        {
            "name": f"热搜 · {name}（DailyHotApi 备用模板）",
            "url": f"https://dailyhot-api.vercel.app/{endpoint}",
            "category": category,
            "region": "国内",
            "adapter": "hotlist",
            "item_limit": 50,
            "enabled": False,
        }
    )

DEFAULT_SOURCES.append(
    {
        "name": "热搜 · 小红书（待测试启用）",
        "url": "https://edith.xiaohongshu.com/api/sns/v1/search/hot_list",
        "category": "生活",
        "region": "国内",
        "adapter": "hotlist",
        "enabled": False,
        "item_limit": 50,
        "options": {
            "items_path": "data.items",
            "title_field": "word",
            "url_field": "word",
            "url_prefix": "https://www.xiaohongshu.com/search_result?keyword=",
        },
    }
)

# 已经由应用实际传输层验证的百度/小红书备用公开聚合接口。
for platform_id, name, provider_type, category in [
    ("baidu", "百度", "baidu", "社会"),
    ("xiaohongshu", "小红书", "xiaohongshu", "生活"),
]:
    DEFAULT_SOURCES.append(
        {
            "name": f"热搜 · {name}（UAPI 聚合）",
            "url": f"https://uapis.cn/api/v1/misc/hotboard?type={provider_type}",
            "category": category,
            "region": "国内",
            "adapter": "hotlist",
            "item_limit": 50,
            "options": {
                "items_path": "list",
                "score_field": "hot_value",
                "platform_id": platform_id,
            },
        }
    )
