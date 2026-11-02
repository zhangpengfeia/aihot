"""长青知识订阅目录：原理、起源、演变和日常科普；统一使用已有 RSS 适配器。"""

# 不抓全文，只保存订阅源提供的标题、摘要和原文链接。
FEEDS = [
    ("科学网 · 科普集锦", "https://www.sciencenet.cn/xml/blog.aspx?di=7", "科普", "国内"),
    ("科学网 · 信息科学", "https://www.sciencenet.cn/xml/field.aspx?di=9", "计算机原理", "国内"),
    ("科学网 · 基础科学", "https://www.sciencenet.cn/xml/field.aspx?di=7", "科普", "国内"),
    ("科学网 · 生命科学", "https://www.sciencenet.cn/xml/field.aspx?di=3", "生命演化", "国内"),
    ("科学网 · 工程技术", "https://www.sciencenet.cn/xml/field.aspx?di=8", "工程原理", "国内"),
    ("科学网 · 人文社科", "https://www.sciencenet.cn/xml/blog.aspx?di=10", "历史", "国内"),
    ("科学网 · 生活常识", "https://www.sciencenet.cn/xml/blog.aspx?di=4", "生活", "国内"),
    ("科学松鼠会 · 日常科普", "https://songshuhui.net/feed", "科普", "国内"),
    ("果壳 · 科学人", "https://www.guokr.com/rss/", "科普", "国内"),
    ("中科院 · 科研进展", "https://www.cas.cn/syky/index.xml", "科普", "国内"),
    ("阮一峰 · 技术与互联网", "https://www.ruanyifeng.com/blog/atom.xml", "计算机原理", "国内"),
    ("科学空间 · 数学与 AI 原理", "https://spaces.ac.cn/feed", "人工智能", "国内"),
    ("Quanta · 数学与科学原理", "https://www.quantamagazine.org/feed/", "科普", "国外"),
    ("Science News · 科学解释", "https://www.sciencenews.org/feed", "科普", "国外"),
    ("Science News Explores · 通俗科普", "https://www.snexplores.org/feed", "科普", "国外"),
    ("ScienceAlert · 冷知识与发现", "https://www.sciencealert.com/feed", "冷知识", "国外"),
    ("Smithsonian · 科学与起源", "https://www.smithsonianmag.com/rss/science/", "科普", "国外"),
    ("Smithsonian · 发明与创新", "https://www.smithsonianmag.com/rss/innovation/", "发明起源", "国外"),
    ("JSTOR Daily · 历史与文化溯源", "https://daily.jstor.org/feed/", "历史", "国外"),
    ("World History Encyclopedia · 世界历史", "https://www.worldhistory.org/feed.rss", "历史", "国外"),
    ("HistoryExtra · 历史故事", "https://www.historyextra.com/feed/", "历史", "国外"),
    ("Archaeology · 考古发现", "https://archaeology.org/feed/", "考古", "国外"),
    ("Public Domain Review · 冷门历史", "https://publicdomainreview.org/rss.xml", "历史", "国外"),
    ("Computer History Museum · 计算机发展史", "https://computerhistory.org/blog/feed/", "计算机历史", "国外"),
    ("IEEE Spectrum · 技术演变", "https://spectrum.ieee.org/feeds/feed.rss", "工程原理", "国外"),
    ("Hackaday · 电子工程原理", "https://hackaday.com/blog/feed/", "工程原理", "国外"),
    ("How-To Geek · 数字生活常识", "https://www.howtogeek.com/feed/", "生活常识", "国外"),
    ("Explain That Stuff · 工作原理", "https://www.explainthatstuff.com/feed.xml", "工程原理", "国外"),
    ("BPS Research Digest · 心理机制", "https://www.bps.org.uk/research-digest/rss", "心理", "国外"),
    ("Nautilus · 大脑与科学", "https://nautil.us/feed/", "科普", "国外"),
    ("EarthSky · 天文与地球", "https://earthsky.org/feed/", "天文地理", "国外"),
    ("Universe Today · 宇宙演化", "https://www.universetoday.com/feed/", "天文地理", "国外"),
    ("NASA Science · 科学解释", "https://science.nasa.gov/feed/", "天文地理", "国外"),
    ("NOAA · 海洋与天气", "https://www.noaa.gov/rss.xml", "天文地理", "国外"),
    ("NIST · 标准与测量原理", "https://www.nist.gov/blogs/taking-measure/rss.xml", "工程原理", "国外"),
    ("MIT · 计算机技术", "https://news.mit.edu/rss/topic/computers", "计算机原理", "国外"),
    ("MIT · 神经科学", "https://news.mit.edu/rss/topic/neuroscience", "脑科学", "国外"),
    ("The Conversation · 科技科普", "https://theconversation.com/global/technology/articles.atom", "科普", "国外"),
]

# 官方目录 https://www.sciencedaily.com/newsfeeds.htm 中的细分订阅。
for name, path, category in [
    ("奇趣冷知识", "strange_offbeat", "冷知识"),
    ("计算机原理", "computers_math/computer_science", "计算机原理"),
    ("人工智能机制", "computers_math/artificial_intelligence", "人工智能"),
    ("通信与网络", "computers_math/internet", "通信原理"),
    ("量子计算", "computers_math/quantum_computers", "计算机原理"),
    ("脑科学", "mind_brain/neuroscience", "脑科学"),
    ("睡眠与梦", "mind_brain/sleep_disorders", "生活常识"),
    ("记忆机制", "mind_brain/memory", "脑科学"),
    ("饮食与营养", "health_medicine/nutrition", "生活常识"),
    ("食品科学", "plants_animals/food", "生活常识"),
    ("运动与健康", "health_medicine/fitness", "生活常识"),
    ("生命演化", "plants_animals/evolution", "生命演化"),
    ("动物行为", "plants_animals/animals", "自然"),
    ("古生物与化石", "fossils_ruins/paleontology", "生命演化"),
    ("考古与文明", "fossils_ruins/archaeology", "考古"),
    ("人类起源", "fossils_ruins/early_humans", "历史"),
    ("物理原理", "matter_energy/physics", "科普"),
    ("化学原理", "matter_energy/chemistry", "科普"),
    ("能源技术", "matter_energy/energy_technology", "工程原理"),
    ("太空与时间", "space_time", "天文地理"),
    ("地震机制", "earth_climate/earthquakes", "天文地理"),
    ("语言起源", "mind_brain/language_acquisition", "文化"),
]:
    FEEDS.append((f"ScienceDaily · {name}", f"https://www.sciencedaily.com/rss/{path}.xml", category, "国外"))

EVERGREEN_SOURCES = [
    dict(name=name, url=url, category=category, region=region,
         topic_kind="知识探索", adapter="rss", item_limit=50, enabled=False)
    for name, url, category, region in FEEDS
]
