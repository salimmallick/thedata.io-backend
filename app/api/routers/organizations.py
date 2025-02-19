"""
Organizations router.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..models.organization import Organization, OrganizationCreate, OrganizationUpdate
from ..core.database import db_pool, DatabaseError
import logging
import secrets
import uuid
from slugify import slugify
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Organizations"])

require_admin = PermissionChecker(["admin"])

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

@router.get("/", response_model=List[Organization])
async def list_organizations(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """List all organizations."""
    try:
        async with db_pool.postgres_connection() as conn:
            orgs = await conn.fetch("""
                SELECT 
                    id as org_id,
                    name,
                    slug,
                    api_key,
                    status,
                    subscription_tier,
                    settings,
                    metadata,
                    created_at,
                    updated_at
                FROM organizations
                ORDER BY id
            """)
            
            return [dict(org) for org in orgs]
    except DatabaseError as e:
        logger.error(f"Database error listing organizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/", response_model=Organization)
async def create_organization(
    org: OrganizationCreate,
    current_user: Dict[str, Any] = Depends(require_admin)
) -> Dict[str, Any]:
    """Create a new organization (admin only)."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Check if name exists
            existing = await conn.fetchrow("""
                SELECT id FROM organizations WHERE name = $1
            """, org.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name already exists"
                )
            
            # Generate API key and slug
            api_key = generate_api_key()
            slug = org.slug if org.slug else slugify(org.name)
            
            # Create organization
            created = await conn.fetchrow("""
                INSERT INTO organizations (
                    name,
                    slug,
                    api_key,
                    status,
                    tier,
                    settings,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING 
                    id,
                    name,
                    slug,
                    api_key,
                    status,
                    tier,
                    settings,
                    created_at,
                    updated_at
            """, 
            org.name,
            slug,
            api_key,
            'active',
            'free',
            org.settings or {})
            
            return dict(created)
    except DatabaseError as e:
        logger.error(f"Database error creating organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{org_id}/members")
async def get_organization_members(
    org_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """Get organization members."""
    try:
        async with db_pool.postgres_connection() as conn:
            members = await conn.fetch("""
                SELECT u.id, u.username, u.full_name, u.role
                FROM users u
                JOIN organization_members om ON u.id = om.user_id
                WHERE om.organization_id = $1
            """, org_id)
            
            return [dict(member) for member in members]
    except DatabaseError as e:
        logger.error(f"Database error getting organization members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error getting organization members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/{org_id}/members")
async def add_organization_member(
    org_id: int,
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Add a member to an organization."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check if organization exists
                org = await conn.fetchrow("""
                    SELECT id FROM organizations WHERE id = $1
                """, org_id)
                if not org:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Organization not found"
                    )
                
                # Check if user exists
                user = await conn.fetchrow("""
                    SELECT id FROM users WHERE id = $1
                """, user_id)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                # Check if membership already exists
                existing = await conn.fetchrow("""
                    SELECT 1 FROM organization_members
                    WHERE organization_id = $1 AND user_id = $2
                """, org_id, user_id)
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is already a member of this organization"
                    )
                
                # Add member
                await conn.execute("""
                    INSERT INTO organization_members (organization_id, user_id, role)
                    VALUES ($1, $2, $3)
                """, org_id, user_id, "member")
            
            return {"status": "success"}
    except DatabaseError as e:
        logger.error(f"Database error adding organization member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding organization member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 