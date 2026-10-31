# AIHot · GitHub Skills 热点资料库

React + TypeScript + Ant Design 6 前端，Python/FastAPI 后端，MySQL 8.0 持久化。每天北京时间凌晨 0 点发现和观测 Agent/Claude/Codex Skills 项目，展示累计 Star Top 20、24 小时净增长 Top 20、历史榜单、README 资料及 Markdown 导出。

## 用户和管理员

网站无需登录即可浏览。首次运行前在 `backend/.env`（生产为 `shared/backend.env`）设置 `ADMIN_USERNAME` 和至少 12 位的 `ADMIN_PASSWORD`，执行 `make migrate` 初始化管理员。已有管理员不会被环境变量覆盖。

左下角头像打开登录、采集状态菜单。管理员登录后增加“用户管理”，可新增账号、分配角色、停用和重置密码；在采集状态面板手动触发 GitHub 或知识库采集。采集复用既有互斥锁和时间窗口幂等，重复请求可能跳过。请求在 API 进程后台运行，重启不会自动恢复请求，可查看状态后重试。

登录会话有效期 12 小时，修改账号会撤销该账号会话。创作者中心登录后可见；收藏、备注和创作脚本按账号隔离，来源配置及用户管理仅管理员可修改。升级迁移会把旧共享收藏和创作归属最早创建的管理员。

## 知识标签、全网热搜与首页卡片

知识选题库提供 279 个热门和小众细分标签，和已有内容分类合并到同一个可搜索多选框。多选命中任意一项，与地区、来源、日期及关键词条件同时生效。标签依据标题/摘要文本规则匹配，不代表已收录同等数量的内容。

