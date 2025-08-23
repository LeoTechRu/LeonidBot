import types
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.models import User, UserRole
from web.routes import profile


class FakeService:
    def __init__(self):
        self.users = {
            1: User(telegram_id=1, first_name="Alice", username="alice", role=UserRole.single.value),
            2: User(telegram_id=2, first_name="Bob", username="bob", role=UserRole.moderator.value),
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get_user_by_telegram_id(self, telegram_id: int):
        return self.users.get(telegram_id)


app = FastAPI()
# Patch UserService in profile module
profile.UserService = FakeService
app.include_router(profile.router)
client = TestClient(app)


def auth_header(user_id: int):
    return {"Authorization": f"Bearer {user_id}"}


def test_user_can_view_own_profile():
    res = client.get("/profile/1", headers=auth_header(1))
    assert res.status_code == 200
    assert "Alice" in res.text


def test_single_user_cannot_view_others():
    res = client.get("/profile/2", headers=auth_header(1))
    assert res.status_code == 403


def test_higher_role_can_view_others():
    res = client.get("/profile/1", headers=auth_header(2))
    assert res.status_code == 200
    assert "Alice" in res.text


def test_single_user_can_update_self():
    res = client.post("/profile/1", headers=auth_header(1), json={"username": "alice_new"})
    assert res.status_code == 200
    assert "alice_new" in res.text


def test_single_user_cannot_update_others():
    res = client.post("/profile/2", headers=auth_header(1), json={"username": "bad"})
    assert res.status_code == 403

