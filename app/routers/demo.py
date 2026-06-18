"""Demo dashboard endpoints.

Serves a single page with four panels (User 1, User 2, Admin, Logs) that
drive the real Quiz API and stream every backend operation (HTTP / DB / Redis)
to the Logs panel, tagged with the actor that triggered it.

This router is purely additive — it only exists to demonstrate the backend.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event, subscribe
from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.models.answer import Answer
from app.models.game import Game, GameQuestion, game_participants
from app.models.question import Question, QuestionOption
from app.models.team import Team
from app.models.token import RefreshToken
from app.models.user import User, UserRole
from app.services.stats import StatsService

router = APIRouter(prefix="/demo", tags=["demo"])

_PAGE = Path(__file__).resolve().parent.parent / "static" / "demo.html"


@router.get("")
async def demo_page() -> FileResponse:
    return FileResponse(_PAGE, media_type="text/html")


@router.get("/logs")
async def demo_logs() -> StreamingResponse:
    """Server-Sent Events stream of all audit events."""

    async def stream():
        # Greeting event so the panel shows it is connected immediately.
        yield f"data: {json.dumps({'ts': '', 'actor': 'system', 'category': 'demo', 'action': 'log stream connected', 'detail': ''})}\n\n"
        async for event in subscribe():
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/standings")
async def demo_standings(session: AsyncSession = Depends(get_db)):
    """Live team + player standings for the demo dashboard table."""
    stats = StatsService(session)
    teams = await stats.top_teams("all", limit=10)
    players = await stats.top_players("all", limit=10)
    return {
        "teams": [t.model_dump(mode="json") for t in teams],
        "players": [p.model_dump(mode="json") for p in players],
    }


_DEMO_QUESTIONS = [
    ("What is the capital of France?", ["Berlin", "Paris", "Madrid", "Rome"], 1),
    ("2 + 2 * 2 = ?", ["6", "8", "4", "2"], 0),
    ("Which planet is the Red Planet?", ["Venus", "Jupiter", "Mars", "Saturn"], 2),
]


@router.post("/reset")
async def demo_reset(session: AsyncSession = Depends(get_db)):
    """Wipe demo data and recreate admin + two players + two teams + questions.

    Returns access tokens and ids the frontend needs to drive the API.
    """
    log_event("demo", "RESET requested", "rebuilding demo data")

    # Delete in FK-safe order.
    await session.execute(delete(Answer))
    await session.execute(delete(GameQuestion))
    await session.execute(delete(game_participants))
    await session.execute(delete(Game))
    await session.execute(delete(RefreshToken))
    await session.execute(delete(Question))
    await session.execute(delete(User))
    await session.execute(delete(Team))
    await session.flush()

    team_red = Team(name="Team Red")
    team_blue = Team(name="Team Blue")
    session.add_all([team_red, team_blue])
    await session.flush()

    admin = User(
        first_name="Ada", last_name="Admin", email="admin@demo.local",
        login="admin", hashed_password=hash_password("admin123"), role=UserRole.admin,
    )
    user1 = User(
        first_name="Uma", last_name="One", email="user1@demo.local",
        login="user1", hashed_password=hash_password("user123"),
        role=UserRole.player, team_id=team_red.id,
    )
    user2 = User(
        first_name="Theo", last_name="Two", email="user2@demo.local",
        login="user2", hashed_password=hash_password("user123"),
        role=UserRole.player, team_id=team_blue.id,
    )
    session.add_all([admin, user1, user2])
    await session.flush()

    questions = [
        Question(
            text=t,
            created_by=admin.id,
            choices=[
                QuestionOption(position=pos, text=opt, is_correct=(pos == i))
                for pos, opt in enumerate(o)
            ],
        )
        for t, o, i in _DEMO_QUESTIONS
    ]
    session.add_all(questions)
    await session.flush()

    return {
        "tokens": {
            "admin": create_access_token(admin.id, admin.role.value),
            "user1": create_access_token(user1.id, user1.role.value),
            "user2": create_access_token(user2.id, user2.role.value),
        },
        "users": {
            "admin": str(admin.id),
            "user1": {"id": str(user1.id), "team_id": str(team_red.id), "team": "Team Red"},
            "user2": {"id": str(user2.id), "team_id": str(team_blue.id), "team": "Team Blue"},
        },
        "team_ids": [str(team_red.id), str(team_blue.id)],
        "question_ids": [str(q.id) for q in questions],
    }
