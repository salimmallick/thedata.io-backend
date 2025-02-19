"""
User models.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from enum import Enum

class UserRole(str, Enum):
    """User role enum."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    """User creation model."""
    password: str

class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    """User model."""
    id: str
    role: UserRole
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""
        from_attributes = True

class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    """Token data model."""
    sub: str
    role: UserRole
    full_name: str 