import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.question import Question
    from app.models.answer import Answer


class GameStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    finished = "finished"


game_participants = Table(
    "game_participants",
    Base.metadata,
    Column("game_id", Uuid, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", Uuid, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[GameStatus] = mapped_column(
        SAEnum(GameStatus, native_enum=False), default=GameStatus.pending
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    redis_channel: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)

    teams: Mapped[list["Team"]] = relationship(
        "Team", secondary=game_participants, back_populates="games"
    )
    game_questions: Mapped[list["GameQuestion"]] = relationship(
        "GameQuestion", back_populates="game",
        cascade="all, delete-orphan",
        order_by="GameQuestion.round_number"
    )


class GameQuestion(Base):
    __tablename__ = "game_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("games.id", ondelete="CASCADE"))
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("questions.id", ondelete="RESTRICT")
    )
    round_number: Mapped[int] = mapped_column(Integer)
    asked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    game: Mapped["Game"] = relationship("Game", back_populates="game_questions")
    question: Mapped["Question"] = relationship("Question")
    answers: Mapped[list["Answer"]] = relationship(
        "Answer", back_populates="game_question",
        cascade="all, delete-orphan"
    )
