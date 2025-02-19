"""
API endpoints for data source operations with integrated metrics.
"""
from fastapi import Request, HTTPException, Depends
from typing import Dict, Any, List
import time
from ..core.routes.base import RecoverableRouter
from ..core.database import db_pool
from ..core.logging.logger import logger
from ..core.monitoring.metrics import (
    track_sync_operation,
    track_sync_duration,
    track_sync_records,
    track_sync_error
)
from ..models.data import DataSource, DataSync, SyncStatus, SourceType

router = RecoverableRouter()

@router.recoverable(
    operation_id="sync_data_source",
    path="/sources/{source_id}/sync",
    methods=["POST"]
)
async def sync_data_source(
    source_id: str,
    request: Request
) -> Dict[str, Any]:
    """
    Synchronize data from a specific source with metrics tracking.
    
    Args:
        source_id: ID of the data source
        request: FastAPI request object
    
    Returns:
        Dict[str, Any]: Sync operation status
    """
    start_time = time.time()
    sync_id = None
    source_type = None
    
    try:
        # Get source details
        async with db_pool.postgres_connection() as conn:
            source = await conn.fetchrow("""
                SELECT id, name, type, config
                FROM data_sources
                WHERE id = $1
            """, source_id)
            
            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"Data source {source_id} not found"
                )
            
            source_type = source["type"]
            track_sync_operation(source_type, SyncStatus.IN_PROGRESS)
            
            # Update sync status
            await conn.execute("""
                UPDATE data_sources
                SET last_sync_status = $2,
                    last_sync_started_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, source_id, SyncStatus.IN_PROGRESS)
        
        # Perform sync operation
        try:
            # Example sync logic
            async with db_pool.postgres_connection() as conn:
                # Create sync record
                sync_id = await conn.fetchval("""
                    INSERT INTO data_syncs (source_id, status)
                    VALUES ($1, $2)
                    RETURNING id
                """, source_id, SyncStatus.IN_PROGRESS)
                
                # Simulate sync operation
                # In a real application, this would be your actual sync logic
                await conn.execute("""
                    -- Sync operation simulation
                    SELECT pg_sleep(2)
                """)
                
                # Update sync status
                await conn.execute("""
                    UPDATE data_syncs
                    SET status = $2,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, sync_id, SyncStatus.COMPLETED)
                
                # Update source status
                await conn.execute("""
                    UPDATE data_sources
                    SET last_sync_status = $2,
                        last_successful_sync = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, source_id, SyncStatus.COMPLETED)
                
                # Track successful sync
                track_sync_operation(source_type, SyncStatus.COMPLETED)
                track_sync_duration(source_type, time.time() - start_time)
                
                # Example: Track processed records
                track_sync_records(source_type, "processed", 100)
                
                logger.info(
                    f"Data sync completed for source {source_id}",
                    extra={
                        "sync_id": sync_id,
                        "source_type": source_type,
                        "duration": time.time() - start_time
                    }
                )
                
                return {
                    "status": "success",
                    "message": "Data sync completed successfully",
                    "sync_id": sync_id,
                    "duration": time.time() - start_time
                }
                
        except Exception as e:
            # Track sync error
            track_sync_error(source_type, type(e).__name__)
            track_sync_operation(source_type, SyncStatus.FAILED)
            
            # Update sync status on failure
            async with db_pool.postgres_connection() as conn:
                await conn.execute("""
                    UPDATE data_sources
                    SET last_sync_status = $2,
                        last_sync_error = $3
                    WHERE id = $1
                """, source_id, SyncStatus.FAILED, str(e))
                
                if sync_id:
                    await conn.execute("""
                        UPDATE data_syncs
                        SET status = $2,
                            error = $3,
                            completed_at = CURRENT_TIMESTAMP
                        WHERE id = $1
                    """, sync_id, SyncStatus.FAILED, str(e))
            
            logger.error(
                f"Data sync failed for source {source_id}",
                extra={
                    "error": str(e),
                    "sync_id": sync_id if sync_id else None,
                    "source_type": source_type,
                    "duration": time.time() - start_time
                }
            )
            raise
            
    except Exception as e:
        # Ensure we track the error even if it occurred before sync started
        if source_type:
            track_sync_error(source_type, type(e).__name__)
            track_sync_operation(source_type, SyncStatus.FAILED)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data source: {str(e)}"
        )

@router.get("/sources/{source_id}/syncs")
async def list_source_syncs(
    source_id: str,
    limit: int = 10,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List sync operations for a specific data source.
    
    Args:
        source_id: ID of the data source
        limit: Maximum number of records to return
        offset: Number of records to skip
    
    Returns:
        List[Dict[str, Any]]: List of sync operations
    """
    try:
        async with db_pool.postgres_connection() as conn:
            # Check if source exists
            source = await conn.fetchrow("""
                SELECT id, type FROM data_sources WHERE id = $1
            """, source_id)
            
            if not source:
                raise HTTPException(
                    status_code=404,
                    detail=f"Data source {source_id} not found"
                )
            
            # Get sync operations
            syncs = await conn.fetch("""
                SELECT id, status, error, 
                       created_at, completed_at,
                       parent_sync_id
                FROM data_syncs
                WHERE source_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """, source_id, limit, offset)
            
            return [dict(sync) for sync in syncs]
            
    except Exception as e:
        logger.error(
            f"Failed to list sync operations",
            extra={
                "source_id": source_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sync operations: {str(e)}"
        )

__all__ = ['router'] 