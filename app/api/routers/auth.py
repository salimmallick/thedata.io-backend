from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Dict, Any
from datetime import timedelta
from ..core.auth.security import (
    verify_password,
    create_access_token,
    get_current_user_token,
    PermissionChecker,
    get_password_hash
)
from ..core.storage.database import get_postgres_conn
from ..models.user import (
    User,
    UserCreate,
    UserUpdate,
    Token,
    TokenData,
    UserRole
)
import asyncpg
import logging
from ..core.storage.database_pool import postgres_pool, init_postgres_pool, db_pool
from fastapi import Request
from ..core.config import settings

logger = logging.getLogger(__name__)

class InvalidCredentialsError(HTTPException):
    """Exception raised when login credentials are invalid."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

router = APIRouter(prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])

# Permission checkers
require_admin = PermissionChecker(["admin"])
require_user_management = PermissionChecker(["manage_users"])

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, Any]:
    """Login endpoint that returns a JWT token"""
    
    try:
        async with db_pool.postgres_connection() as conn:
            # First check if the user exists and is active
            user = await conn.fetchrow(
                """
                SELECT id, email, full_name, is_superuser, hashed_password
                FROM users
                WHERE email = $1 AND is_active = true
                """,
                form_data.username
            )
            
            if not user:
                raise InvalidCredentialsError()
            
            # Verify password
            if not verify_password(form_data.password, user['hashed_password']):
                raise InvalidCredentialsError()
            
            # Create access token
            access_token = create_access_token(
                data={
                    "sub": str(user['id']),
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "role": "admin" if user['is_superuser'] else "viewer"
                }
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user['id']),
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "role": "admin" if user['is_superuser'] else "viewer",
                    "isAdmin": user['is_superuser'],
                    "permissions": ["admin"] if user['is_superuser'] else ["viewer"]
                }
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/users", response_model=User)
async def create_user(
    user_in: UserCreate,
    token: TokenData = Depends(require_admin)
):
    """Create new user (admin only)."""
    async with get_postgres_conn() as conn:
        # Check if user exists
        existing_user = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1",
            user_in.email
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = await conn.fetchrow(
            """
            INSERT INTO users (email, full_name, role, hashed_password, is_active)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, full_name, role, is_active, created_at, updated_at
            """,
            user_in.email,
            user_in.full_name,
            user_in.role,
            get_password_hash(user_in.password),
            user_in.is_active
        )
        
        return User(**user)

@router.get("/users", response_model=List[User])
async def list_users(
    token: TokenData = Depends(require_user_management)
):
    """List all users (requires user management permission)."""
    async with get_postgres_conn() as conn:
        users = await conn.fetch("SELECT * FROM users")
        return [User(**user) for user in users]

@router.get("/users/me", response_model=User)
async def get_current_user(
    token: TokenData = Depends(get_current_user_token)
):
    """Get current user information."""
    try:
        async with db_pool.postgres_connection() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, full_name, is_superuser, is_active, created_at, updated_at
                FROM users
                WHERE id = $1 AND is_active = true
                """,
                int(token.sub)  # Use the user ID from the token
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Convert to response format
            return {
                "id": str(user['id']),
                "email": user['email'],
                "full_name": user['full_name'],
                "role": "admin" if user['is_superuser'] else "viewer",
                "is_active": user['is_active'],
                "created_at": user['created_at'],
                "updated_at": user['updated_at'],
                "isAdmin": user['is_superuser'],
                "permissions": ["admin"] if user['is_superuser'] else ["viewer"]
            }
            
    except asyncpg.PostgresError as e:
        logger.error(f"Database error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    token: TokenData = Depends(require_user_management)
):
    """Update user information (requires user management permission)."""
    async with get_postgres_conn() as conn:
        # Check if user exists
        existing_user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user
        update_dict = user_in.dict(exclude_unset=True)
        if "password" in update_dict:
            update_dict["hashed_password"] = get_password_hash(update_dict.pop("password"))
        
        if update_dict:
            fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(update_dict.keys()))
            values = list(update_dict.values())
            query = f"""
                UPDATE users 
                SET {fields}, updated_at = NOW()
                WHERE id = $1
                RETURNING id, email, full_name, role, is_active, created_at, updated_at
            """
            user = await conn.fetchrow(query, user_id, *values)
            return User(**user)
        
        return User(**existing_user) 