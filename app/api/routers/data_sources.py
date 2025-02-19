from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from ..core.auth.security import get_current_user_token, PermissionChecker
from ..services.data_flow import data_flow_service
from ..core.database.pool import db_pool
from ..core.database.errors import DatabaseError
from ..models.data_source import DataSource, DataSourceCreate, DataSourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])

# Permission checker
require_data_admin = PermissionChecker(["manage_data"])

class DataSourceBase(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]
    description: Optional[str] = None

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(DataSourceBase):
    pass

class DataSourceInDB(DataSourceBase):
    id: str
    created_at: datetime
    updated_at: datetime
    status: str
    health: str

class DataSourceMetrics(BaseModel):
    throughput: float
    latency: float
    error_rate: float
    last_sync: datetime

@router.get("/", response_model=List[DataSource])
async def list_data_sources(
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> List[Dict[str, Any]]:
    """List all data sources for the current user's organization."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get user's organizations
            org_ids = await conn.fetch("""
                SELECT organization_id
                FROM organization_members
                WHERE user_id = $1
            """, current_user["id"])
            
            if not org_ids:
                return []
            
            # Get data sources for these organizations
            data_sources = await conn.fetch("""
                SELECT 
                    id, name, type, config, organization_id, 
                    is_active, created_at, updated_at
                FROM data_sources
                WHERE organization_id = ANY($1::bigint[])
                ORDER BY created_at DESC
            """, [org["organization_id"] for org in org_ids])
            
            return [dict(source) for source in data_sources]
    except DatabaseError as e:
        logger.error(f"Database error listing data sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Error listing data sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/", response_model=DataSource)
async def create_data_source(
    source: DataSourceCreate,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Create a new data source."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check if user has access to the organization
                member = await conn.fetchrow("""
                    SELECT role
                    FROM organization_members
                    WHERE organization_id = $1 AND user_id = $2
                """, source.organization_id, current_user["id"])
                
                if not member:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not a member of this organization"
                    )
                
                # Create data source
                new_source = await conn.fetchrow("""
                    INSERT INTO data_sources (
                        name, type, config, organization_id, is_active
                    )
                    VALUES ($1, $2, $3, $4, true)
                    RETURNING id, name, type, config, organization_id, 
                             is_active, created_at, updated_at
                """, source.name, source.type, source.config, source.organization_id)
                
                return dict(new_source)
    except DatabaseError as e:
        logger.error(f"Database error creating data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{source_id}", response_model=DataSource)
async def get_data_source(
    source_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Get a specific data source."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Get data source and check access
            source = await conn.fetchrow("""
                SELECT ds.id, ds.name, ds.type, ds.config, ds.organization_id,
                       ds.is_active, ds.created_at, ds.updated_at
                FROM data_sources ds
                JOIN organization_members om 
                    ON ds.organization_id = om.organization_id
                WHERE ds.id = $1 AND om.user_id = $2
            """, source_id, current_user["id"])
            
            if not source:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Data source not found or access denied"
                )
            
            return dict(source)
    except DatabaseError as e:
        logger.error(f"Database error getting data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{source_id}", response_model=DataSource)
async def update_data_source(
    source_id: int,
    source_update: DataSourceUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Update a data source."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check access
                existing = await conn.fetchrow("""
                    SELECT ds.id
                    FROM data_sources ds
                    JOIN organization_members om 
                        ON ds.organization_id = om.organization_id
                    WHERE ds.id = $1 AND om.user_id = $2
                """, source_id, current_user["id"])
                
                if not existing:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Data source not found or access denied"
                    )
                
                # Update data source
                update_data = source_update.dict(exclude_unset=True)
                if update_data:
                    fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(update_data.keys()))
                    values = list(update_data.values())
                    query = f"""
                        UPDATE data_sources 
                        SET {fields}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $1
                        RETURNING id, name, type, config, organization_id,
                                 is_active, created_at, updated_at
                    """
                    updated = await conn.fetchrow(query, source_id, *values)
                    return dict(updated)
                
                # If no updates, return current state
                current = await conn.fetchrow("""
                    SELECT id, name, type, config, organization_id,
                           is_active, created_at, updated_at
                    FROM data_sources
                    WHERE id = $1
                """, source_id)
                return dict(current)
    except DatabaseError as e:
        logger.error(f"Database error updating data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    source_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> None:
    """Delete a data source."""
    try:
        async with db_pool.postgres_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Check access
                existing = await conn.fetchrow("""
                    SELECT ds.id
                    FROM data_sources ds
                    JOIN organization_members om 
                        ON ds.organization_id = om.organization_id
                    WHERE ds.id = $1 AND om.user_id = $2
                """, source_id, current_user["id"])
                
                if not existing:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Data source not found or access denied"
                    )
                
                # Delete related pipelines first
                await conn.execute("""
                    DELETE FROM pipelines WHERE data_source_id = $1
                """, source_id)
                
                # Delete data source
                await conn.execute("""
                    DELETE FROM data_sources WHERE id = $1
                """, source_id)
    except DatabaseError as e:
        logger.error(f"Database error deleting data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{source_id}/metrics", response_model=DataSourceMetrics)
async def get_data_source_metrics(
    source_id: str,
    token = Depends(require_data_admin)
):
    """Get metrics for a data source"""
    return await data_flow_service.get_data_source_metrics(source_id)

@router.post("/validate")
async def validate_connection(
    config: Dict[str, Any],
    token = Depends(require_data_admin)
):
    """Validate connection configuration"""
    is_valid = await data_flow_service.validate_connection(config)
    return {"valid": is_valid} 