import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
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

    async def create(self, body: QuestionCreate, creator: User) -> Question:
        q = Question(
            text=body.text,
            options=body.options,
            correct_option_index=body.correct_option_index,
            created_by=creator.id,
        )
        return await self.repo.add(q)

    async def update(self, question_id: uuid.UUID, body: QuestionUpdate) -> Question:
        q = await self.get_or_404(question_id)
        updates = body.model_dump(exclude_none=True)
        new_options = updates.get("options", q.options)
        new_index = updates.get("correct_option_index", q.correct_option_index)
        if not (0 <= new_index < len(new_options)):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"correct_option_index out of range for {len(new_options)} options",
            )
        for field, value in updates.items():
            setattr(q, field, value)
        await self.repo.session.flush()
        await self.repo.session.refresh(q)
        return q

    async def delete(self, question_id: uuid.UUID) -> None:
        q = await self.get_or_404(question_id)
        await self.repo.delete(q)
