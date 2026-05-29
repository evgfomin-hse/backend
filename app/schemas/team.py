import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    score: int
    games_played: int
    games_won: int
    games_lost: int
    created_at: datetime

    model_config = {"from_attributes": True}
