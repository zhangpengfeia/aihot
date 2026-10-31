# 在项目根目录执行 make start；命令路径支持包含空格的项目目录。
.DEFAULT_GOAL := help
.PHONY: help install start dev api frontend worker knowledge-worker migrate check build
PYTHON := backend/.venv/bin/python

help:
	@printf '%s\n' 'make install           安装前后端依赖（需要 uv、npm）' 'make start / make dev  仅启动前端和 API，不启动采集；Ctrl+C 统一停止' 'make api               单独启动 API' 'make frontend          单独启动前端' 'make worker            单独启动 GitHub 定时采集' 'make knowledge-worker  单独启动知识定时采集' 'make migrate           创建或升级数据库结构' 'make check             后端检查与测试、前端格式检查' 'make build             构建前端'

install:
	cd backend && uv sync --frozen
	cd frontend && npm ci

start dev:
	@test -x "$(PYTHON)" || { echo '请先执行 make install'; exit 1; }
	@"$(PYTHON)" scripts/dev.py

api:
	cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev -- --port 5173 --strictPort

worker:
	cd backend && .venv/bin/python -m app.runtime.github_worker

knowledge-worker:
	cd backend && .venv/bin/python -m app.runtime.knowledge_worker

migrate:
	cd backend && .venv/bin/python -m app.runtime.migrations

check:
	cd backend && .venv/bin/ruff check app tests
	cd backend && .venv/bin/python -m pytest
	cd frontend && npm run format:check

build:
	cd frontend && npm run build
