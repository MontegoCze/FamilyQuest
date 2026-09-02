import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def override_db():
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def auth(client: TestClient, email: str, name: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": name},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_completion_requires_assignment_and_awards_xp(client: TestClient):
    parent_headers = auth(client, "parent@example.com", "Parent")
    assert client.post("/api/v1/family", headers=parent_headers, json={"name": "Home"}).status_code == 201
    child = client.post(
        "/api/v1/family/children",
        headers=parent_headers,
        json={"full_name": "Child", "password": "password123"},
    ).json()
    task = client.post(
        "/api/v1/tasks",
        headers=parent_headers,
        json={"title": "Tidy", "xp": 25, "assignee_ids": [child["id"]]},
    ).json()
    child_headers = auth(client, child["email"], child["full_name"])
    completion = client.post(f"/api/v1/tasks/{task['id']}/complete", headers=child_headers, json={})
    assert completion.status_code == 201
    assert client.post(
        f"/api/v1/completions/{completion.json()['id']}/review",
        headers=parent_headers,
        json={"status": "approved"},
    ).status_code == 200
    assert client.get("/api/v1/stats", headers=child_headers).json()["total_xp"] == 25


def test_child_cannot_manage_tasks_or_view_other_stats(client: TestClient):
    parent_headers = auth(client, "p2@example.com", "Parent")
    client.post("/api/v1/family", headers=parent_headers, json={"name": "Home"})
    child = client.post(
        "/api/v1/family/children",
        headers=parent_headers,
        json={"full_name": "Child", "password": "password123"},
    ).json()
    child_headers = auth(client, child["email"], child["full_name"])
    assert client.post("/api/v1/tasks", headers=child_headers, json={"title": "Nope"}).status_code == 403
    parent_id = client.get("/api/v1/auth/me", headers=parent_headers).json()["id"]
    assert client.get(f"/api/v1/users/{parent_id}/stats", headers=child_headers).status_code == 403


def test_adventure_points_are_family_scoped_and_read_only_for_children(client: TestClient):
    parent_headers = auth(client, "adventure-parent@example.com", "Parent")
    assert client.post("/api/v1/family", headers=parent_headers, json={"name": "Adventure Home"}).status_code == 201
    child = client.post(
        "/api/v1/family/children",
        headers=parent_headers,
        json={"full_name": "Explorer", "password": "password123"},
    ).json()
    first = client.post(
        "/api/v1/adventure/points",
        headers=parent_headers,
        json={"name": "Start", "icon": "🏠", "required_xp": 0, "position_x": 20, "position_y": 80},
    )
    assert first.status_code == 201
    assert first.json()["name"] == "Start"
    second = client.post(
        "/api/v1/adventure/points",
        headers=parent_headers,
        json={"title": "Les", "required_xp": 500, "position_x": 70, "position_y": 30},
    )
    assert second.status_code == 201
    child_headers = auth(client, child["email"], child["full_name"])
    points = client.get("/api/v1/adventure", headers=child_headers)
    assert points.status_code == 200
    assert [(item["title"], item["status"]) for item in points.json()] == [
        ("Start", "completed"),
        ("Les", "current"),
    ]
    assert client.post("/api/v1/adventure/points", headers=child_headers, json={"title": "Nope"}).status_code == 403


def test_parent_can_manage_family_accounts_without_deleting_history(client: TestClient):
    parent_headers = auth(client, "accounts-parent@example.com", "Parent")
    assert client.post("/api/v1/family", headers=parent_headers, json={"name": "Accounts"}).status_code == 201
    child = client.post(
        "/api/v1/family/accounts",
        headers=parent_headers,
        json={"role": "child", "full_name": "Kid", "password": "password123"},
    ).json()
    assert client.get(f"/api/v1/family/accounts/{child['user_id']}/preview", headers=parent_headers).status_code == 200
    assert client.patch(
        f"/api/v1/family/accounts/{child['user_id']}",
        headers=parent_headers,
        json={"full_name": "Updated Kid", "avatar": "🐉"},
    ).status_code == 200
    assert client.post(
        f"/api/v1/family/accounts/{child['user_id']}/reset-password",
        headers=parent_headers,
        json={"password": "newpassword123"},
    ).status_code == 204
    assert client.patch(
        f"/api/v1/family/accounts/{child['user_id']}/status",
        headers=parent_headers,
        json={"is_active": False},
    ).status_code == 200
    accounts = client.get("/api/v1/family/accounts", headers=parent_headers).json()
    assert any(account["user_id"] == child["user_id"] and not account["is_active"] for account in accounts)
    assert client.patch(
        f"/api/v1/family/accounts/{child['user_id']}/status",
        headers=parent_headers,
        json={"is_active": True},
    ).status_code == 200
