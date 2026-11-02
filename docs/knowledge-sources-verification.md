# 长青知识来源验证

2026-11-02 使用项目现有 PublicFeedTransport 和 collect_source 实测；不写数据库、不触发采集任务。
仅返回非空、可解析 RSS/Atom 记录的来源进入默认配置。RSS 是结构化订阅接口，不能称为平台官方 JSON API。
新增默认来源通过原有迁移增量导入，不覆盖用户修改、停用、删除的配置；本地启动仍不采集。
部署后执行现有数据库初始化/迁移，再由管理员手动采集知识库，或由线上知识任务采集。
外文源保持原文标题和摘要，不冒充中文内容。只保存来源摘要及链接，不下载全文。

核对目录：
- https://www.sciencenet.cn/RSS.aspx
- https://www.sciencedaily.com/newsfeeds.htm
- https://www.smithsonianmag.com/rss/

## 本次验证

| 来源 | 可解析条目 | 结果 |
| --- | ---: | --- |
| 科学网 · 科普集锦 | 20 | 默认启用 |
| 科学网 · 信息科学 | 0 | 未导入：订阅源过大或包含不支持的 XML 声明 |
| 科学网 · 基础科学 | 0 | 未导入：来源域名解析失败 |
| 科学网 · 生命科学 | 0 | 未导入：订阅源过大或包含不支持的 XML 声明 |
| 科学网 · 工程技术 | 0 | 未导入：订阅源过大或包含不支持的 XML 声明 |
| 科学网 · 人文社科 | 20 | 默认启用 |
| 科学网 · 生活常识 | 20 | 默认启用 |
| 科学松鼠会 · 日常科普 | 0 | 未导入：timed out |
| 果壳 · 科学人 | 0 | 未导入：Client error '404 NOT FOUND' for url 'https://www.guokr.com/rss/' |
| 中科院 · 科研进展 | 0 | 未导入：Client error '404 Not Found' for url 'https://www.cas.cn/syky/index.xml' |
| 阮一峰 · 技术与互联网 | 3 | 默认启用 |
| 科学空间 · 数学与 AI 原理 | 10 | 默认启用 |
| Quanta · 数学与科学原理 | 5 | 默认启用 |
| Science News · 科学解释 | 20 | 默认启用 |
| Science News Explores · 通俗科普 | 20 | 默认启用 |
| ScienceAlert · 冷知识与发现 | 10 | 默认启用 |
| Smithsonian · 科学与起源 | 0 | 未导入：Client error '404 Not Found' for url 'https://www.smithsonianmag.com/rss/science/' |
| Smithsonian · 发明与创新 | 6 | 默认启用 |
| JSTOR Daily · 历史与文化溯源 | 10 | 默认启用 |
| World History Encyclopedia · 世界历史 | 0 | 未导入：Client error '404 Not Found' for url 'https://www.worldhistory.org/feed.rss' |
| HistoryExtra · 历史故事 | 10 | 默认启用 |
| Archaeology · 考古发现 | 10 | 默认启用 |
| Public Domain Review · 冷门历史 | 50 | 默认启用 |
| Computer History Museum · 计算机发展史 | 0 | 未导入：订阅源过大或包含不支持的 XML 声明 |
| IEEE Spectrum · 技术演变 | 30 | 默认启用 |
| Hackaday · 电子工程原理 | 7 | 默认启用 |
| How-To Geek · 数字生活常识 | 0 | 未导入：Server disconnected without sending a response. |
| Explain That Stuff · 工作原理 | 0 | 未导入：Client error '404 Not Found' for url 'https://www.explainthatstuff.com/feed.xml' |
| BPS Research Digest · 心理机制 | 0 | 未导入：Client error '404 Not Found' for url 'https://www.bps.org.uk/research-digest/rss' |
| Nautilus · 大脑与科学 | 10 | 默认启用 |
| EarthSky · 天文与地球 | 10 | 默认启用 |
| Universe Today · 宇宙演化 | 20 | 默认启用 |
| NASA Science · 科学解释 | 0 | 未导入：not well-formed (invalid token): line 8, column 45 |
| NOAA · 海洋与天气 | 10 | 默认启用 |
| NIST · 标准与测量原理 | 40 | 默认启用 |
| MIT · 计算机技术 | 50 | 默认启用 |
| MIT · 神经科学 | 50 | 默认启用 |
| The Conversation · 科技科普 | 0 | 未导入：timed out |
| ScienceDaily · 奇趣冷知识 | 50 | 默认启用 |
| ScienceDaily · 计算机原理 | 50 | 默认启用 |
| ScienceDaily · 人工智能机制 | 50 | 默认启用 |
| ScienceDaily · 通信与网络 | 50 | 默认启用 |
| ScienceDaily · 量子计算 | 50 | 默认启用 |
| ScienceDaily · 脑科学 | 50 | 默认启用 |
| ScienceDaily · 睡眠与梦 | 50 | 默认启用 |
| ScienceDaily · 记忆机制 | 50 | 默认启用 |
| ScienceDaily · 饮食与营养 | 50 | 默认启用 |
| ScienceDaily · 食品科学 | 50 | 默认启用 |
| ScienceDaily · 运动与健康 | 50 | 默认启用 |
| ScienceDaily · 生命演化 | 50 | 默认启用 |
| ScienceDaily · 动物行为 | 50 | 默认启用 |
| ScienceDaily · 古生物与化石 | 50 | 默认启用 |
| ScienceDaily · 考古与文明 | 50 | 默认启用 |
| ScienceDaily · 人类起源 | 50 | 默认启用 |
| ScienceDaily · 物理原理 | 50 | 默认启用 |
| ScienceDaily · 化学原理 | 50 | 默认启用 |
| ScienceDaily · 能源技术 | 50 | 默认启用 |
| ScienceDaily · 太空与时间 | 50 | 默认启用 |
| ScienceDaily · 地震机制 | 50 | 默认启用 |
| ScienceDaily · 语言起源 | 50 | 默认启用 |

验证仅代表本次运行结果，外部接口可能限流、变更或停止；来源管理可独立测试、停用。
