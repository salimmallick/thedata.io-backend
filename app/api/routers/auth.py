"""
Authentication router.
"""
from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ..models.user import Token, User, UserCreate, UserRole
from ..core.auth.security import (
    authenticate_user,
    create_access_token,
    get_current_user_token,
    get_password_hash
)
from ..core.config.settings import Settings
from ..core.database import db_pool
import logging

logger = logging.getLogger(__name__)
settings = Settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    """Login user and return access token."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get user by email (using username field from form as email)
            user = await conn.fetchrow("""
                SELECT id, email, hashed_password, role, full_name, is_active
                FROM users
                WHERE email = $1
            """, form_data.username)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not await authenticate_user(form_data.password, user["hashed_password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={
                    "sub": user["email"],
                    "role": user["role"],
                    "full_name": user["full_name"]
                },
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "email": user["email"],
                    "role": user["role"],
                    "full_name": user["full_name"]
                }
            }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e

@router.post("/register", response_model=User)
async def register(user: UserCreate) -> Dict[str, Any]:
    """Register a new user."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check if user already exists
                existing_user = await conn.fetchrow("""
                    SELECT id FROM users WHERE email = $1
                """, user.email)
                
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                
                # Create new user
                hashed_password = get_password_hash(user.password)
                new_user = await conn.fetchrow("""
                    INSERT INTO users (email, hashed_password, full_name, role, is_active)
                    VALUES ($1, $2, $3, $4, true)
                    RETURNING id, email, full_name, role, is_active, created_at, updated_at
                """, user.email, hashed_password, user.full_name, UserRole.USER)
                
                # Convert id to string and return user data
                user_data = dict(new_user)
                user_data["id"] = str(user_data["id"])
                return user_data
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e

@router.get("/me", response_model=User)
async def get_current_user(current_user: Dict[str, Any] = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current user details."""
    try:
        async with db_pool.postgres_connection() as conn:
            user = await conn.fetchrow("""
                SELECT id, email, full_name, role, is_active, created_at, updated_at
                FROM users
                WHERE id = $1 AND is_active = true
            """, current_user["id"])
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found or inactive"
                )
            
            # Convert id to string and return user data
            user_data = dict(user)
            user_data["id"] = str(user_data["id"])
            return user_data
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e 