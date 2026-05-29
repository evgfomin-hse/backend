import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class QuestionCreate(BaseModel):
    text: str
    options: list[str]
    correct_option_index: int

    @field_validator("options")
    @classmethod
    def at_least_two_options(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("At least 2 options required")
        return v

    @model_validator(mode="after")
    def index_in_range(self) -> "QuestionCreate":
        if not (0 <= self.correct_option_index < len(self.options)):
            raise ValueError(
                f"correct_option_index must be 0..{len(self.options) - 1}"
            )
        return self


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    options: Optional[list[str]] = None
    correct_option_index: Optional[int] = None


class QuestionResponse(BaseModel):
    id: uuid.UUID
    text: str
    options: list[str]
    correct_option_index: int
    created_by: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionPublic(BaseModel):
    """Sent to players during game — no correct answer."""
    id: uuid.UUID
    text: str
    options: list[str]
