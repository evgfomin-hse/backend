import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.token import RefreshToken
from app.models.user import User, UserRole
from app.repositories.token import TokenRepository
from app.repositories.user import UserRepository
from app.schemas.token import TokenPair


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repo = UserRepository(session)
        self.token_repo = TokenRepository(session)
        self.session = session

    async def register(
        self,
        first_name: str,
        last_name: str,
        email: str,
        login: str,
        password: str,
        role: UserRole = UserRole.player,
        team_id: uuid.UUID | None = None,
    ) -> User:
        if await self.user_repo.get_by_email(email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        if await self.user_repo.get_by_login(login):
            raise HTTPException(status.HTTP_409_CONFLICT, "Login already taken")
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            login=login,
            hashed_password=hash_password(password),
            role=role,
            team_id=team_id,
        )
        return await self.user_repo.add(user)

    async def login(self, login: str, password: str) -> TokenPair:
        user = await self.user_repo.get_by_login(login)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        return await self._issue_tokens(user)

    async def refresh(self, raw_token: str) -> TokenPair:
        token_hash = hash_refresh_token(raw_token)
        token = await self.token_repo.get_by_hash(token_hash)
        if not token or token.revoked_at is not None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        expires = token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")
        token.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()
        return await self._issue_tokens(token.user)

    async def change_password(self, user: User, old_password: str, new_password: str) -> None:
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Wrong current password")
        user.hashed_password = hash_password(new_password)
        await self.session.flush()

    async def _issue_tokens(self, user: User) -> TokenPair:
        access_token = create_access_token(user.id, user.role.value)
        raw_refresh = generate_refresh_token()
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        await self.token_repo.add(refresh_token_obj)
        return TokenPair(access_token=access_token, refresh_token=raw_refresh)
