from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..models.user import User, UserCreate, UserUpdate, UserRole
from ..core.storage.database_pool import db_pool
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

require_admin = PermissionChecker([UserRole.ADMIN.value])

@router.get("", response_model=List[User])
async def list_users(token = Depends(require_admin)):
    """List all users (admin only)."""
    try:
        async with db_pool.postgres_connection() as conn:
            users = await conn.fetch("""
                SELECT id, email, full_name, is_superuser, is_active, created_at, updated_at
                FROM users
                ORDER BY id
            """)
            
            return [
                {
                    "id": str(user['id']),
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "role": UserRole.ADMIN if user['is_superuser'] else UserRole.VIEWER,
                    "is_active": user['is_active'],
                    "created_at": user['created_at'],
                    "updated_at": user['updated_at']
                }
                for user in users
            ]
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("", response_model=User)
async def create_user(user: UserCreate, token = Depends(require_admin)):
    """Create a new user (admin only)."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Check if email exists
            existing = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1",
                user.email
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create user
            created = await conn.fetchrow("""
                INSERT INTO users (email, full_name, is_superuser, is_active, hashed_password)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, email, full_name, is_superuser, is_active, created_at, updated_at
            """, user.email, user.full_name, user.role == UserRole.ADMIN, user.is_active, user.hashed_password)
            
            return {
                "id": str(created['id']),
                "email": created['email'],
                "full_name": created['full_name'],
                "role": UserRole.ADMIN if created['is_superuser'] else UserRole.VIEWER,
                "is_active": created['is_active'],
                "created_at": created['created_at'],
                "updated_at": created['updated_at']
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/roles")
async def get_user_roles(token = Depends(get_current_user_token)):
    """Get available user roles."""
    return [role.value for role in UserRole] 