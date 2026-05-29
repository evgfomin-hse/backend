import uuid
from datetime import datetime

from pydantic import BaseModel


class AnswerCreate(BaseModel):
    chosen_option_index: int


class AnswerResponse(BaseModel):
    id: uuid.UUID
    game_question_id: uuid.UUID
    team_id: uuid.UUID
    player_id: uuid.UUID
    chosen_option_index: int
    is_correct: bool
    answered_at: datetime
    points_awarded: int

    model_config = {"from_attributes": True}
