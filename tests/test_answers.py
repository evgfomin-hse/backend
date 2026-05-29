import asyncio
from datetime import datetime, timezone, timedelta
import pytest


async def full_game_setup(session, client):
    """Returns (admin_headers, player_headers, game_id, gq_id, team_id)"""
    from tests.conftest import create_test_user, get_auth_headers
    from app.models.team import Team
    from app.models.question import Question

    admin = await create_test_user(
        session, login="aadm", password="p", role="admin", email="aadm@x.com"
    )
    team = Team(name="AnswerTeam")
    session.add(team)
    await session.flush()

    player = await create_test_user(
        session, login="aplayer", password="p", role="player",
        email="aplayer@x.com", team_id=team.id,
    )
    q = Question(text="Q?", options=["A", "B"], correct_option_index=0, created_by=admin.id)
    session.add(q)
    await session.flush()

    admin_headers = await get_auth_headers(client, "aadm", "p")
    player_headers = await get_auth_headers(client, "aplayer", "p")

    create_resp = await client.post("/games", json={
        "title": "AnswerGame",
        "team_ids": [str(team.id)],
        "question_ids": [str(q.id)],
    }, headers=admin_headers)
    game_id = create_resp.json()["id"]

    await client.post(f"/games/{game_id}/start", headers=admin_headers)
    nq_resp = await client.post(f"/games/{game_id}/next-question", headers=admin_headers)
    gq_id = nq_resp.json()["id"]

    return admin_headers, player_headers, game_id, gq_id, str(team.id)


async def test_submit_correct_answer(client, session, fake_redis):
    _, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    resp = await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_correct"] is True
    assert data["points_awarded"] == 1


async def test_submit_wrong_answer(client, session, fake_redis):
    _, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    resp = await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 1},
        headers=player_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_correct"] is False
    assert data["points_awarded"] == 0


async def test_duplicate_answer_rejected(client, session, fake_redis):
    _, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    resp = await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    assert resp.status_code == 409
