import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import pytest


async def full_game_setup(session, client):
    """Returns (admin_headers, player_headers, game_id, gq_id, team_id)"""
    from tests.conftest import create_test_user, get_auth_headers
    from app.models.team import Team
    from app.models.question import Question, QuestionOption

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
    q = Question(
        text="Q?",
        created_by=admin.id,
        choices=[
            QuestionOption(position=0, text="A", is_correct=True),
            QuestionOption(position=1, text="B", is_correct=False),
        ],
    )
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


async def test_submit_requires_player_role(client, session, fake_redis):
    admin_headers, _, game_id, gq_id, _ = await full_game_setup(session, client)
    resp = await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=admin_headers,
    )
    assert resp.status_code == 403


async def test_submit_player_without_team(client, session):
    import uuid
    from tests.conftest import create_test_user, get_auth_headers
    await create_test_user(
        session, login="noteam", password="p", role="player", email="noteam@x.com",
    )
    headers = await get_auth_headers(client, "noteam", "p")
    resp = await client.post(
        f"/games/{uuid.uuid4()}/questions/{uuid.uuid4()}/answer",
        json={"chosen_option_index": 0},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_submit_question_not_in_game(client, session, fake_redis):
    import uuid
    _, player_headers, game_id, _, _ = await full_game_setup(session, client)
    resp = await client.post(
        f"/games/{game_id}/questions/{uuid.uuid4()}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    assert resp.status_code == 404


async def test_submit_game_not_active(client, session, fake_redis):
    admin_headers, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    await client.post(f"/games/{game_id}/finish", headers=admin_headers)
    resp = await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    assert resp.status_code == 409


async def test_submit_question_not_asked(client, session, fake_redis):
    """Game is active but the question has not been pushed via next-question yet."""
    from sqlalchemy import select
    from app.models.game import GameQuestion
    from tests.conftest import create_test_user, get_auth_headers
    from app.models.team import Team
    from app.models.question import Question, QuestionOption

    admin = await create_test_user(
        session, login="naadm", password="p", role="admin", email="naadm@x.com"
    )
    team = Team(name="NotAskedTeam")
    session.add(team)
    await session.flush()
    await create_test_user(
        session, login="naplayer", password="p", role="player",
        email="naplayer@x.com", team_id=team.id,
    )
    q = Question(
        text="Q?", created_by=admin.id,
        choices=[
            QuestionOption(position=0, text="A", is_correct=True),
            QuestionOption(position=1, text="B", is_correct=False),
        ],
    )
    session.add(q)
    await session.flush()

    admin_headers = await get_auth_headers(client, "naadm", "p")
    player_headers = await get_auth_headers(client, "naplayer", "p")
    create_resp = await client.post("/games", json={
        "title": "NA", "team_ids": [str(team.id)], "question_ids": [str(q.id)],
    }, headers=admin_headers)
    game_id = create_resp.json()["id"]
    await client.post(f"/games/{game_id}/start", headers=admin_headers)

    gq = (await session.execute(select(GameQuestion))).scalars().first()
    resp = await client.post(
        f"/games/{game_id}/questions/{gq.id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    assert resp.status_code == 409


async def test_submit_answer_time_expired(client, session, fake_redis):
    from sqlalchemy import select
    from app.models.game import GameQuestion

    _, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    gq = (await session.execute(
        select(GameQuestion).where(GameQuestion.id == uuid.UUID(gq_id))
    )).scalar_one()
    gq.asked_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    await session.flush()

    resp = await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    assert resp.status_code == 409
