import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.question import QuestionCreate, QuestionResponse, QuestionUpdate
from app.services.question import QuestionService

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    skip: int = 0, limit: int = 100,
    session: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await QuestionService(session).list(skip=skip, limit=limit)


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: QuestionCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await QuestionService(session).create(body, admin)


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await QuestionService(session).get_or_404(question_id)


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    body: QuestionUpdate,
    session: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await QuestionService(session).update(question_id, body)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    await QuestionService(session).delete(question_id)
