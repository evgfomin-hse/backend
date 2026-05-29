import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.game import GameQuestion
    from app.models.team import Team
    from app.models.user import User


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("game_question_id", "team_id", name="unique_answer_gamequestions_team"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    game_question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("game_questions.id", ondelete="CASCADE")
    )
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("teams.id", ondelete="CASCADE"))
    player_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    chosen_option_index: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)

    game_question: Mapped["GameQuestion"] = relationship("GameQuestion", back_populates="answers")
    team: Mapped["Team"] = relationship("Team")
    player: Mapped["User"] = relationship("User")
