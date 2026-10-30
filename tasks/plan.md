# 个人创作工作空间实施计划

按用户直接实现四项功能的要求推进。沿用个人本地资料库，无账户系统；数据由当前实例共用。

| 模块 | 责任 | 依赖 |
| --- | --- | --- |
| favorites | 按仓库稳定 ID 或选题 ID 收藏、编辑备注、取消收藏 | 现有项目与选题 |
| daily-summary | 最近两次成功累计 Star 榜的新上榜、排名变化及正增长 | 现有快照与榜单 |
| collection-status | 最近尝试、最近成功、错误、预计下一次每日调度 | 现有批次与 worker 时间规则 |
| creation-board | 选题唯一创作卡、四阶段、脚本与成品链接 | 现有选题 |

实施顺序：favorites → daily-summary / collection-status → creation-board → 整体验证。

接口使用现有 SQLAlchemy、FastAPI 和 Ant Design。新增表通过可重入 migrate 的 create_all 创建，不改写历史快照。写接口校验来源存在性、长度、状态及链接协议；请求只允许同源浏览器写入，不引入外部服务与新依赖。每日摘要无历史基线时不把首批项目称作新上榜。采集面板的下次执行是计划时间，不声称 worker 在线。

验证：pytest 隔离数据库验证 CRUD、重复收藏、备注保留、看板阶段与字段更新、摘要仓库更名和缺少基线、采集状态时间；前端 TypeScript/Vite 构建与浏览器功能流程。
