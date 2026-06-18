import uuid
import pytest


async def setup_admin_with_team_and_questions(session, client):
    """Returns (headers, team_id, question_ids)"""
    from tests.conftest import create_test_user, get_auth_headers
    from app.models.team import Team
    from app.models.question import Question, QuestionOption

    admin = await create_test_user(
        session, login="gadm", password="p", role="admin", email="gadm@x.com"
    )
    headers = await get_auth_headers(client, "gadm", "p")

    team = Team(name="Game Team")
    session.add(team)
    q1 = Question(
        text="Q1?",
        created_by=admin.id,
        choices=[
            QuestionOption(position=0, text="A", is_correct=True),
            QuestionOption(position=1, text="B", is_correct=False),
        ],
    )
    q2 = Question(
        text="Q2?",
        created_by=admin.id,
        choices=[
            QuestionOption(position=0, text="X", is_correct=False),
            QuestionOption(position=1, text="Y", is_correct=True),
        ],
    )
    session.add_all([q1, q2])
    await session.flush()

    return headers, str(team.id), [str(q1.id), str(q2.id)]


async def test_create_game(client, session):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    resp = await client.post("/games", json={
        "title": "Test Game",
        "team_ids": [team_id],
        "question_ids": question_ids,
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Game"
    assert data["status"] == "pending"


async def test_list_games(client, session):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    await client.post("/games", json={"title": "G1", "team_ids": [team_id], "question_ids": question_ids}, headers=headers)
    resp = await client.get("/games", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_start_game(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "StartGame", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]

    resp = await client.post(f"/games/{game_id}/start", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_next_question(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "NQ", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=headers)

    resp = await client.post(f"/games/{game_id}/next-question", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["round_number"] == 1
    assert data["asked_at"] is not None


async def test_finish_game(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "FG", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=headers)

    resp = await client.post(f"/games/{game_id}/finish", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"


async def test_start_game_twice_fails(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "Twice", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=headers)
    resp = await client.post(f"/games/{game_id}/start", headers=headers)
    assert resp.status_code == 409


async def test_get_game_not_found(client, session):
    headers, _, _ = await setup_admin_with_team_and_questions(session, client)
    resp = await client.get(f"/games/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_create_game_unknown_question(client, session):
    headers, team_id, _ = await setup_admin_with_team_and_questions(session, client)
    resp = await client.post("/games", json={
        "title": "Bad", "team_ids": [team_id], "question_ids": [str(uuid.uuid4())],
    }, headers=headers)
    assert resp.status_code == 404


async def test_create_game_unknown_team(client, session):
    headers, _, question_ids = await setup_admin_with_team_and_questions(session, client)
    resp = await client.post("/games", json={
        "title": "Bad", "team_ids": [str(uuid.uuid4())], "question_ids": question_ids,
    }, headers=headers)
    assert resp.status_code == 404


async def test_update_game(client, session):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "Old Title", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    resp = await client.patch(f"/games/{game_id}", json={"title": "New Title"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


async def test_update_game_not_pending(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "T", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=headers)
    resp = await client.patch(f"/games/{game_id}", json={"title": "Nope"}, headers=headers)
    assert resp.status_code == 409


async def test_delete_game(client, session):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "ToDelete", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    resp = await client.delete(f"/games/{game_id}", headers=headers)
    assert resp.status_code == 204


async def test_delete_game_not_pending(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "T", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=headers)
    resp = await client.delete(f"/games/{game_id}", headers=headers)
    assert resp.status_code == 409


async def test_next_question_not_active(client, session):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "T", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    resp = await client.post(f"/games/{game_id}/next-question", headers=headers)
    assert resp.status_code == 409


async def test_next_question_no_more(client, session, fake_redis):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "T", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=headers)
    for _ in question_ids:
        await client.post(f"/games/{game_id}/next-question", headers=headers)
    resp = await client.post(f"/games/{game_id}/next-question", headers=headers)
    assert resp.status_code == 409


async def test_finish_game_not_found(client, session):
    headers, _, _ = await setup_admin_with_team_and_questions(session, client)
    resp = await client.post(f"/games/{uuid.uuid4()}/finish", headers=headers)
    assert resp.status_code == 404


async def test_finish_game_not_active(client, session):
    headers, team_id, question_ids = await setup_admin_with_team_and_questions(session, client)
    create_resp = await client.post("/games", json={
        "title": "T", "team_ids": [team_id], "question_ids": question_ids,
    }, headers=headers)
    game_id = create_resp.json()["id"]
    resp = await client.post(f"/games/{game_id}/finish", headers=headers)
    assert resp.status_code == 409
