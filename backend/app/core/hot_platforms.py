"""热搜平台目录。目录预留与实际采集接口分离，不为预留平台虚构 API。"""

# (稳定标识, 展示名, 分类, 地区, 已有来源别名)
PLATFORM_ROWS = [
    ("xiaohongshu", "小红书", "生活", "国内", []),
    ("weibo", "微博", "综合", "国内", []),
    ("zhihu", "知乎", "综合", "国内", []),
    ("wechat", "微信", "综合", "国内", []),
    ("baidu", "百度", "综合", "国内", []),
    ("bilibili", "哔哩哔哩", "综合", "国内", []),
    ("36kr", "36氪", "科技", "国内", []),
    ("sspai", "少数派", "科技", "国内", []),
    ("huxiu", "虎嗅网", "科技", "国内", ["虎嗅"]),
    ("ithome", "IT之家", "科技", "国内", []),
    ("juejin", "掘金", "科技", "国内", []),
    ("jiqizhixin", "机器之心", "科技", "国内", []),
    ("qbitai", "量子位", "科技", "国内", []),
    ("readhub", "Readhub", "科技", "国内", []),
    ("douyin", "抖音", "综合", "国内", []),
    ("acfun", "AcFun", "综合", "国内", []),
    ("52pojie", "吾爱破解", "科技", "国内", []),
    ("douban-group", "豆瓣社区", "社区", "国内", ["豆瓣小组"]),
    ("tieba", "百度贴吧", "社区", "国内", []),
    ("qq-news", "腾讯新闻", "资讯", "国内", []),
    ("hupu", "虎扑社区", "体育", "国内", ["虎扑"]),
    ("taobao-tmall", "淘宝 · 天猫", "购物", "国内", []),
    ("smzdm", "什么值得买", "购物", "国内", []),
    ("today-sales", "今日热卖", "购物", "国内", []),
    ("taobao", "淘宝", "购物", "国内", []),
    ("xueqiu", "雪球", "财经", "国内", []),
    ("yicai", "第一财经", "财经", "国内", []),
    ("wallstreetcn", "华尔街见闻", "财经", "国内", []),
    ("sina-finance", "新浪财经新闻", "财经", "国内", []),
    ("newsmth", "水木社区", "社区", "国内", []),
    ("bdwm", "北大未名", "社区", "国内", []),
    ("byr", "北邮人论坛", "社区", "国内", []),
    ("zhihu-daily", "知乎日报", "文化", "国内", []),
    ("eyepetizer", "开眼视频", "文化", "国内", []),
    ("history", "历史上的今天", "文化", "国内", []),
    ("gaoloumi", "高楼迷", "社区", "国内", []),
    ("kds", "宽带山", "社区", "国内", []),
    ("xmfish", "厦门小鱼", "社区", "国内", []),
    ("guanggoo", "过早客（光谷社区）", "社区", "国内", []),
    ("coming-movies", "即将上映电影", "影视", "国内", []),
    ("douban-movie", "豆瓣电影", "影视", "国内", []),
    ("weread", "微信读书", "阅读", "国内", []),
    ("dangdang", "当当", "阅读", "国内", []),
    ("qimao", "七猫中文网", "阅读", "国内", []),
    ("zongheng", "纵横中文网", "阅读", "国内", []),
    ("taptap", "TapTap", "游戏", "国内", []),
    ("3dm", "3DM游戏网", "游戏", "国内", []),
    ("gcores", "机核网", "游戏", "国内", []),
    ("yystv", "游研社", "游戏", "国内", []),
    ("heybox", "小黑盒", "游戏", "国内", []),
    ("sina-sports", "新浪体育新闻", "体育", "国内", []),
    ("dongqiudi", "懂球帝", "体育", "国内", []),
    ("woshipm", "人人都是产品经理", "设计", "国内", []),
    ("coffee", "咖啡日报", "生活", "国内", []),
    ("jike", "即刻圈子", "社区", "国内", []),
    ("producthunt", "Product Hunt", "科技", "国外", []),
    ("github", "GitHub", "科技", "国外", []),
    ("csdn", "CSDN博客", "科技", "国内", ["CSDN"]),
    ("oschina", "开源中国", "科技", "国内", []),
    ("zcool", "站酷", "设计", "国内", []),
    ("dribbble", "Dribbble", "设计", "国外", []),
    ("uisdc", "优设网", "设计", "国内", []),
    ("ui-cn", "UI 中国", "设计", "国内", []),
    ("app-store", "App Store", "科技", "国外", []),
    ("ifanr", "爱范儿", "科技", "国内", []),
    ("appso", "AppSo", "科技", "国内", []),
    ("autohome", "汽车之家", "汽车", "国内", []),
    ("dongchedi", "懂车帝", "汽车", "国内", []),
    ("yiche", "易车网", "汽车", "国内", []),
    ("pcauto", "太平洋汽车网", "汽车", "国内", []),
    ("xz", "先知社区", "安全", "国内", []),
    ("anquanke", "安全客", "安全", "国内", []),
    ("freebuf", "FreeBuf", "安全", "国内", []),
    ("secpulse", "安全脉搏", "安全", "国内", []),
    # 图外补充：本轮按用户要求仅预留国外平台，不增加接口或自动采集任务。
    ("youtube", "YouTube", "视频", "国外", []),
    ("x", "X（Twitter）", "综合", "国外", ["X", "Twitter"]),
    ("reddit", "Reddit", "社区", "国外", []),
    ("tiktok", "TikTok", "视频", "国外", []),
    ("instagram", "Instagram", "社交", "国外", []),
    ("threads", "Threads", "社交", "国外", []),
    ("facebook", "Facebook", "社交", "国外", []),
    ("twitch", "Twitch", "直播", "国外", []),
    ("bluesky", "Bluesky", "社交", "国外", []),
    ("mastodon", "Mastodon", "社交", "国外", []),
    ("hackernews", "Hacker News", "科技", "国外", []),
    ("stackoverflow", "Stack Overflow", "科技", "国外", []),
    ("huggingface", "Hugging Face", "人工智能", "国外", []),
    ("medium", "Medium", "阅读", "国外", []),
    ("substack", "Substack", "阅读", "国外", []),
    ("devto", "DEV Community", "科技", "国外", []),
    ("lobsters", "Lobsters", "科技", "国外", []),
    ("techcrunch", "TechCrunch", "科技", "国外", []),
    ("theverge", "The Verge", "科技", "国外", []),
    ("wired", "WIRED", "科技", "国外", []),
    ("arstechnica", "Ars Technica", "科技", "国外", []),
    ("engadget", "Engadget", "科技", "国外", []),
    ("reuters", "Reuters", "资讯", "国外", []),
    ("bbc", "BBC", "资讯", "国外", []),
    ("cnn", "CNN", "资讯", "国外", []),
    ("nytimes", "The New York Times", "资讯", "国外", []),
    ("theguardian", "The Guardian", "资讯", "国外", []),
    ("behance", "Behance", "设计", "国外", []),
    ("pinterest", "Pinterest", "设计", "国外", []),
    ("steam", "Steam", "游戏", "国外", []),
    ("indiehackers", "Indie Hackers", "商业", "国外", []),
    ("kickstarter", "Kickstarter", "商业", "国外", []),
    ("imdb", "IMDb", "影视", "国外", []),
    ("spotify", "Spotify", "音乐", "国外", []),
    ("apple-music", "Apple Music", "音乐", "国外", []),
    ("google-trends", "Google Trends", "综合", "国外", []),
]
HOT_PLATFORM_CATALOG = [
    dict(id=key, name=name, category=category, region=region, aliases=aliases)
    for key, name, category, region, aliases in PLATFORM_ROWS
]
PLATFORMS_BY_ID = {platform["id"]: platform for platform in HOT_PLATFORM_CATALOG}
NAME_TO_ID = {
    name.casefold(): platform["id"]
    for platform in HOT_PLATFORM_CATALOG
    for name in [platform["name"], *platform["aliases"]]
}


def platform_from_name(name):
    import re

    clean = re.split(r"[（(]", name.removeprefix("热搜 · ").strip())[0].strip()
    return NAME_TO_ID.get(clean.casefold())


def platform_for_source(source):
    from app.core.sources import DEFAULT_SOURCES
    from app.utils.urls import source_key

    explicit = (source.options or {}).get("platform_id")
    if explicit in PLATFORMS_BY_ID:
        return explicit
    by_name = platform_from_name(source.name)
    if by_name:
        return by_name
    # 管理员改名后依旧能依据原始来源键关联平台，不覆盖用户配置。
    origin = source.origin_key or source.source_key
    return next(
        (
            platform_from_name(item["name"])
            for item in DEFAULT_SOURCES
            if source_key(item["url"]) == origin
        ),
        None,
    )
