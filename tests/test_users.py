import pytest


async def create_admin(session, client):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(
        session, login="admin", password="adminpass",
        role="admin", email="admin@example.com",
    )
    headers = await get_auth_headers(client, "admin", "adminpass")
    return headers


@pytest.mark.asyncio
async def test_get_me(client, session):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session)
    headers = await get_auth_headers(client)
    resp = await client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["login"] == "testuser"


@pytest.mark.asyncio
async def test_list_users_requires_admin(client, session):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session)
    headers = await get_auth_headers(client)
    resp = await client.get("/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_admin(client, session):
    headers = await create_admin(session, client)
    resp = await client.get("/users", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_user_admin(client, session):
    headers = await create_admin(session, client)
    resp = await client.post("/users", json={
        "first_name": "New", "last_name": "Player",
        "email": "new@example.com", "login": "newplayer", "password": "pass123",
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["login"] == "newplayer"


@pytest.mark.asyncio
async def test_delete_user_admin(client, session):
    headers = await create_admin(session, client)
    from tests.conftest import create_test_user
    user = await create_test_user(session, login="todelete", email="del@example.com")
    resp = await client.delete(f"/users/{user.id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_patch_user_admin(client, session):
    headers = await create_admin(session, client)
    from tests.conftest import create_test_user
    user = await create_test_user(session, login="patchme", email="patch@example.com")
    resp = await client.patch(f"/users/{user.id}", json={"first_name": "Updated"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"
