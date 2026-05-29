import pytest


async def make_admin(session, client, login="tadm", email="tadm@x.com"):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session, login=login, password="p", role="admin", email=email)
    return await get_auth_headers(client, login, "p")


@pytest.mark.asyncio
async def test_create_team(client, session):
    headers = await make_admin(session, client)
    resp = await client.post("/teams", json={"name": "Red Team"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Red Team"


@pytest.mark.asyncio
async def test_list_teams(client, session):
    headers = await make_admin(session, client, "tadm2", "t2@x.com")
    await client.post("/teams", json={"name": "Team A"}, headers=headers)
    resp = await client.get("/teams", headers=headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "Team A" in names


@pytest.mark.asyncio
async def test_update_team(client, session):
    headers = await make_admin(session, client, "tadm3", "t3@x.com")
    create_resp = await client.post("/teams", json={"name": "OldName"}, headers=headers)
    team_id = create_resp.json()["id"]
    resp = await client.patch(f"/teams/{team_id}", json={"name": "NewName"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewName"


@pytest.mark.asyncio
async def test_delete_team(client, session):
    headers = await make_admin(session, client, "tadm4", "t4@x.com")
    create_resp = await client.post("/teams", json={"name": "ToDelete"}, headers=headers)
    team_id = create_resp.json()["id"]
    resp = await client.delete(f"/teams/{team_id}", headers=headers)
    assert resp.status_code == 204
