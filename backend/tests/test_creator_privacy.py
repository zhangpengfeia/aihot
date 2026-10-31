"""登录要求、跨用户读写隔离和首页个性化配置。"""

from types import SimpleNamespace

from test_workspace import context  # noqa: F401

from app.core.auth import current_user
from app.main import app


def test_private_workspace_and_dashboard(context):  # noqa: F811
    client, _, _ = context
    app.dependency_overrides[current_user] = lambda: None
    for path in (
        "/api/workspace/items",
        "/api/workspace/items/topic/1",
        "/api/workspace/cards",
        "/api/workspace/dashboard-preferences",
    ):
        assert client.get(path).status_code == 401
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        id=999, role="user", enabled=True
    )
    assert (
        client.put(
            "/api/workspace/items/topic/1", json={"favorite": True, "note": "private 999"}
        ).status_code
        == 200
    )
    card = client.post("/api/workspace/cards", json={"topic_id": 1}).json()
    client.patch(f"/api/workspace/cards/{card['id']}", json={"script": "private script"})
    assert (
        client.put(
            "/api/workspace/dashboard-preferences", json={"cards": ["favorites", "knowledge"]}
        ).status_code
        == 200
    )
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        id=1000, role="admin", enabled=True
    )
    assert client.get("/api/workspace/items").json()["total"] == 0
    assert client.get("/api/workspace/items/topic/1").json()["note"] == ""
    assert client.get("/api/workspace/cards").json()["items"] == []
    assert (
        client.patch(f"/api/workspace/cards/{card['id']}", json={"script": "attack"}).status_code
        == 404
    )
    client.delete(f"/api/workspace/cards/{card['id']}")
    client.delete("/api/workspace/items/topic/1")
    assert client.get("/api/workspace/dashboard-preferences").json()["cards"] == [
        "projects",
        "knowledge",
        "hotlists",
    ]
    assert client.post("/api/workspace/cards", json={"topic_id": 1}).json()["id"] != card["id"]
    assert client.put("/api/workspace/items/topic/1", json={"favorite": True}).status_code == 200
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        id=999, role="user", enabled=True
    )
    assert client.get("/api/workspace/items").json()["items"][0]["note"] == "private 999"
    assert client.get("/api/workspace/cards").json()["items"][0]["script"] == "private script"
    assert client.get("/api/workspace/dashboard-preferences").json()["cards"] == [
        "favorites",
        "knowledge",
    ]
    assert (
        client.put("/api/workspace/dashboard-preferences", json={"cards": ["unknown"]}).status_code
        == 422
    )


def test_dashboard_preserves_individual_card_order(context):  # noqa: F811
    client, _, _ = context
    cards = ["hotlists", "growth", "risers", "overview", "knowledge", "new_entries", "favorites"]
    assert (
        client.put("/api/workspace/dashboard-preferences", json={"cards": cards}).json()["cards"]
        == cards
    )
    assert client.get("/api/workspace/dashboard-preferences").json()["cards"] == cards
    assert (
        client.put("/api/workspace/dashboard-preferences", json={"cards": []}).json()["cards"] == []
    )
    assert client.get("/api/workspace/dashboard-preferences").json()["cards"] == []


def test_dashboard_widths_legacy_and_account_isolation(context):  # noqa: F811
    from app.models.users import DashboardPreference

    client, db, _ = context
    db.add(DashboardPreference(user_id=999, cards=["knowledge", "projects"]))
    db.commit()
    old = client.get("/api/workspace/dashboard-preferences").json()
    assert old["cards"] == ["knowledge", "projects"]
    assert old["widths"]["new_entries"] == "half"
    saved = client.put(
        "/api/workspace/dashboard-preferences",
        json={"cards": ["knowledge", "growth"], "widths": {"knowledge": "half", "growth": "half"}},
    )
    assert saved.status_code == 200
    assert saved.json()["widths"]["knowledge"] == "half"
    client.put("/api/workspace/dashboard-preferences", json={"cards": ["growth", "knowledge"]})
    assert (
        client.get("/api/workspace/dashboard-preferences").json()["widths"]["knowledge"] == "half"
    )
    assert (
        client.put(
            "/api/workspace/dashboard-preferences",
            json={"cards": [], "widths": {"growth": "quarter"}},
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/workspace/dashboard-preferences",
            json={"cards": [], "widths": {"unknown": "half"}},
        ).status_code
        == 422
    )
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        id=1000, role="user", enabled=True
    )
    assert (
        client.get("/api/workspace/dashboard-preferences").json()["widths"]["knowledge"] == "full"
    )
