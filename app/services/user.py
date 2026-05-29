import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        return user

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repo.list(skip=skip, limit=limit)

    async def create(self, body: UserCreate) -> User:
        if await self.repo.get_by_email(body.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        if await self.repo.get_by_login(body.login):
            raise HTTPException(status.HTTP_409_CONFLICT, "Login already taken")
        user = User(
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            login=body.login,
            hashed_password=hash_password(body.password),
            role=body.role,
            team_id=body.team_id,
        )
        return await self.repo.add(user)

    async def update(self, user_id: uuid.UUID, body: UserUpdate) -> User:
        user = await self.get_or_404(user_id)
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        await self.repo.session.flush()
        await self.repo.session.refresh(user)
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.get_or_404(user_id)
        await self.repo.delete(user)
