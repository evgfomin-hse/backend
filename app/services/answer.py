import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.game import GameStatus
from app.models.user import User
from app.repositories.answer import AnswerRepository
from app.repositories.game import GameRepository
from app.schemas.answer import AnswerCreate

ANSWER_WINDOW_SECONDS = 30


class AnswerService:
    def __init__(self, session: AsyncSession) -> None:
        self.answer_repo = AnswerRepository(session)
        self.game_repo = GameRepository(session)
        self.session = session

    async def submit(
        self,
        game_id: uuid.UUID,
        gq_id: uuid.UUID,
        body: AnswerCreate,
        player: User,
    ) -> Answer:
        if player.team_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Player has no team")

        gq = await self.game_repo.get_game_question(gq_id)
        if not gq or gq.game_id != game_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found in this game")

        game = await self.game_repo.get(game_id)
        if game.status != GameStatus.active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Game is not active")

        if gq.asked_at is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Question has not been asked yet")

        now = datetime.now(timezone.utc)
        asked_at = gq.asked_at
        if asked_at.tzinfo is None:
            asked_at = asked_at.replace(tzinfo=timezone.utc)
        if (now - asked_at) > timedelta(seconds=ANSWER_WINDOW_SECONDS):
            raise HTTPException(status.HTTP_409_CONFLICT, "Answer time expired (30s limit)")

        existing = await self.answer_repo.get_team_answer_for_game_question(gq_id, player.team_id)
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Team already answered this question")

        is_correct = body.chosen_option_index == gq.question.correct_option_index
        points = 1 if is_correct else 0

        answer = Answer(
            game_question_id=gq_id,
            team_id=player.team_id,
            player_id=player.id,
            chosen_option_index=body.chosen_option_index,
            is_correct=is_correct,
            points_awarded=points,
        )
        answer = await self.answer_repo.add(answer)

        if is_correct:
            from app.repositories.team import TeamRepository
            team_repo = TeamRepository(self.session)
            team = await team_repo.get(player.team_id)
            team.score += points
            await self.session.flush()

        return answer
