"""真实 HTTP 验证公开访问、管理员权限和会话撤销。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.auth import hash_password
from app.core.database import Base, get_session
from app.main import create_app
from app.models.users import User


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    app = create_app()
    with Session(engine) as db:
        db.add(
            User(
                username="admin",
                display_name="管理员",
                role="admin",
                password_hash=hash_password("test-password-123"),
            )
        )
        db.commit()
        app.dependency_overrides[get_session] = lambda: db
        with TestClient(app) as http:
            yield http
    engine.dispose()


def test_public_and_admin_permissions(client):
    assert client.get("/api/auth/me").json() is None
    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/admin/collect/knowledge", json={}).status_code == 401
    assert client.get("/api/knowledge/manage/sources").status_code == 401
    assert client.get("/api/knowledge/manage/categories").status_code == 401
    assert client.post("/api/knowledge/manage/sources", json={}).status_code == 401
    assert (
        client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "test-password-123"}
        ).status_code
        == 200
    )
    created = client.post(
        "/api/admin/users",
        json={
            "username": "reader",
            "display_name": "读者",
            "password": "reader-password-123",
            "role": "user",
        },
    )
    assert created.status_code == 200
    assert "password_hash" not in created.json()
    assert (
        client.post(
            "/api/admin/users",
            json={"username": "reader", "display_name": "重复", "password": "reader-password-123"},
        ).status_code
        == 409
    )
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert client.get("/api/auth/me").json() is None
    client.post("/api/auth/login", json={"username": "reader", "password": "reader-password-123"})
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/admin/collect/knowledge", json={}).status_code == 403
    assert client.get("/api/knowledge/manage/sources").status_code == 403
    assert client.get("/api/knowledge/manage/categories").status_code == 403
    assert client.post("/api/knowledge/manage/sources", json={}).status_code == 403


def test_csrf_and_self_disable(client):
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "test-password-123"},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": "test-password-123"}
    )
    assert "HttpOnly" in response.headers["set-cookie"]
    user = response.json()
    assert (
        client.put(f"/api/admin/users/{user['id']}", json={**user, "enabled": False}).status_code
        == 422
    )
    old_cookie = client.cookies.get("aihot_session")
    assert (
        client.put(
            f"/api/admin/users/{user['id']}", json={**user, "password": "updated-password-123"}
        ).status_code
        == 200
    )
    client.cookies.set("aihot_session", old_cookie)
    assert client.get("/api/auth/me").json() is None


def test_admin_can_trigger_both_collectors(client, monkeypatch):
    from app.api import users
    from app.core.config import get_settings

    calls = []
    monkeypatch.setattr(
        users, "run_collection", lambda kind, task_id: calls.append((kind, task_id))
    )
    monkeypatch.setattr(get_settings(), "github_token", "test-token")
    client.post("/api/auth/login", json={"username": "admin", "password": "test-password-123"})
    for kind in ("github", "knowledge"):
        response = client.post(f"/api/admin/collect/{kind}", json={})
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        snapshot = client.get(f"/api/admin/collection-tasks/{task_id}")
        assert snapshot.status_code == 200
        assert snapshot.json()["status"] == "pending"
        assert snapshot.json()["kind"] == kind
    assert [kind for kind, _ in calls] == ["github", "knowledge"]
    assert client.get("/api/admin/collection-tasks/missing").status_code == 404
    assert client.post("/api/admin/collect/unknown", json={}).status_code == 422


@pytest.mark.parametrize(
    "outcome,status", [(True, "success"), (False, "skipped"), ("error", "failed")]
)
def test_collection_task_progress(client, monkeypatch, outcome, status):
    from app.api import users
    from app.core import database
    from app.models.users import CollectionTask
    from app.services.skills import collector
    from app.utils.time import utcnow

    db = client.app.dependency_overrides[get_session]()
    monkeypatch.setattr(database, "get_engine", lambda: db.get_bind())

    def collect(settings, progress):
        progress(45, "已检查 1/2：example/repo")
        if outcome == "error":
            raise ValueError("private-token")
        return outcome

    monkeypatch.setattr(collector, "collect", collect)
    task_id = "a" * 32
    db.add(CollectionTask(id=task_id, kind="github", updated_at=utcnow(), logs=[]))
    db.commit()
    users.run_collection("github", task_id)
    db.expire_all()
    task = db.get(CollectionTask, task_id)
    assert task.status == status
    assert any("已检查 1/2" in row["message"] for row in task.logs)
    assert "private-token" not in str(task.logs)
    if status != "failed":
        assert task.progress == 100
