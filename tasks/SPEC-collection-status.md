# collection-status

## 目标与验收
展示 GitHub 最近尝试和成功批次、失败原因、历史记录、北京时间下次每日 02:00 计划；计划非在线心跳，不主动触发采集。

## 结构与风格
后端 app/ 模型与独立 router，前端 src/ 独立组件；沿用 Python snake_case、TypeScript interface 与 Ant Design。示例：`session.get(KnowledgeTopic, topic_id)`。

## 命令与测试
`cd backend && .venv/bin/pytest -q`；`cd frontend && npm run build`。隔离 SQLite 验证真实 API 读写及错误边界，迁移可重复执行。

## 边界
始终校验输入、数据库持久化并保留原有快照；新增表在用户实现请求范围内。涉及外部发布或删除原始采集资料时再确认；不存储凭据、不引入账户与外部通知。
