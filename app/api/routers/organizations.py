from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..core.auth.security import get_current_user_token, PermissionChecker
from ..models.organization import Organization, OrganizationCreate, OrganizationUpdate
from ..core.storage.database_pool import db_pool
import logging
import secrets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])

require_admin = PermissionChecker(["admin"])

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

@router.get("", response_model=List[Organization])
async def list_organizations(token = Depends(get_current_user_token)):
    """List all organizations."""
    try:
        async with db_pool.postgres_connection() as conn:
            orgs = await conn.fetch("""
                SELECT id, name, api_key, created_at
                FROM organizations
                ORDER BY id
            """)
            
            return [
                {
                    "id": str(org['id']),
                    "name": org['name'],
                    "api_key": org['api_key'],
                    "created_at": org['created_at']
                }
                for org in orgs
            ]
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("", response_model=Organization)
async def create_organization(org: OrganizationCreate, token = Depends(require_admin)):
    """Create a new organization (admin only)."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Check if name exists
            existing = await conn.fetchval(
                "SELECT id FROM organizations WHERE name = $1",
                org.name
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name already exists"
                )
            
            # Generate API key
            api_key = generate_api_key()
            
            # Create organization
            created = await conn.fetchrow("""
                INSERT INTO organizations (name, api_key)
                VALUES ($1, $2)
                RETURNING id, name, api_key, created_at
            """, org.name, api_key)
            
            return {
                "id": str(created['id']),
                "name": created['name'],
                "api_key": created['api_key'],
                "created_at": created['created_at']
            }
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
    org_id: str,
    token = Depends(get_current_user_token)
):
    """Get organization members."""
    # This is a placeholder - you'll need to implement the organization members table
    return []

@router.post("/{org_id}/members")
async def add_organization_member(
    org_id: str,
    user_id: str,
    role: str,
    token = Depends(require_admin)
):
    """Add a member to an organization (admin only)."""
    # This is a placeholder - you'll need to implement the organization members table
    return {"status": "success"} 