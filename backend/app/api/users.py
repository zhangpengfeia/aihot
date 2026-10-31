"""公开浏览，管理员管理账号及手动采集。"""

import hashlib
import logging
import secrets
import time
from datetime import timedelta
from threading import Lock
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import same_origin_writes
from app.core.auth import current_user, hash_password, public_user, require_admin, verify_password
from app.core.config import get_settings
from app.core.database import get_session
from app.models.users import CollectionTask, LoginSession, User
from app.utils.time import utcnow

router = APIRouter(prefix="/api", dependencies=[Depends(same_origin_writes)])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class UserWrite(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,80}$")
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(default="", max_length=128)
    role: Literal["admin", "user"] = "user"
    enabled: bool = True


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return public_user(user) if user else None


_attempts = {}
_attempt_lock = Lock()


@router.post("/auth/login")
def login(
    body: Credentials, request: Request, response: Response, db: Session = Depends(get_session)
):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _attempt_lock:
        for address in list(_attempts):
            if now - _attempts[address][0] > 300:
                del _attempts[address]
        started, count = _attempts.get(key, (now, 0))
        if count >= 10:
            raise HTTPException(429, "登录尝试过多，请五分钟后重试")
        _attempts[key] = (started, count + 1)
    user = db.scalar(select(User).where(User.username == body.username))
    # 不存在的账号也执行同等密码计算，避免快速枚举用户名。
    encoded = user.password_hash if user else hash_password("dummy")
    valid = verify_password(body.password, encoded)
    if not user or not valid or not user.enabled:
        raise HTTPException(401, "账号或密码错误，或账号已停用")
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at < utcnow()))
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=12),
        )
    )
    db.commit()
    response.set_cookie(
        "aihot_session",
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=43200,
    )
    return public_user(user)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session)):
    token = request.cookies.get("aihot_session", "")
    db.execute(
        delete(LoginSession).where(
            LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
        )
    )
    db.commit()
    response.delete_cookie("aihot_session")
    return {"ok": True}


@router.get("/admin/users", dependencies=[Depends(require_admin)])
def users(db: Session = Depends(get_session)):
    return [public_user(user) for user in db.scalars(select(User).order_by(User.id))]


@router.post("/admin/users", dependencies=[Depends(require_admin)])
def create_user(body: UserWrite, db: Session = Depends(get_session)):
    if len(body.password) < 12:
        raise HTTPException(422, "密码至少 12 位")
    user = User(**body.model_dump(exclude={"password"}), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名已存在") from None
    return public_user(user)


@router.put("/admin/users/{user_id}")
def update_user(
    user_id: int, body: UserWrite, admin=Depends(require_admin), db: Session = Depends(get_session)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if admin.id == user_id and (not body.enabled or body.role != "admin"):
        raise HTTPException(422, "不能停用或取消当前账号的管理员权限")
    if body.password and len(body.password) < 12:
        raise HTTPException(422, "密码至少 12 位")
    for key, value in body.model_dump(exclude={"password"}).items():
        setattr(user, key, value)
    if body.password:
        user.password_hash = hash_password(body.password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名已存在") from None
    return public_user(user)


def run_collection(kind, task_id):
    from app.core.database import get_engine
    from app.services.knowledge.collector import collect_knowledge
    from app.services.skills.collector import collect

    def report(progress, message, status="running"):
        with Session(get_engine()) as db:
            task = db.get(CollectionTask, task_id)
            if progress is not None:
                task.progress = progress
            task.status = status
            task.updated_at = utcnow()
            task.logs = (task.logs + [{"time": task.updated_at.isoformat(), "message": message}])[
                -500:
            ]
            db.commit()

    try:
        report(0, "开始采集")
        result = (collect if kind == "github" else collect_knowledge)(
            get_settings(), progress=report
        )
        if kind == "knowledge" and result.get("skipped"):
            report(100, "已跳过：已有知识采集任务正在执行", "skipped")
        elif kind == "knowledge":
            failed = result["failed"]
            report(
                100,
                f"处理结束：成功来源 {result['sources']}，失败 {failed}，新增 {result['added']} 条",
                "partial" if failed else "success",
            )
        else:
            report(
                100,
                "采集完成" if result else "已跳过：已有任务执行或当前窗口已完成",
                "success" if result else "skipped",
            )
    except Exception as exc:
        report(None, f"采集失败：{type(exc).__name__}，请查看服务端日志", "failed")
        logging.getLogger(__name__).exception("手动采集失败：%s", kind)


@router.post("/admin/collect/{kind}", status_code=202, dependencies=[Depends(require_admin)])
def trigger(
    kind: Literal["github", "knowledge"], tasks: BackgroundTasks, db: Session = Depends(get_session)
):
    if kind == "github" and not get_settings().github_token:
        raise HTTPException(422, "请先配置 GITHUB_TOKEN")
    task = CollectionTask(id=secrets.token_hex(16), kind=kind, updated_at=utcnow(), logs=[])
    db.add(task)
    db.commit()
    tasks.add_task(run_collection, kind, task.id)
    return {"task_id": task.id, "message": "采集请求已接受"}


@router.get("/admin/collection-tasks/{task_id}", dependencies=[Depends(require_admin)])
def collection_task(task_id: str, db: Session = Depends(get_session)):
    task = db.get(CollectionTask, task_id)
    if task is None:
        raise HTTPException(404, "采集任务不存在")
    return {
        "id": task.id,
        "kind": task.kind,
        "status": task.status,
        "progress": task.progress,
        "logs": task.logs,
        "updated_at": task.updated_at,
    }


class DashboardWrite(BaseModel):
    cards: list[Literal["projects", "overview", "new_entries", "risers", "growth", "knowledge", "hotlists", "favorites"]] = Field(max_length=8)


@router.get("/workspace/dashboard-preferences")
def dashboard_preferences(user=Depends(current_user), db: Session = Depends(get_session)):
    from app.models.users import DashboardPreference

    if user is None:
        raise HTTPException(401, "请先登录")
    row = db.get(DashboardPreference, user.id)
    return {"cards": row.cards if row else ["projects", "knowledge", "hotlists"]}


@router.put("/workspace/dashboard-preferences")
def save_dashboard(
    body: DashboardWrite, user=Depends(current_user), db: Session = Depends(get_session)
):
    from app.models.users import DashboardPreference

    if user is None:
        raise HTTPException(401, "请先登录")
    row = db.get(DashboardPreference, user.id)
    if row is None:
        row = DashboardPreference(user_id=user.id)
        db.add(row)
    row.cards = list(dict.fromkeys(body.cards))
    db.commit()
    return {"cards": row.cards}
