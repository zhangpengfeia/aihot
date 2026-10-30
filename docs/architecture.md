# 项目目录与职责

本项目使用 React/TypeScript + FastAPI + MySQL。按现有业务拆分，参考页面目录组织，不创建尚无业务的 agents/chat 等空模块。

## 后端

```text
backend/app/
├── main.py                  # ASGI 应用装配、create_app
├── api/                     # HTTP 路由和请求校验依赖
│   ├── router.py            # 统一注册，业务模块不导入 main
│   ├── health.py
│   ├── skills.py            # 项目库、榜单、历史快照
│   ├── knowledge/           # 题库查询、采集接口、分类管理
│   └── workspace/           # 收藏备注、创作卡、变化和状态报告
├── core/                    # 环境配置、来源配置、数据库基础设施
├── infrastructure/          # GitHub 客户端、公网 HTTP 传输
├── models/                  # skills/knowledge/workspace 数据表
├── schemas/                 # HTTP 输入模型和合法枚举
├── services/                # 业务编排、规则、持久化与资料映射
│   ├── skills/              # GitHub 采集、用途/安装信息、响应映射
│   ├── knowledge/           # 采集、标准化、适配器、分类目录与配置管理
│   └── workspace/           # 收藏和创作卡共用资料映射
├── runtime/                 # 两个 worker、建表与迁移命令
└── utils/                   # 无副作用的日期、时区、URL 身份工具
```

根目录 worker.py、knowledge_worker.py、migrate.py、init_db.py 是兼容命令入口。实际实现只有一份，位于 runtime；现有 `python -m app.worker` 等命令继续可用，Compose 使用新的标准模块路径。

模型使用 `models/__init__.py` 统一注册，表名、字段和迁移语义保持原样。此次重构不改变数据库结构，也不需要迁移现有数据。服务与工具不导入 main，避免应用装配与业务形成循环依赖。

## 前端

```text
frontend/src/
├── main.tsx                 # React 挂载、中文 locale、样式入口
├── app/                     # 页面选择、菜单定义、Ant Design 主题
├── api/http.ts              # 统一请求与错误处理
├── components/
│   ├── common/              # 共用页面标题
│   ├── layout/              # 布局、侧栏收缩、面包屑
│   └── workspace/           # 收藏备注、加入创作看板等共用操作
├── hooks/                   # 可取消的资源查询、周期刷新
├── styles/                  # 布局、共用组件、响应式、工作空间、导航
├── types/                   # 接口契约，按 skills/knowledge/workspace 分类
├── utils/date.ts            # 北京时间格式化
└── views/
    ├── skills/              # 项目库、当前/历史榜单、详情抽屉、查询 hook
    ├── knowledge/           # 知识题库、接口管理、分类整理
    │   ├── components/      # 筛选、表格、接口表单、测试预览、选题详情
    │   └── hooks/           # 筛选和分页查询状态
    └── workspace/           # 收藏、每日摘要、采集状态、创作看板
```

App 只管理页面选择和全局 Skill 详情抽屉。页面读取自己的查询 hook，通用请求和日期处理不复制到页面。大页面的表单、预览、表格与详情按职责拆开。样式入口按原顺序引入各文件，保持原有级联与视觉表现。

## 修改功能时的落点

| 改动 | 位置 |
|---|---|
| 新增/修改 HTTP 接口 | backend/app/api 对应领域；输入放 schemas |
| 新增采集渠道的解析方式 | services/knowledge/adapters.py |
| 默认来源、数量和地区配置 | core/sources.py；用户覆盖仍使用 .env |
| 修改数据库表 | models + runtime/migrations.py；显式迁移 |
| 修改采集时刻 | runtime 中对应 worker |
| 新页面 | frontend/src/views 对应领域，并在 app 注册菜单与页面 |
| 页面独有组件 | 对应 views/.../components |
| 跨页面通用行为 | components/hooks/api/utils/types |

## 检查

在 backend 执行 `.venv/bin/ruff check app tests` 和 `.venv/bin/python -m pytest`；在 frontend 执行 `npm run format:check` 和 `npm run build`。TypeScript 同时检查未使用的变量、参数和导入。首次部署与运行方式见根目录 README。