新增百度、微博、小红书、知乎、B站、抖音、头条、贴吧、IT之家、懂车帝的 60s 聚合来源，以及 30 个默认停用的 DailyHotApi 备用模板。社区公共接口可能限流或失效，可在接口管理测试、替换地址和启停。全网热搜显示最后成功榜单及时间，失败保留旧榜单并展示错误，不伪造热度。参考 [60s API 文档](https://docs.60s-api.viki.moe/) 和 [DailyHotApi](https://github.com/imsyy/DailyHotApi)。

首页“编辑首页卡片”可选择项目、知识库、热搜、我的收藏，支持全部隐藏。登录后按账号保存；访客仅保存在当前浏览器，收藏卡片需登录。

更新后先备份数据库，再运行 `make migrate` 创建新表、升级个人数据归属并增量导入来源，然后重启 API。管理员点击左下角头像进入采集状态面板，手动采集知识库后才会产生新榜单；`make start` 继续只启动前端和 API。迁移后不要回退到仍将收藏/创作当作共享数据的旧版本。

## 热度含义

- 累计榜按当前观测 Star 数排序，是默认榜单。
- 增长榜按约 24–26 小时净增 Star 排序，详情展示实际基线时间。首次部署须积累至少 24 小时数据，不伪造历史增长。
- 每轮每个搜索词取 Star 排序、更新排序各前 100 项；默认选累计 Star 和最近推送各 100 个候选，加最近跟踪的 200 个，合并去重后重新获取统计。每轮最多约 400 个仓库，相关上限可配置。只输出规则匹配且本轮观测成功的项目，不足 20 个不补假数据。
- Skills 识别依据：README 提及 SKILL.md、匹配专题 Topics 或 Agent/Claude/Codex Skills 关键词。排除归档仓库和 Fork。这是启发式识别，可能误判/漏判；不是 GitHub 官方或全网热榜。
- 每轮耗时取决于仓库数、API 延迟和限流。每天北京时间 00:00 启动 GitHub 采集，完成后发布榜单，不是秒级实时服务。前端每分钟读取已存榜单。

## 本地启动

要求 Python 3.11+、Node.js 20.19+/22.12+、MySQL 8.0 和可访问 GitHub API 的网络。推荐安装 uv，后端依赖由 uv.lock 锁定，前端由 package-lock.json 锁定。

### Make 一键启动（推荐）

在项目根目录执行；已有依赖和数据库结构时，直接运行 `make start`：

```bash
make install    # 首次安装前后端依赖
# 首次使用：复制 backend/.env.example 为 backend/.env 并填写配置
make migrate    # 首次建表或版本升级时执行
make start      # 仅前端 + API，不启动采集
```

访问 http://127.0.0.1:5173，按 `Ctrl+C` 统一停止本次启动的服务。`make dev` 与 `make start` 等价。启动不会自动安装依赖或修改表结构；端口 8000 / 5173 被占用时会提示先停止原服务。本地及线上均通过 MYSQL_HOST/MYSQL_PORT 直接连接 MySQL，默认配置为 152.136.228.231:3306，无需 SSH 隧道。

本地 `make start` / `make dev` 不启动 GitHub 或知识库采集进程。需要采集时可使用管理员手动采集，或明确执行 `make worker` / `make knowledge-worker`。线上定时采集保持不变。任一服务退出会停止本次启动的其他服务，避免留下残余进程。可用 `make api`、`make frontend`、`make worker`、`make knowledge-worker` 单独启动；`make help` 查看全部命令，`make check` 检查代码和测试，`make build` 构建前端。

### 1. 准备 MySQL

用管理账号执行以下示例（生产环境调整用户名、来源主机和密码）：

```sql
CREATE DATABASE aihot CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'aihot'@'localhost' IDENTIFIED BY 'replace-with-your-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES ON aihot.* TO 'aihot'@'localhost';
```

应用账号需要 `GET_LOCK`/`RELEASE_LOCK` 可用，MySQL 8.0 标准安装支持这些函数。Docker 连接时 MySQL 用户来源主机应允许对应容器网络，不能仅允许 localhost。

### 2. 配置后端

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 MYSQL_* 和 GITHUB_TOKEN
cd backend
uv sync --frozen
uv run python -m app.init_db
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

GitHub Token 只需读取公开仓库，无需赋予仓库写权限。默认采集量超过匿名额度，worker 要求配置 Token。不要把 .env 提交到 Git。API 文档：http://127.0.0.1:8000/docs 。

如不使用 uv，可在 Python 3.11+ 的虚拟环境中执行 `pip install -e '.[dev]'`。

### 3. 启动采集（另一个终端）

```bash
cd backend
uv run python -m app.worker
# 或立即手动采集一次（保留批次幂等）：
uv run python -m app.worker --once
```

GitHub worker 启动后等待每天北京时间 00:00 执行，不立即采集，也不补采错过的日期。每轮结束后等待下一个 00:00，执行期间不重叠；失败后等待下一次每日调度，可使用 `--once` 手动立即重试。需要进程持续运行，线上建议 Docker Compose 或进程管理器。底层保留现有半小时批次幂等与历史兼容，手动执行时同一窗口的成功批次不会重复写。知识选题采集仍保持每半小时执行。

### 4. 启动 React（另一个终端）

```bash
cd frontend
npm ci
npm run dev
```

访问终端显示的地址（默认 http://127.0.0.1:5173）。Vite 将 `/api` 转发到 8000。开发时 API 文档直接访问 8000 端口。

## Docker 部署（使用已有 MySQL）

`zhangff.cn` 生产部署与 GitHub 自动发布见 [服务器部署说明](deploy/README.md)。包含 MySQL 直连、常驻定时采集、HTTPS/认证、发布健康检查与应用版本回退；6 个生产容器日志合计预算 600 MiB，达到阈值自动轮转。

1. 配好 backend/.env。容器中 MYSQL_HOST 应填写数据库网络地址；macOS Docker 访问宿主机可使用 host.docker.internal，不能填写 127.0.0.1。
2. 执行 `docker compose up --build -d`。
3. 访问 http://127.0.0.1:8080 。`docker compose logs -f worker` 查看采集状态。

默认只绑定本机。公开服务应配置反向代理认证和 TLS。项目不包含数据库容器，也不会修改你已有的数据库内容；初始化命令仅创建缺失的本项目表。修改模型后需要编写迁移。

## 配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| MYSQL_HOST / MYSQL_PORT | 152.136.228.231 / 3306 | MySQL 连接地址 |
| MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD | aihot / aihot / 空 | 数据库和账号 |
| GITHUB_TOKEN | 空 | 公开仓库读取凭证，worker 必填 |
| SEARCH_QUERIES | 见 config.py | JSON 字符串数组；查询自动排除归档和 Fork |
| CANDIDATE_LIMIT | 200 | 搜索候选上限，20–1000 |
| TRACKED_LIMIT | 200 | 跟踪旧项目的上限，20–1000 |
| REQUEST_INTERVAL | 2.1 | 每个 API 请求前等待秒数 |

超过范围的旧项目不再持续观测；返回候选池后有合适的基线才再次进入增长榜。抓取错误采用有限重试，403/429 立即终止本轮，等待下一次每日调度，不绕过限流。README 缺失不算失败，资料太长截取前 100,000 字符。批次搜索不完整或网络错误会使本轮失败，保留上一期成功榜单。历史受容量保留策略约束，达到阈值会自动淘汰最旧采集数据，详见下文“采集存储上限”。

## API

| 路径 | 功能 |
|---|---|
| GET /api/health | MySQL 连通性 |
| GET /api/rankings?kind=stars | 最新成功累计榜 |
| GET /api/rankings?kind=growth&run_id=1 | 指定批次增长榜 |
| GET /api/runs?day=2026-10-30 | 北京时间某日全部批次 |
| GET /api/runs?limit=100&offset=100 | 历史分页 |
| GET /api/snapshots/1 | 某次观测的资料详情 |
| GET /api/snapshots/1/markdown | 下载资料 |

## 开发与验证

```bash
cd backend
uv run ruff check app tests
uv run pytest
cd ../frontend
npm run format:check
npm run build
```

测试通过 SQLite 隔离测试识别、增长、事务回滚、历史不可变及 API，额外验证 MySQL 方言 DDL。它不能替代真实 MySQL 8.0 的建表、互斥锁与网络集成验证。MySQL 集成测试见 `tests/test_mysql.py`，设置 `AIHOT_TEST_MYSQL=1` 后运行；只对配置指向的**专用空测试库**执行，测试完成删除该测试库内本项目表。

## 目录与维护约定

```text
backend/app/api/             按功能拆分的 HTTP 接口
backend/app/core/            配置、默认来源与数据库
backend/app/models/          Skill / 知识 / 工作空间表定义
backend/app/services/        按领域拆分的业务规则与采集服务
backend/app/infrastructure/  外部 HTTP 与 GitHub 客户端
backend/app/schemas/         请求输入模型
backend/app/runtime/         worker、初始化与迁移
backend/app/utils/           纯工具
backend/tests/               核心规则和接口测试
frontend/src/app/            应用壳、导航和主题
frontend/src/views/          skills / knowledge / workspace 页面
frontend/src/components/     跨页面共用组件
frontend/src/hooks/          共用加载和刷新行为
frontend/src/api/            HTTP 请求
frontend/src/types/          接口类型
frontend/src/styles/         按职责拆分的样式
frontend/src/utils/          日期等工具
compose.yaml                Web/API/worker 部署
 docs/decisions/             架构与排名决策
```

函数使用类型注解，中文注释解释业务规则、边界和取舍。修改排名逻辑应同步文档和测试；数据库后续升级应增加显式迁移。README 为项目作者原文，未经本工具实测；许可证仅记录原始元数据，使用素材前请查看原项目条款。

接口参考：[GitHub 搜索 API](https://docs.github.com/en/rest/search/search)、[仓库资料 API](https://docs.github.com/en/rest/repos/contents)、[API 限流](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)。

## v0.2：Skill 库与知识选题库

菜单已调整为：

- **Skill 库**：项目资料、今日热榜、历史热榜。项目资料保留每个仓库最近一次快照，支持名称搜索和脚本写作、配音、字幕、动画、剪辑等多标签用途筛选。即使项目掉出 Top 20，也可以在资料库中找到。安装方式摘自 README 安装章节，许可证记录 GitHub 元数据；分类为规则匹配，安装命令未经执行验证。
- **知识选题库**：科技、商业、历史、自然、生活等领域的订阅资料。支持内容分类、关键词、类型和发布日期筛选、分页及 Markdown 导出；保存知识摘要、原始来源链接、来源名称、发布日期、首次采集时间和视频切入角度。

知识默认来源为 MIT 人工智能、BBC 商业、Smithsonian 历史、NASA、少数派。可通过 `KNOWLEDGE_SOURCES` JSON 数组添加任意内容分类来源（配置示例见 backend/.env.example）；来源必须提供 RSS 2.0 或 Atom。一个来源失败不会阻断其他来源，来源状态会在页面展示。

知识摘要为订阅源摘要摘录，保留原语言，不调用模型翻译；缺失摘要时明确提示。发布日期缺失或无法解析时保留为空，绝不使用采集日期冒充。视频切入角度是按内容分类生成的规则建议，尚未进行事实推理与核验。知识“热点候选”以新发布资料供选题，“知识探索”供小众与常青内容发现，**不具备阅读量或全网热度排名依据**。默认按发布日期降序，无发布日期时按首次采集时间排序。

### 从 v0.1 升级

先备份数据库，然后在 backend 目录执行：

```bash
uv run python -m app.migrate
```

迁移会创建知识表，并为旧 snapshots 表添加可空的 categories JSON、installation TEXT 两列，不删除历史数据。需要账号有 ALTER 权限。命令可重复执行，但请不要并发运行多个迁移进程。全新数据库可以执行 init_db 或 migrate。Docker Compose 的 init 服务已改为运行 migrate。

### 运行知识采集

```bash
cd backend
uv run python -m app.knowledge_worker
# 单次执行：
uv run python -m app.knowledge_worker --once
```

独立于 GitHub worker，每半小时运行，无需 GitHub Token。相同来源同一窗口成功后不重复采集，失败来源后续可重试。按规范化原文 URL 去重，去掉 utm_* 和片段；不同网站对同一事件的转载仍保留各自资料，不自动认定为独立证据。每个源每轮最多读取 50 项、2MB 内容。知识和 GitHub 的 worker 必须分别保持运行，Compose 已包含两者。

新增接口：`GET /api/skills`（category/q/page/page_size）、`GET /api/knowledge/topics`（category/topic_kind/q/day/page/page_size）、`GET /api/knowledge/meta`、`GET /api/knowledge/topics/{id}/markdown`。知识来源来自服务端配置，浏览器不能写入任意抓取地址。

### 国内与国外题材

知识库支持国内/国外筛选，并可与内容分类、类型、关键词、发布日期组合。地区优先根据标题和摘要中明确的中国或海外关键词判断；无明确线索时按来源的 `region` 配置归类（默认 `国外`，少数派配置为 `国内`）。涉及中国的跨国话题优先归国内。详情与 Markdown 保留判断依据，这是整理标签，可能需要人工核实。

`KNOWLEDGE_SOURCES` 每个来源可增加 `"region":"国内"` 或 `"region":"国外"`。运行 `python -m app.migrate` 为旧知识表增补 region、region_basis 字段与索引，并给能匹配当前配置的旧来源资料补地区；未知旧来源保留“待分类”，不会凭空改为国外。所有题材模式仍能看到待分类记录。


内容分类列表通过中文维基百科免费 MediaWiki API 远程获取，无需 API Key。后端在 `/api/knowledge/meta` 首次请求时拉取“主要话题分类”的子分类，与已配置来源及已有选题分类合并去重。`category_catalog` 返回来源、状态、远程数量、最近成功时间和错误信息，前端展示同步状态及来源链接。

分类成功后在每个 API 进程内缓存 24 小时，失败后 5 分钟重试，并保留上次成功结果；进程重启会清空缓存。首次同步失败时使用本地分类，刷新页面不会跳过重试间隔。部署后端需要能访问 `zh.wikipedia.org`；每次请求超时 4 秒，分页最多 5 页。远程分类只影响分类列表，不自动采集文章，也不重写历史选题的分类。


## 个人创作工作空间

新增四个菜单：

- **收藏与个人备注**：在项目资料或知识选题详情点击“收藏 / 备注”。收藏按仓库稳定 ID 或选题 ID 保存；项目更名后备注仍保留。取消收藏不会清空备注，可在“全部收藏与备注记录”查看。删除记录同时移除该条收藏和备注，不影响原始资料。
- **每日变化摘要**：对比最近两次成功的累计 Star 榜，显示新上榜与排名上升；正增长展示本期有有效 24h 基线的前 10 个项目。新上榜表示未进入前期榜单，不代表新创建仓库。只有一期数据时不判断榜单变化；采集不连续时按页面显示的两期时间理解对比范围。
- **采集状态面板**：查看最近尝试、最近成功、最近失败、最近 10 个 GitHub 批次及知识来源状态。下次执行时间按北京时间每日 00:00 计算，是计划时间；面板不提供 worker 在线心跳，也不会触发采集。榜单超过 26 小时未更新时提示检查。
- **选题创作看板**：知识选题点击“加入创作看板”，重复添加返回已有卡片。支持待筛选、待创作、制作中、已发布四阶段切换，以及脚本、成品链接编辑。删除卡片不会删除原始选题；成品链接仅允许 http(s)。

### 升级与运行

已有数据库先备份，再在后端执行（新增 `personal_items`、`creation_cards` 表，可重复运行且保留已有数据）：

```bash
cd backend
uv run python -m app.migrate
```

随后重启 API 并重新构建前端。Docker Compose 部署执行 `docker compose up -d --build`，初始化服务会运行迁移。当前版本沿用个人实例模式，收藏、备注、脚本由同一实例的访问者共用；没有账户隔离。

### 新增 API

| 接口 | 用途 |
| --- | --- |
| `GET /api/workspace/items` | 收藏列表；支持 `q`、`kind`、分页，`all_records=true` 包含已取消收藏的备注记录 |
| `GET /api/workspace/items/{repository或topic}/{id}` | 读取收藏状态和备注；项目 ID 为 repo_id，选题 ID 为 topic_id |
| `PUT /api/workspace/items/{kind}/{id}` | 保存 `favorite` 和/或 `note`，未传字段保留 |
| `DELETE /api/workspace/items/{kind}/{id}` | 删除收藏和备注记录 |
| `GET /api/workspace/daily-summary` | 最近两期成功榜单变化与本期正增长 |
| `GET /api/workspace/collection-status` | 采集记录及计划时间 |
| `GET /api/workspace/cards` | 创作卡列表，支持标题关键词 `q` |
| `POST /api/workspace/cards` | 按 `topic_id` 幂等添加创作卡 |
| `PATCH /api/workspace/cards/{id}` | 编辑 `stage`、`script`、`output_url`，未传字段保留 |
| `DELETE /api/workspace/cards/{id}` | 删除创作卡 |

写入接口采用 JSON，并拒绝跨源浏览器写请求。API 与页面应同源部署；自定义反向代理需保留原始 Host（项目 Nginx 已配置）。

## v0.6：多渠道知识融合与采集接口管理

导航统一为 **知识选 → 知识选题库 / 采集接口管理**，不再保留重复的来源管理入口。分类合并与可见性整理放在采集接口管理的“分类整理”标签中。

默认接口目录扩充到 22 项，覆盖科技、人工智能、商业、历史、自然、生活、文化、教育、健康、社会、体育、心理、环境、旅行等题材。包括原有渠道、中新网 7 个行业订阅、ScienceDaily 3 个研究订阅、Smithsonian 文化与旅行、arXiv 人工智能 API、Hacker News 热榜 API、NASA 图像元数据 API。Wikipedia 历史事件接口目前会拒绝部分网络请求，故默认停用，可由用户测试后启用。配置数不代表实际可用或本轮成功数，以管理页面最近采集状态为准。

采集适配器：

| adapter | 用途 |
|---|---|
| rss | RSS 2.0 / Atom，包含 arXiv 查询 API |
| hackernews | 官方 topstories / beststories / newstories API；最多 100 条、4 路并发读取详情 |
| wikipedia | 官方“历史上的今天”事件 JSON API；事件年份不冒充文章发布日期 |
| json | 公开 JSON GET API；通过点路径映射列表、标题、链接、摘要、发布日期 |

Hacker News 投票只表示该社区的热度，不能和其他来源作全网热度对比。缺少摘要时明确提示，不把标题自动编成“事实摘要”。所有渠道继续经过公网地址校验、每跳重定向校验、请求超时和 2MB 大小限制。不支持需要 OAuth、签名或付费授权的 API；这些需另加针对性适配器。

接口管理支持新增、编辑地址/类型/字段映射、删除、启停和连接测试。删除是停用并隐藏配置，保留历史选题、引用、收藏和备注；用户主动重新新增同地址可恢复该配置。迁移增量导入新默认渠道，保留原有编辑、停用和删除状态。

单次采集上限可设 1–200（Hacker News 上限 100），RSS 默认由原来 50 提升到 100。历史记录持续积累；上游只返回最新资料的渠道不能凭空补齐历史。按规范化原文链接去重时，通过 knowledge_citations 保留每个发现渠道，不把转载当作独立事实证据；不同 URL 的同事件暂不自动合并。

通用 JSON 示例：接口返回 `{"data":{"items":[{"title":"选题","url":"https://example.com/a","description":"摘要","published_at":"2026-10-30T10:00:00Z"}]}}`，配置：

```json
{"items_path":"data.items","title_field":"title","url_field":"url","summary_field":"description","date_field":"published_at"}
```

路径支持 `data.0.title` 数组下标；`url_prefix` 可将文章 ID 拼接为来源链接。地址不可含账号密码，勿在 URL 或映射中填私密 Token。

分页接口 `/api/knowledge/topics` 支持 page/page_size（1–100），并返回 total、page、page_size、total_pages。可组合 category、region、topic_kind、q、day、source_id 和 sort_by（published/collected）。相同日期使用稳定 ID 排序。页面提供 20/50/100 条每页、直接跳页、首尾两处分页与总数，切换过滤条件自动回到第一页。

升级：先按需备份数据库，然后运行 `cd backend && uv run python -m app.migrate`，随后重启后端和知识 worker。迁移创建引用表及接口类型、映射、删除标记等可空字段，不删除已有资料。新知识运行 `uv run python -m app.knowledge_worker --once` 可立即验证入库。


补充：Hacker News 搜索 API（hn.algolia.com）作为独立备选接口，一次读取热点列表，减少逐条请求带来的超时；其 points 仅代表社区指标。通用 JSON 映射可选 score_field。公网传输优先 IPv4，连接失败可尝试第二个已校验地址；数据库连接/读写设置超时，批量入库减少数据库查询往返。数据库使用直连，断线后本轮事务回滚，恢复后可重试，不补造成功记录。


## 代码组织

完整目录、模块职责和新增功能的放置位置见 [项目架构说明](docs/architecture.md)。前后端已按领域和职责拆分，现有运行命令和 HTTP 地址保持兼容。本次目录整理无需数据库迁移。


GitHub 请求遇到临时断连、读取/连接超时或代理连接异常时，首次请求失败后最多重试 5 次（最多请求 6 次），重试前分别退避 1、2、4、8、16 秒；每次仍遵守请求间隔。HTTP 5xx 使用相同重试策略，401/403/429 不继续重试。重试期间保留本轮内存中的已抓取记录；全部尝试失败仍将批次标记失败，不发布不完整榜单。这不提供跨进程断点续采，失败退出后可在 backend 目录执行 `.venv/bin/python -m app.worker --once` 重新运行。

GitHub 采集日志会输出搜索进度与去重数量、候选及历史补充数量、当前仓库、已检查/匹配/未匹配/跳过数量、入库开始及成功结果、累计耗时。采集中匹配数量代表内存中的待保存记录，只有事务提交后的“采集成功”日志才代表本轮已入库；失败日志会保留失败前的进度统计。

## 采集存储上限

默认有效数据估算上限 **5 GB**（1 GB = 1,000,000,000 字节）。在 `backend/.env` 配置：

```dotenv
DATABASE_MAX_SIZE_GB=5
DATABASE_CLEANUP_TARGET_RATIO=0.9
```

重启 API、GitHub worker 与知识 worker 后生效。两种采集都会在开始及写入前检查容量，为新增内容预留空间；达到阈值时自动永久删除最旧采集数据，目标降至约 90%（默认 4.5 GB）。按采集时间排序，GitHub 以完整批次淘汰，知识选题同时删除渠道引用；每次检查最多淘汰 1000 个批次/选题。未达到目标但足以容纳本次写入时可继续；仍不足则暂停本轮，下次任务继续检查。

收藏、个人备注、创作卡片引用的知识选题保留；每个仓库最新快照所在批次、最近两期成功榜单、最近 26 小时及运行中批次保留，最新一个知识选题保留。仓库身份、来源配置、个人资料和创作脚本不删除。保留数据已占满或单批数据太大时停止写入，在日志记录原因。清理后采集失败不会恢复已经删除的历史。

采集状态面板显示估算已用容量、上限与清理规则；日志记录清理前后容量及删除数量。容量汇总应用表字段的实际字节长度，并估算行与索引开销，**不是 MySQL 磁盘文件的硬上限**，不包含数据库日志、备份及临时文件。DELETE 释放空间供数据库复用，文件不会立即缩小，不自动执行锁表重建。严格限制物理磁盘占用需要在服务器设置磁盘配额；仍需独立备份。容量扫描在数据库内聚合，大数据量时应关注查询开销。

管理员点击“立即采集”后需二次确认；确认后可查看进度条和最近 500 条任务日志（每两秒刷新），关闭弹窗后可通过“查看采集进度”重新打开。本次升级新增 `collection_tasks` 表，已有部署需先运行 `python -m app.runtime.migrations`。进度按已处理项目或来源计算，搜索阶段保持等待；任务状态持久化在数据库中，服务重启不会自动恢复中断的后台任务。
