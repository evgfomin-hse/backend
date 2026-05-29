from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.token import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    user = await service.register(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        login=body.login,
        password=body.password,
        role=body.role,
        team_id=body.team_id,
    )
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)):
    return await AuthService(session).login(body.login, body.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_db)):
    return await AuthService(session).refresh(body.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await AuthService(session).change_password(current_user, body.old_password, body.new_password)
