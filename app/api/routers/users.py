"""
User management router.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..models.user import User, UserCreate, UserUpdate
from ..core.auth.security import get_current_user_token, get_password_hash
from ..core.database import db_pool, DatabaseError
import logging
from fastapi.responses import RedirectResponse
import warnings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])

@router.get("/")
async def list_users(current_user: Dict[str, Any] = Depends(get_current_user_token)) -> List[Dict[str, Any]]:
    """List all users (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        async with db_pool.postgres_connection() as conn:
            users = await conn.fetch("""
                SELECT id, email, full_name, role, is_active, created_at, updated_at
                FROM users
                ORDER BY id
            """)
            return [dict(user) for user in users]
    except DatabaseError as e:
        logger.error(f"Database error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me")
async def get_current_user_deprecated(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> RedirectResponse:
    """
    [DEPRECATED] Get current user information.
    This endpoint is deprecated, please use /api/v1/auth/me instead.
    """
    warnings.warn(
        "This endpoint is deprecated. Please use /api/v1/auth/me instead.",
        DeprecationWarning
    )
    return RedirectResponse(
        url="/api/v1/auth/me",
        status_code=status.HTTP_308_PERMANENT_REDIRECT
    )

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Update current user details."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                update_data = user_update.dict(exclude_unset=True)
                if "password" in update_data:
                    update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
                
                if update_data:
                    # Build update query
                    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(update_data.keys()))
                    values = list(update_data.values())
                    query = f"""
                        UPDATE users 
                        SET {fields}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $1
                        RETURNING id, username, full_name, role, is_active, created_at, updated_at
                    """
                    updated_user = await conn.fetchrow(query, current_user["id"], *values)
                    return dict(updated_user)
                
                # If no updates, return current user
                user = await conn.fetchrow("""
                    SELECT id, username, full_name, role, is_active, created_at, updated_at
                    FROM users
                    WHERE id = $1
                """, current_user["id"])
                return dict(user)
    except DatabaseError as e:
        logger.error(f"Database error updating current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error updating current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Get user details by ID (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        async with db_pool.postgres_connection() as conn:
            user = await conn.fetchrow("""
                SELECT id, username, full_name, role, is_active, created_at, updated_at
                FROM users
                WHERE id = $1
            """, user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return dict(user)
    except DatabaseError as e:
        logger.error(f"Database error getting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Update user details (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check if user exists
                existing_user = await conn.fetchrow("""
                    SELECT id FROM users WHERE id = $1
                """, user_id)
                if not existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                # Update user
                update_data = user_update.dict(exclude_unset=True)
                if "password" in update_data:
                    update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
                
                if update_data:
                    # Build update query
                    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(update_data.keys()))
                    values = list(update_data.values())
                    query = f"""
                        UPDATE users 
                        SET {fields}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $1
                        RETURNING id, username, full_name, role, is_active, created_at, updated_at
                    """
                    updated_user = await conn.fetchrow(query, user_id, *values)
                    return dict(updated_user)
                
                # If no updates, return current user state
                user = await conn.fetchrow("""
                    SELECT id, username, full_name, role, is_active, created_at, updated_at
                    FROM users
                    WHERE id = $1
                """, user_id)
                return dict(user)
    except DatabaseError as e:
        logger.error(f"Database error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> None:
    """Delete user (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check if user exists
                existing_user = await conn.fetchrow("""
                    SELECT id FROM users WHERE id = $1
                """, user_id)
                if not existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                # Delete user's organization memberships first
                await conn.execute("""
                    DELETE FROM organization_members WHERE user_id = $1
                """, user_id)
                
                # Delete user
                await conn.execute("""
                    DELETE FROM users WHERE id = $1
                """, user_id)
    except DatabaseError as e:
        logger.error(f"Database error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 