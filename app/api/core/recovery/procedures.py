"""
Common recovery procedures for critical operations.
"""
from typing import Dict, Any, Optional
import logging
from ..database import db_pool, DatabaseError
from ..monitoring.instances import metrics
from ..logging.logger import logger
from .manager import recovery_manager
from .data_sync import register_data_sync_recovery

async def recover_database_connection(
    database: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Recover database connection."""
    logger.info(f"Attempting to recover {database} connection")
    
    try:
        if database == "postgres":
            await db_pool._init_postgres_pool()
        elif database == "redis":
            await db_pool._init_redis_pool()
        
        # Verify connection
        async with getattr(db_pool, f"{database}_connection")() as conn:
            if database == "postgres":
                await conn.execute("SELECT 1")
            elif database == "redis":
                await conn.ping()
        
        logger.info(f"Successfully recovered {database} connection")
        
    except Exception as e:
        logger.error(f"Failed to recover {database} connection: {str(e)}")
        raise

async def recover_transaction(
    database: str,
    transaction_id: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Recover a failed database transaction."""
    logger.info(f"Attempting to recover transaction {transaction_id}")
    
    try:
        async with getattr(db_pool, f"{database}_connection")() as conn:
            # Check transaction status
            status = await conn.fetchval("""
                SELECT status FROM transaction_logs
                WHERE transaction_id = $1
            """, transaction_id)
            
            if status == "failed":
                # Rollback transaction
                await conn.execute("""
                    ROLLBACK TRANSACTION $1
                """, transaction_id)
                
                # Mark as rolled back
                await conn.execute("""
                    UPDATE transaction_logs
                    SET status = 'rolled_back',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE transaction_id = $1
                """, transaction_id)
                
                logger.info(f"Successfully rolled back transaction {transaction_id}")
            
            elif status == "pending":
                # Attempt to complete transaction
                if context and "operations" in context:
                    for op in context["operations"]:
                        await conn.execute(op["query"], *op["params"])
                
                # Mark as completed
                await conn.execute("""
                    UPDATE transaction_logs
                    SET status = 'completed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE transaction_id = $1
                """, transaction_id)
                
                logger.info(f"Successfully completed transaction {transaction_id}")
    
    except Exception as e:
        logger.error(f"Failed to recover transaction {transaction_id}: {str(e)}")
        raise

async def recover_data_sync(
    source_id: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Recover a failed data synchronization."""
    logger.info(f"Attempting to recover data sync for source {source_id}")
    
    try:
        async with db_pool.postgres_connection() as conn:
            # Get sync status
            status = await conn.fetchrow("""
                SELECT last_sync_status, last_successful_sync
                FROM data_sources
                WHERE id = $1
            """, source_id)
            
            if status["last_sync_status"] == "failed":
                # Reset sync status
                await conn.execute("""
                    UPDATE data_sources
                    SET last_sync_status = 'pending',
                        retry_count = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, source_id)
                
                # Trigger new sync
                if context and "sync_service" in context:
                    await context["sync_service"].start_sync(source_id)
                
                logger.info(f"Successfully initiated new sync for source {source_id}")
    
    except Exception as e:
        logger.error(f"Failed to recover data sync for source {source_id}: {str(e)}")
        raise

async def recover_pipeline(
    pipeline_id: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Recover a failed pipeline."""
    logger.info(f"Attempting to recover pipeline {pipeline_id}")
    
    try:
        async with db_pool.postgres_connection() as conn:
            # Get pipeline status
            status = await conn.fetchrow("""
                SELECT status, error, last_run
                FROM pipelines
                WHERE id = $1
            """, pipeline_id)
            
            if status["status"] == "failed":
                # Reset pipeline status
                await conn.execute("""
                    UPDATE pipelines
                    SET status = 'pending',
                        error = NULL,
                        retry_count = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, pipeline_id)
                
                # Restart pipeline
                if context and "pipeline_service" in context:
                    await context["pipeline_service"].start_pipeline(pipeline_id)
                
                logger.info(f"Successfully restarted pipeline {pipeline_id}")
    
    except Exception as e:
        logger.error(f"Failed to recover pipeline {pipeline_id}: {str(e)}")
        raise

# Register common recovery procedures
async def register_common_procedures():
    """Register common recovery procedures."""
    await recovery_manager.register_recovery_procedure(
        "postgres_connection",
        lambda: recover_database_connection("postgres")
    )
    await recovery_manager.register_recovery_procedure(
        "redis_connection",
        lambda: recover_database_connection("redis")
    )
    await recovery_manager.register_recovery_procedure(
        "transaction",
        recover_transaction
    )
    await recovery_manager.register_recovery_procedure(
        "pipeline",
        recover_pipeline
    )
    
    # Register data sync recovery procedures
    await register_data_sync_recovery(recovery_manager)
    
    logger.info("Registered all recovery procedures")

__all__ = [
    'recover_database_connection',
    'recover_transaction',
    'recover_data_sync',
    'recover_pipeline',
    'register_common_procedures'
] 