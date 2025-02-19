"""
Data source service implementation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from fastapi import HTTPException, status

from ..models.data_source import (
    DataSource, DataSourceCreate, DataSourceUpdate,
    DataSourceType, DataSourceStatus, DataSourceHealth,
    DataSourceValidationResult, DataSourceMetrics, DataSourceLog
)
from ..core.database import db_pool, DatabaseError
from ..core.monitoring.instances import metrics
from .data_source_validator import data_source_validator

logger = logging.getLogger(__name__)

class DataSourceService:
    """Service for managing data sources."""
    
    async def list_data_sources(self, user_id: int) -> List[Dict[str, Any]]:
        """List all data sources for user's organizations."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get user's organization memberships
                sources = await conn.fetch("""
                    SELECT ds.* 
                    FROM data_sources ds
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE om.user_id = $1
                    ORDER BY ds.created_at DESC
                """, user_id)
                
                return [dict(source) for source in sources]
                
        except DatabaseError as e:
            logger.error(f"Database error in list_data_sources: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def create_data_source(
        self,
        source: DataSourceCreate,
        user_id: int
    ) -> Dict[str, Any]:
        """Create a new data source."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Start transaction
                async with conn.transaction():
                    # Verify user has access to organization
                    org_access = await conn.fetchrow("""
                        SELECT 1 FROM organization_members
                        WHERE organization_id = $1 AND user_id = $2
                    """, source.organization_id, user_id)
                    
                    if not org_access:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have access to this organization"
                        )
                    
                    # Check if name exists in organization
                    existing = await conn.fetchrow("""
                        SELECT id FROM data_sources
                        WHERE organization_id = $1 AND name = $2
                    """, source.organization_id, source.name)
                    
                    if existing:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Data source with this name already exists"
                        )
                    
                    # Create data source
                    created = await conn.fetchrow("""
                        INSERT INTO data_sources (
                            name, description, type, config, tags,
                            organization_id, status, health
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING *
                    """,
                    source.name,
                    source.description,
                    source.type.value,
                    source.config.dict(),
                    source.tags,
                    source.organization_id,
                    DataSourceStatus.INACTIVE.value,
                    DataSourceHealth.UNKNOWN.value
                    )
                    
                    return dict(created)
                    
        except DatabaseError as e:
            logger.error(f"Database error in create_data_source: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def get_data_source(
        self,
        source_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Get a specific data source."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get data source with access check
                source = await conn.fetchrow("""
                    SELECT ds.* 
                    FROM data_sources ds
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE ds.id = $1 AND om.user_id = $2
                """, source_id, user_id)
                
                if not source:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Data source not found"
                    )
                
                return dict(source)
                
        except DatabaseError as e:
            logger.error(f"Database error in get_data_source: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def update_data_source(
        self,
        source_id: int,
        source_update: DataSourceUpdate,
        user_id: int
    ) -> Dict[str, Any]:
        """Update a data source."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Start transaction
                async with conn.transaction():
                    # Get current data source with access check
                    current = await conn.fetchrow("""
                        SELECT ds.* 
                        FROM data_sources ds
                        JOIN organization_members om ON ds.organization_id = om.organization_id
                        WHERE ds.id = $1 AND om.user_id = $2
                        FOR UPDATE
                    """, source_id, user_id)
                    
                    if not current:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data source not found"
                        )
                    
                    # Build update query dynamically
                    updates = []
                    values = [source_id]
                    update_idx = 2
                    
                    if source_update.name is not None:
                        # Check name uniqueness in organization
                        name_exists = await conn.fetchrow("""
                            SELECT 1 FROM data_sources
                            WHERE organization_id = $1 AND name = $2 AND id != $3
                        """, current["organization_id"], source_update.name, source_id)
                        
                        if name_exists:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Data source with this name already exists"
                            )
                        updates.append(f"name = ${update_idx}")
                        values.append(source_update.name)
                        update_idx += 1
                    
                    if source_update.description is not None:
                        updates.append(f"description = ${update_idx}")
                        values.append(source_update.description)
                        update_idx += 1
                    
                    if source_update.type is not None:
                        updates.append(f"type = ${update_idx}")
                        values.append(source_update.type.value)
                        update_idx += 1
                    
                    if source_update.config is not None:
                        updates.append(f"config = ${update_idx}")
                        values.append(source_update.config.dict())
                        update_idx += 1
                    
                    if source_update.tags is not None:
                        updates.append(f"tags = ${update_idx}")
                        values.append(source_update.tags)
                        update_idx += 1
                    
                    if source_update.status is not None:
                        updates.append(f"status = ${update_idx}")
                        values.append(source_update.status.value)
                        update_idx += 1
                    
                    if updates:
                        # Perform update
                        updated = await conn.fetchrow(f"""
                            UPDATE data_sources
                            SET {", ".join(updates)},
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = $1
                            RETURNING *
                        """, *values)
                        
                        return dict(updated)
                    
                    return dict(current)
                    
        except DatabaseError as e:
            logger.error(f"Database error in update_data_source: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def delete_data_source(self, source_id: int, user_id: int) -> None:
        """Delete a data source."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Start transaction
                async with conn.transaction():
                    # Get data source with access check
                    source = await conn.fetchrow("""
                        SELECT ds.* 
                        FROM data_sources ds
                        JOIN organization_members om ON ds.organization_id = om.organization_id
                        WHERE ds.id = $1 AND om.user_id = $2
                        FOR UPDATE
                    """, source_id, user_id)
                    
                    if not source:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data source not found"
                        )
                    
                    # Delete related pipelines first
                    await conn.execute("""
                        DELETE FROM pipelines
                        WHERE data_source_id = $1
                    """, source_id)
                    
                    # Delete data source
                    await conn.execute("""
                        DELETE FROM data_sources
                        WHERE id = $1
                    """, source_id)
                    
        except DatabaseError as e:
            logger.error(f"Database error in delete_data_source: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def validate_connection(
        self,
        source_id: int,
        user_id: int
    ) -> DataSourceValidationResult:
        """Validate data source connection."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get data source with access check
                source = await conn.fetchrow("""
                    SELECT ds.* 
                    FROM data_sources ds
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE ds.id = $1 AND om.user_id = $2
                """, source_id, user_id)
                
                if not source:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Data source not found"
                    )
                
                # Update status to validating
                await conn.execute("""
                    UPDATE data_sources
                    SET status = $1, last_validated = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, DataSourceStatus.VALIDATING.value, source_id)
                
                # Perform validation using validator
                validation_result = await data_source_validator.validate(
                    source["type"],
                    source["config"]
                )
                
                # Update status based on validation result
                await conn.execute("""
                    UPDATE data_sources
                    SET status = $1,
                        health = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                """,
                validation_result.status.value,
                validation_result.health.value,
                source_id
                )
                
                # Log validation event
                await conn.execute("""
                    INSERT INTO data_source_logs (
                        data_source_id, level, message, details
                    ) VALUES ($1, $2, $3, $4)
                """,
                source_id,
                "INFO" if validation_result.is_valid else "ERROR",
                f"Connection validation {'succeeded' if validation_result.is_valid else 'failed'}",
                {
                    "validation_details": validation_result.validation_details,
                    "error_message": validation_result.error_message
                }
                )
                
                return validation_result
                
        except DatabaseError as e:
            logger.error(f"Database error in validate_connection: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
    
    async def get_metrics(
        self,
        source_id: int,
        user_id: int
    ) -> DataSourceMetrics:
        """Get data source metrics."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get data source with access check
                source = await conn.fetchrow("""
                    SELECT ds.* 
                    FROM data_sources ds
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE ds.id = $1 AND om.user_id = $2
                """, source_id, user_id)
                
                if not source:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Data source not found"
                    )
                
                # Get latest metrics
                metrics_data = await conn.fetchrow("""
                    SELECT *
                    FROM data_source_metrics
                    WHERE data_source_id = $1
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, source_id)
                
                if not metrics_data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No metrics found for data source"
                    )
                
                return DataSourceMetrics(**dict(metrics_data))
                
        except DatabaseError as e:
            logger.error(f"Database error in get_metrics: {str(e)}")
            metrics.track_error("database_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

# Create global service instance
data_source_service = DataSourceService() 