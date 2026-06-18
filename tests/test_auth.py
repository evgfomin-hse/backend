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


async def test_register_duplicate_email(client):
    payload = {
        "first_name": "A", "last_name": "B",
        "email": "same@b.com", "login": "first", "password": "x",
    }
    await client.post("/auth/register", json=payload)
    payload2 = {**payload, "login": "second"}
    resp = await client.post("/auth/register", json=payload2)
    assert resp.status_code == 409


async def test_refresh_invalid_token(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


async def test_refresh_expired_token(client, session):
    from datetime import datetime, timedelta, timezone
    from tests.conftest import create_test_user
    from app.core.security import hash_refresh_token
    from app.repositories.token import TokenRepository

    await create_test_user(session, login="frank", password="pass", email="frank@example.com")
    login_resp = await client.post("/auth/login", json={"login": "frank", "password": "pass"})
    raw = login_resp.json()["refresh_token"]

    token = await TokenRepository(session).get_by_hash(hash_refresh_token(raw))
    token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await session.flush()

    resp = await client.post("/auth/refresh", json={"refresh_token": raw})
    assert resp.status_code == 401


async def test_change_password_wrong_current(client, session):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session, login="grace", password="rightpass", email="grace@example.com")
    headers = await get_auth_headers(client, "grace", "rightpass")

    resp = await client.post(
        "/auth/change-password",
        json={"old_password": "wrongpass", "new_password": "newpass"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_protected_route_invalid_token(client, session):
    from tests.conftest import create_test_user
    await create_test_user(session)
    resp = await client.get("/users/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


async def test_protected_route_unknown_user(client, session):
    import uuid
    from app.core.security import create_access_token
    token = create_access_token(uuid.uuid4(), "player")
    resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
