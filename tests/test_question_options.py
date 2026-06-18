import uuid

from sqlalchemy import select


async def make_admin(session, client, login="qoadm", email="qoadm@x.com"):
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(session, login=login, password="p", role="admin", email=email)
    return await get_auth_headers(client, login, "p")


PAYLOAD = {
    "text": "What is 2+2?",
    "options": ["1", "2", "4", "8"],
    "correct_option_index": 2,
}


async def test_options_are_stored_as_normalized_rows(client, session):
    """The JSON options array must be persisted as one row per option."""
    from app.models.question import QuestionOption

    headers = await make_admin(session, client)
    resp = await client.post("/questions", json=PAYLOAD, headers=headers)
    assert resp.status_code == 201
    qid = uuid.UUID(resp.json()["id"])

    rows = (
        await session.execute(
            select(QuestionOption)
            .where(QuestionOption.question_id == qid)
            .order_by(QuestionOption.position)
        )
    ).scalars().all()

    assert [r.position for r in rows] == [0, 1, 2, 3]
    assert [r.text for r in rows] == ["1", "2", "4", "8"]
    assert [r.is_correct for r in rows] == [False, False, True, False]


async def test_response_reconstructs_options_and_index(client, session):
    """The public API contract (options list + correct index) is preserved."""
    headers = await make_admin(session, client, "qoadm2", "qoadm2@x.com")
    resp = await client.post("/questions", json=PAYLOAD, headers=headers)
    data = resp.json()
    assert data["options"] == ["1", "2", "4", "8"]
    assert data["correct_option_index"] == 2


async def test_update_options_rebuilds_rows(client, session):
    """Updating options replaces the option rows, not appends."""
    from app.models.question import QuestionOption

    headers = await make_admin(session, client, "qoadm3", "qoadm3@x.com")
    qid = (await client.post("/questions", json=PAYLOAD, headers=headers)).json()["id"]

    resp = await client.patch(
        f"/questions/{qid}",
        json={"options": ["yes", "no"], "correct_option_index": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["options"] == ["yes", "no"]
    assert resp.json()["correct_option_index"] == 1

    rows = (
        await session.execute(
            select(QuestionOption)
            .where(QuestionOption.question_id == uuid.UUID(qid))
            .order_by(QuestionOption.position)
        )
    ).scalars().all()
    assert [r.text for r in rows] == ["yes", "no"]
    assert [r.is_correct for r in rows] == [False, True]
