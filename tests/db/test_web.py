import pytest
from django.test import Client

from hw_radar.accounts.models import User

PASSWORD = "a-strong-password-123!"


@pytest.fixture
def owner(db: None) -> User:
    return User.objects.create_user(username="owner", password=PASSWORD)


def test_healthz_ok(client: Client, db: None) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["version"]


def test_dashboard_requires_login(client: Client, db: None) -> None:
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/accounts/login/")


def test_login_then_dashboard(client: Client, owner: User) -> None:
    assert client.login(username="owner", password=PASSWORD)
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hardware Radar" in response.content


def test_wrong_password_rejected(client: Client, owner: User) -> None:
    assert not client.login(username="owner", password="wrong-password-000!")


def test_login_page_renders(client: Client, db: None) -> None:
    assert client.get("/accounts/login/").status_code == 200
