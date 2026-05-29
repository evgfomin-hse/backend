import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.game import GameStatus


class GameCreate(BaseModel):
    title: str
    scheduled_at: Optional[datetime] = None
    team_ids: list[uuid.UUID]
    question_ids: list[uuid.UUID]


class GameUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class GameResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: GameStatus
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    redis_channel: Optional[str]

    model_config = {"from_attributes": True}


class GameQuestionResponse(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    question_id: uuid.UUID
    round_number: int
    asked_at: Optional[datetime]

    model_config = {"from_attributes": True}
