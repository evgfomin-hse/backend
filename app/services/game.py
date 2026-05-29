import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.models.game import Game, GameQuestion, GameStatus, game_participants
from app.models.user import User
from app.repositories.game import GameRepository
from app.repositories.team import TeamRepository
from app.repositories.question import QuestionRepository
from app.schemas.game import GameCreate, GameUpdate


class GameService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self.repo = GameRepository(session)
        self.team_repo = TeamRepository(session)
        self.question_repo = QuestionRepository(session)
        self.session = session
        self.redis = redis

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repo.list(skip=skip, limit=limit)

    async def get_or_404(self, game_id: uuid.UUID) -> Game:
        game = await self.repo.get(game_id)
        if not game:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
        return game

    async def create(self, body: GameCreate, creator: User) -> Game:
        game = Game(
            title=body.title,
            scheduled_at=body.scheduled_at,
            created_by=creator.id,
        )
        self.session.add(game)
        await self.session.flush()

        for i, question_id in enumerate(body.question_ids, start=1):
            question = await self.question_repo.get(question_id)
            if not question:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Question {question_id} not found")
            game_question = GameQuestion(game_id=game.id, question_id=question_id, round_number=i)
            self.session.add(game_question)

        for team_id in body.team_ids:
            team = await self.team_repo.get(team_id)
            if not team:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Team {team_id} not found")
            await self.session.execute(
                game_participants.insert().values(game_id=game.id, team_id=team_id)
            )

        await self.session.flush()
        await self.session.refresh(game)
        return game

    async def update(self, game_id: uuid.UUID, body: GameUpdate) -> Game:
        game = await self.get_or_404(game_id)
        if game.status != GameStatus.pending:
            raise HTTPException(status.HTTP_409_CONFLICT, "Only pending games can be updated")
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(game, field, value)
        await self.session.flush()
        await self.session.refresh(game)
        return game

    async def delete(self, game_id: uuid.UUID) -> None:
        game = await self.get_or_404(game_id)
        if game.status != GameStatus.pending:
            raise HTTPException(status.HTTP_409_CONFLICT, "Only pending games can be deleted")
        await self.repo.delete(game)

    async def start(self, game_id: uuid.UUID) -> Game:
        game = await self.get_or_404(game_id)
        if game.status != GameStatus.pending:
            raise HTTPException(status.HTTP_409_CONFLICT, "Game is not pending")
        game.status = GameStatus.active
        game.started_at = datetime.now(timezone.utc)
        game.redis_channel = f"game:{game.id}"
        await self.session.flush()
        await self.redis.publish(game.redis_channel, json.dumps({"type": "game_started"}))
        await self.session.refresh(game)
        return game

    async def next_question(self, game_id: uuid.UUID) -> GameQuestion:
        game = await self.get_or_404(game_id)
        if game.status != GameStatus.active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Game is not active")
        gq = await self.repo.get_next_unasked_question(game_id)
        if not gq:
            raise HTTPException(status.HTTP_409_CONFLICT, "No more questions")
        gq.asked_at = datetime.now(timezone.utc)
        await self.session.flush()
        payload = {
            "type": "question",
            "round": gq.round_number,
            "game_question_id": str(gq.id),
            "question": {
                "id": str(gq.question.id),
                "text": gq.question.text,
                "options": gq.question.options,
            },
            "asked_at": gq.asked_at.isoformat(),
        }
        if game.redis_channel:
            await self.redis.publish(game.redis_channel, json.dumps(payload))
        await self.session.refresh(gq)
        return gq

    async def finish(self, game_id: uuid.UUID) -> Game:
        game = await self.repo.get_with_questions(game_id)
        if not game:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
        if game.status != GameStatus.active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Game is not active")
        game.status = GameStatus.finished
        game.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        for team in game.teams:
            team.games_played += 1
        await self.session.flush()
        if game.redis_channel:
            await self.redis.publish(game.redis_channel, json.dumps({"type": "game_over"}))
        await self.session.refresh(game)
        return game
