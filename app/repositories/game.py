import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.game import Game, GameQuestion, GameStatus
from app.repositories.base import BaseRepository


class GameRepository(BaseRepository[Game]):
    model = Game

    async def get_with_questions(self, game_id: uuid.UUID) -> Game | None:
        result = await self.session.execute(
            select(Game)
            .options(
                selectinload(Game.game_questions).selectinload(GameQuestion.question),
                selectinload(Game.teams),
            )
            .where(Game.id == game_id)
        )
        return result.scalar_one_or_none()

    async def get_next_unasked_question(self, game_id: uuid.UUID) -> GameQuestion | None:
        result = await self.session.execute(
            select(GameQuestion)
            .options(selectinload(GameQuestion.question))
            .where(
                GameQuestion.game_id == game_id,
                GameQuestion.asked_at.is_(None),
            )
            .order_by(GameQuestion.round_number, GameQuestion.id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_game_question(self, gq_id: uuid.UUID) -> GameQuestion | None:
        result = await self.session.execute(
            select(GameQuestion)
            .options(selectinload(GameQuestion.question))
            .where(GameQuestion.id == gq_id)
        )
        return result.scalar_one_or_none()
