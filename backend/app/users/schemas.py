from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.users.model import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    role: str = UserRole.USER.value
    is_active: bool
    is_approved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    is_approved: bool | None = None
    role: str | None = None
    is_active: bool | None = None
