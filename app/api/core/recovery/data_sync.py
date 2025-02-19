"""
Recovery procedures for data sync operations.
"""
from typing import Dict, Any, Optional
import time
from ..database import db_pool
from ..logging.logger import logger
from ..monitoring.metrics import (
    track_sync_recovery_attempt,
    track_sync_recovery_success,
    track_sync_recovery_duration
)
from ...models.data import SyncStatus

async def recover_data_sync_operation(
    context: Dict[str, Any]
) -> None:
    """
    Recover a failed data sync operation.
    
    Args:
        context: Recovery context containing operation details
    """
    source_id = context.get("source_id")
    sync_id = context.get("sync_id")
    source_type = context.get("source_type", "unknown")
    
    if not source_id:
        logger.error("Cannot recover sync operation: missing source_id")
        return
    
    start_time = time.time()
    track_sync_recovery_attempt(source_type)
    
    try:
        async with db_pool.postgres_connection() as conn:
            # Get current sync status
            source = await conn.fetchrow("""
                SELECT last_sync_status, last_sync_error, type
                FROM data_sources
                WHERE id = $1
            """, source_id)
            
            if not source:
                logger.error(f"Data source {source_id} not found")
                return
            
            # Update source type if not provided in context
            if source_type == "unknown":
                source_type = source["type"]
            
            if source["last_sync_status"] == SyncStatus.FAILED:
                # Reset sync status
                await conn.execute("""
                    UPDATE data_sources
                    SET last_sync_status = $2,
                        last_sync_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, source_id, SyncStatus.PENDING)
                
                if sync_id:
                    # Mark failed sync as recovered
                    await conn.execute("""
                        UPDATE data_syncs
                        SET status = 'recovered',
                            error = NULL,
                            completed_at = CURRENT_TIMESTAMP
                        WHERE id = $1
                    """, sync_id)
                
                # Create new sync record
                new_sync_id = await conn.fetchval("""
                    INSERT INTO data_syncs (source_id, status, parent_sync_id)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """, source_id, SyncStatus.PENDING, sync_id)
                
                logger.info(
                    f"Created recovery sync for source {source_id}",
                    extra={
                        "new_sync_id": new_sync_id,
                        "parent_sync_id": sync_id,
                        "source_type": source_type
                    }
                )
                
                # Trigger sync service if provided in context
                if "sync_service" in context:
                    await context["sync_service"].start_sync(
                        source_id,
                        sync_id=new_sync_id
                    )
                    logger.info(
                        f"Triggered recovery sync for source {source_id}",
                        extra={
                            "sync_id": new_sync_id,
                            "source_type": source_type
                        }
                    )
                
                # Track successful recovery
                track_sync_recovery_success(source_type)
                track_sync_recovery_duration(
                    source_type,
                    time.time() - start_time
                )
    
    except Exception as e:
        logger.error(
            f"Failed to recover sync operation",
            extra={
                "source_id": source_id,
                "sync_id": sync_id,
                "source_type": source_type,
                "error": str(e)
            }
        )
        raise

async def register_data_sync_recovery(recovery_manager) -> None:
    """Register data sync recovery procedures."""
    await recovery_manager.register_recovery_procedure(
        "data_sync",
        recover_data_sync_operation
    )

__all__ = ['recover_data_sync_operation', 'register_data_sync_recovery'] 