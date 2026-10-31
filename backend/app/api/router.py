"""HTTP 路由集中注册；新增页面功能在相应业务子包中实现。"""

from fastapi import APIRouter, Depends

from app.core.auth import protect_management

from . import health, skills, users
from .knowledge import categories, sources, topics
from .workspace import creation, personal, reports

router = APIRouter()
for feature in (health, skills, topics, sources, categories, personal, creation, reports):
    router.include_router(feature.router, dependencies=[Depends(protect_management)])

router.include_router(users.router)
