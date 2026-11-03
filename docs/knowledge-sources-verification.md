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

## 2026-11-03 热搜聚合平台接入验证

使用 collect_source 实测各公开聚合接口后接入目录平台；不写数据库。结论：

- 60s（60s.viki.moe/v2）仅支持已有 10 个榜单端点；其 bili 端点当前返回 500（线上表现为 B 站 HTTPStatusError），已用 UAPI 聚合的哔哩哔哩接口补上。
- dailyhot-api.vercel.app 备用模板所在示例站连接失败（DNS/网络不可达）；模板保留，管理员可自托管后改地址启用。
- UAPI 聚合（uapis.cn/api/v1/misc/hotboard）实测可用，本轮新接入：哔哩哔哩、知乎日报、腾讯新闻、36氪、虎嗅网、少数派、掘金、CSDN、吾爱破解、豆瓣社区、豆瓣电影、微信读书、虎扑社区、AcFun、爱范儿、什么值得买、历史上的今天（均通过）。
- 华尔街见闻官方热文接口（api-one-wscn.awtmt.com，成功码 20000）实测可用，已接入并新增 success_code 字段映射。
- 未接入平台（微信、机器之心、量子位、Readhub、淘宝/天猫、雪球、第一财经、汽车类、设计类、安全类、社区论坛类等及全部国外平台）：60s/UAPI/DailyHotApi/vvhan/tenapi/oioweb/pearktrue 均无可用榜单接口，官方 RSS/JSON 实测失败（403、302 跳营销页、超时），按“不为预留平台虚构 API”原则保持预留。
- 聚合接口不给直链的平台（吾爱破解、微信读书、历史上的今天）使用百度搜索词链接保持可追溯，与小红书搜索链接方案一致。

## 2026-11-03 第二轮：官方直连接口接入验证

继续为剩余预留平台实测官方/公开接口（collect_source 真实走一遍），新接入 3 个：

- 新浪财经新闻（sina-finance）：zhibo.sina.com.cn 财经 7x24 快讯接口（zhibo_id=152），50 条/次全部带 finance.sina.cn 直链。注：同一接口的体育（151）等其它频道条目不带直链，无法满足可追溯要求，故只接财经频道。
- 开眼视频（eyepetizer）：baobab.kaiyanapp.com 每日精选接口。每日更新条目少（1~2 条），但为平台真实每日榜单；其它 tab 接口（allRec/discovery）内容陈旧或稀疏，弃用。
- 即将上映电影（coming-movies）：猫眼 m.maoyan.com comingList 接口，10 部待映影片，榜单只给影片 id，用猫眼影片页拼链接，“想看数”作为热度指标。

继续尝试但不可用（保持预留）：微信（各聚合均无该榜单）、雪球（接口需 cookie）、第一财经（接口 404）、懂球帝/TapTap/小黑盒（403/404）、水木社区（nforum JSON 接口 404）、机器之心（RSS 跳营销页）、量子位（RSS 403）、Readhub（API 返回 HTML）、淘宝/天猫（接口需签名）、newsnow 聚合（无响应）、tenapi（502）。
