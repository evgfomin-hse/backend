from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question, QuestionOption
from app.models.user import User
from app.repositories.question import QuestionRepository
from app.schemas.question import QuestionCreate, QuestionUpdate


class QuestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = QuestionRepository(session)

    async def get_or_404(self, question_id: uuid.UUID) -> Question:
        q = await self.repo.get(question_id)
        if not q:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
        return q

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repo.list(skip=skip, limit=limit)

    @staticmethod
    def _build_choices(options: list[str], correct_index: int) -> list[QuestionOption]:
        return [
            QuestionOption(position=i, text=text, is_correct=(i == correct_index))
            for i, text in enumerate(options)
        ]

    async def create(self, body: QuestionCreate, creator: User) -> Question:
        q = Question(
            text=body.text,
            created_by=creator.id,
            choices=self._build_choices(body.options, body.correct_option_index),
        )
        return await self.repo.add(q)

    async def update(self, question_id: uuid.UUID, body: QuestionUpdate) -> Question:
        q = await self.get_or_404(question_id)
        updates = body.model_dump(exclude_none=True)

        if "text" in updates:
            q.text = updates["text"]

        if "options" in updates or "correct_option_index" in updates:
            new_options = updates.get("options", q.options)
            new_index = updates.get("correct_option_index", q.correct_option_index)
            if not (0 <= new_index < len(new_options)):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"correct_option_index out of range for {len(new_options)} options",
                )
            q.choices.clear()
            await self.repo.session.flush()
            q.choices = self._build_choices(new_options, new_index)

        await self.repo.session.flush()
        await self.repo.session.refresh(q)
        return q

    async def delete(self, question_id: uuid.UUID) -> None:
        q = await self.get_or_404(question_id)
        await self.repo.delete(q)
