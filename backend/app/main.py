"""ASGI 入口：只装配应用，业务代码位于 api/services。"""

from fastapi import FastAPI

from app.api.router import router


def create_app() -> FastAPI:
    application = FastAPI(title="AIHot GitHub Skills 热榜", version="0.1.0")
    application.include_router(router)
    return application


app = create_app()
