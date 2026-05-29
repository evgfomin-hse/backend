import pytest


async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "first_name": "Alice", "last_name": "Smith",
        "email": "alice@example.com", "login": "alice", "password": "secret123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["login"] == "alice"
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_duplicate_login(client):
    payload = {"first_name": "A", "last_name": "B", "email": "a@b.com", "login": "dup", "password": "x"}
    await client.post("/auth/register", json=payload)
    payload2 = {**payload, "email": "c@d.com"}
    resp = await client.post("/auth/register", json=payload2)
    assert resp.status_code == 409


async def test_login_success(client, session):
    from tests.conftest import create_test_user
    await create_test_user(session, login="bob", password="pass123", email="bob@example.com")

    resp = await client.post("/auth/login", json={"login": "bob", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client, session):
    from tests.conftest import create_test_user
    await create_test_user(session, login="carol", password="correct", email="carol@example.com")
    resp = await client.post("/auth/login", json={"login": "carol", "password": "wrong"})
    assert resp.status_code == 401


async def test_refresh_token(client, session):
    from tests.conftest import create_test_user
    await create_test_user(session, login="dave", password="pass", email="dave@example.com")
    login_resp = await client.post("/auth/login", json={"login": "dave", "password": "pass"})
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_change_password(client, session):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session, login="eve", password="oldpass", email="eve@example.com")
    headers = await get_auth_headers(client, "eve", "oldpass")

    resp = await client.post(
        "/auth/change-password",
        json={"old_password": "oldpass", "new_password": "newpass"},
        headers=headers,
    )
    assert resp.status_code == 204

    resp = await client.post("/auth/login", json={"login": "eve", "password": "newpass"})
    assert resp.status_code == 200
