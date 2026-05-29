import uuid

from pydantic import BaseModel


class PlayerStats(BaseModel):
    player_id: uuid.UUID
    first_name: str
    last_name: str
    total_points: int
    correct_answers: int


class TeamStats(BaseModel):
    team_id: uuid.UUID
    name: str
    total_points: int
    games_played: int
    games_won: int
