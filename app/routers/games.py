import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.dependencies import get_current_user, get_db, require_admin, require_player
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.answer import AnswerCreate, AnswerResponse
from app.schemas.game import GameCreate, GameQuestionResponse, GameResponse, GameUpdate
from app.services.answer import AnswerService
from app.services.game import GameService

router = APIRouter(prefix="/games", tags=["games"])


def _service(session: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)) -> GameService:
    return GameService(session, redis)


@router.get("", response_model=list[GameResponse])
async def list_games(skip: int = 0, limit: int = 100, svc: GameService = Depends(_service)):
    return await svc.list(skip=skip, limit=limit)


@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    body: GameCreate,
    admin: User = Depends(require_admin),
    svc: GameService = Depends(_service),
):
    return await svc.create(body, admin)


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(game_id: uuid.UUID, svc: GameService = Depends(_service)):
    return await svc.get_or_404(game_id)


@router.patch("/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: uuid.UUID,
    body: GameUpdate,
    _admin: User = Depends(require_admin),
    svc: GameService = Depends(_service),
):
    return await svc.update(game_id, body)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    svc: GameService = Depends(_service),
):
    await svc.delete(game_id)


@router.post("/{game_id}/start", response_model=GameResponse)
async def start_game(
    game_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    svc: GameService = Depends(_service),
):
    return await svc.start(game_id)


@router.post("/{game_id}/next-question", response_model=GameQuestionResponse)
async def next_question(
    game_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    svc: GameService = Depends(_service),
):
    return await svc.next_question(game_id)


@router.post("/{game_id}/finish", response_model=GameResponse)
async def finish_game(
    game_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    svc: GameService = Depends(_service),
):
    return await svc.finish(game_id)


@router.post(
    "/{game_id}/questions/{gq_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer(
    game_id: uuid.UUID,
    gq_id: uuid.UUID,
    body: AnswerCreate,
    player: User = Depends(require_player),
    session: AsyncSession = Depends(get_db),
):
    return await AnswerService(session).submit(game_id, gq_id, body, player)
