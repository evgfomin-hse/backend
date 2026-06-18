import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email: EmailStr
    login: str
    password: str
    role: UserRole = UserRole.player
    team_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    email: Optional[EmailStr] = None
    login: Optional[str] = None
    role: Optional[UserRole] = None
    team_id: Optional[uuid.UUID] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email: str
    login: str
    role: UserRole
    team_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}
