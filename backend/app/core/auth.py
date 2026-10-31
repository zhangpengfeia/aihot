"""PBKDF2 密码和随机会话；数据库只存 token 摘要。"""

import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.users import LoginSession, User
from app.utils.time import utcnow


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return f"{salt}${digest}"


def verify_password(password, encoded):
    salt, expected = encoded.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(digest, expected)


def current_user(request: Request, db: Session = Depends(get_session)):
    token = request.cookies.get("aihot_session", "")
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    user = db.get(User, session.user_id) if session and session.expires_at > utcnow() else None
    return user if user and user.enabled else None


def require_user(user=Depends(current_user)):
    if not user:
        raise HTTPException(401, "请先登录后访问创作者中心")
    return user


def require_admin(user=Depends(current_user)):
    if not user:
        raise HTTPException(401, "请先登录管理员账号")
    if user.role != "admin":
        raise HTTPException(403, "此操作需要管理员权限")
    return user


def protect_management(request: Request, user=Depends(current_user)):
    management = "/manage" in request.url.path or "/admin" in request.url.path
    if management or request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not user:
            raise HTTPException(401, "请先登录")
        if management and user.role != "admin":
            raise HTTPException(403, "此操作需要管理员权限")


def public_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "enabled": user.enabled,
    }


def seed_admin(db, settings):
    from sqlalchemy import select

    if not db.scalar(select(User).where(User.role == "admin", User.enabled.is_(True))):
        if len(settings.admin_password) < 12:
            raise RuntimeError("首次部署请配置 ADMIN_PASSWORD（至少 12 位）")
        db.add(
            User(
                username=settings.admin_username,
                display_name="管理员",
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
        )
        db.commit()
