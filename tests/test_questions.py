import pytest


async def make_admin(session, client, login="qadm", email="qadm@x.com"):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session, login=login, password="p", role="admin", email=email)
    return await get_auth_headers(client, login, "p")


QUESTION_PAYLOAD = {
    "text": "What is 2+2?",
    "options": ["1", "2", "4", "8"],
    "correct_option_index": 2,
}


@pytest.mark.asyncio
async def test_create_question(client, session):
    headers = await make_admin(session, client)
    resp = await client.post("/questions", json=QUESTION_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["text"] == "What is 2+2?"
    assert data["correct_option_index"] == 2


@pytest.mark.asyncio
async def test_invalid_correct_index(client, session):
    headers = await make_admin(session, client, "qadm2", "q2@x.com")
    payload = {**QUESTION_PAYLOAD, "correct_option_index": 10}
    resp = await client.post("/questions", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_question(client, session):
    headers = await make_admin(session, client, "qadm3", "q3@x.com")
    create_resp = await client.post("/questions", json=QUESTION_PAYLOAD, headers=headers)
    qid = create_resp.json()["id"]
    resp = await client.get(f"/questions/{qid}", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_question(client, session):
    headers = await make_admin(session, client, "qadm4", "q4@x.com")
    create_resp = await client.post("/questions", json=QUESTION_PAYLOAD, headers=headers)
    qid = create_resp.json()["id"]
    resp = await client.patch(f"/questions/{qid}", json={"text": "Updated?"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["text"] == "Updated?"


@pytest.mark.asyncio
async def test_delete_question(client, session):
    headers = await make_admin(session, client, "qadm5", "q5@x.com")
    create_resp = await client.post("/questions", json=QUESTION_PAYLOAD, headers=headers)
    qid = create_resp.json()["id"]
    resp = await client.delete(f"/questions/{qid}", headers=headers)
    assert resp.status_code == 204
