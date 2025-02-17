from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.VIEWER

class UserUpdate(UserBase):
    password: Optional[str] = None
    role: Optional[UserRole] = None

class User(UserBase):
    id: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    sub: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    exp: int 