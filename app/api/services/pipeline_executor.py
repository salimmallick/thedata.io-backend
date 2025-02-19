"""
Pipeline executor service for handling pipeline execution.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status

from ..core.database import db_pool, DatabaseError
from ..models.pipeline import (
    Pipeline, PipelineStatus, PipelineHealth,
    PipelineMetrics, PipelineLog, LogLevel
)

logger = logging.getLogger(__name__)

class PipelineExecutor:
    """Service for executing data pipelines."""

    def __init__(self):
        """Initialize pipeline executor."""
        self._running_pipelines: Dict[int, asyncio.Task] = {}
        self._pipeline_metrics: Dict[int, PipelineMetrics] = {}

    async def start_pipeline(self, pipeline_id: int) -> None:
        """Start pipeline execution."""
        if pipeline_id in self._running_pipelines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline is already running"
            )

        try:
            async with db_pool.postgres_connection() as conn:
                pipeline = await conn.fetchrow("""
                    SELECT id, name, type, config, schedule
                    FROM pipelines
                    WHERE id = $1
                """, pipeline_id)

                if not pipeline:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pipeline not found"
                    )

                # Initialize metrics
                self._pipeline_metrics[pipeline_id] = PipelineMetrics(
                    throughput=0.0,
                    latency=0.0,
                    error_rate=0.0,
                    success_rate=0.0,
                    processed_records=0,
                    failed_records=0
                )

                # Start pipeline execution task
                task = asyncio.create_task(
                    self._execute_pipeline(pipeline_id, dict(pipeline))
                )
                self._running_pipelines[pipeline_id] = task

                # Log pipeline start
                await self._log_pipeline_event(
                    pipeline_id,
                    LogLevel.INFO,
                    f"Pipeline {pipeline['name']} started",
                    {"type": pipeline["type"]}
                )

        except DatabaseError as e:
            logger.error(f"Database error starting pipeline {pipeline_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def stop_pipeline(self, pipeline_id: int) -> None:
        """Stop pipeline execution."""
        if pipeline_id not in self._running_pipelines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline is not running"
            )

        try:
            # Cancel the pipeline task
            task = self._running_pipelines[pipeline_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # Update pipeline status
            async with db_pool.postgres_connection() as conn:
                await conn.execute("""
                    UPDATE pipelines
                    SET status = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, pipeline_id, PipelineStatus.STOPPED)

                # Log pipeline stop
                await self._log_pipeline_event(
                    pipeline_id,
                    LogLevel.INFO,
                    "Pipeline stopped",
                    {"final_metrics": self._pipeline_metrics[pipeline_id].dict()}
                )

            # Cleanup
            del self._running_pipelines[pipeline_id]
            del self._pipeline_metrics[pipeline_id]

        except DatabaseError as e:
            logger.error(f"Database error stopping pipeline {pipeline_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def get_pipeline_status(self, pipeline_id: int) -> Dict[str, Any]:
        """Get pipeline execution status."""
        try:
            async with db_pool.postgres_connection() as conn:
                status = await conn.fetchrow("""
                    SELECT status, health, last_run
                    FROM pipelines
                    WHERE id = $1
                """, pipeline_id)

                if not status:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pipeline not found"
                    )

                return {
                    "status": status["status"],
                    "health": status["health"],
                    "is_running": pipeline_id in self._running_pipelines,
                    "metrics": self._pipeline_metrics.get(pipeline_id),
                    "last_run": status["last_run"]
                }

        except DatabaseError as e:
            logger.error(f"Database error getting pipeline status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def _execute_pipeline(self, pipeline_id: int, pipeline: Dict[str, Any]) -> None:
        """Execute pipeline logic."""
        try:
            # Initialize execution
            start_time = datetime.now(timezone.utc)
            processed_records = 0
            failed_records = 0

            # Get source and destination connections
            source_config = pipeline["config"]["source_config"]
            dest_config = pipeline["config"]["destination_config"]

            async with db_pool.postgres_connection() as conn:
                # Update pipeline status to running
                await conn.execute("""
                    UPDATE pipelines
                    SET status = $2,
                        health = $3,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, pipeline_id, PipelineStatus.RUNNING, PipelineHealth.HEALTHY)

                # Execute pipeline based on type
                if pipeline["type"] == "etl":
                    await self._execute_etl_pipeline(
                        pipeline_id, source_config, dest_config
                    )
                elif pipeline["type"] == "streaming":
                    await self._execute_streaming_pipeline(
                        pipeline_id, source_config, dest_config
                    )
                else:
                    await self._execute_custom_pipeline(
                        pipeline_id, pipeline["config"]
                    )

                # Update final status
                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds()
                
                metrics = self._pipeline_metrics[pipeline_id]
                await conn.execute("""
                    UPDATE pipelines
                    SET status = $2,
                        health = $3,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, pipeline_id, PipelineStatus.COMPLETED, PipelineHealth.HEALTHY)

                # Store final metrics
                await conn.execute("""
                    INSERT INTO pipeline_metrics (
                        pipeline_id, timestamp, throughput, latency,
                        error_rate, success_rate, processed_records,
                        failed_records
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, pipeline_id, end_time, metrics.throughput,
                     metrics.latency, metrics.error_rate, metrics.success_rate,
                     metrics.processed_records, metrics.failed_records)

        except asyncio.CancelledError:
            # Pipeline was stopped
            raise

        except Exception as e:
            logger.error(f"Error executing pipeline {pipeline_id}: {str(e)}")
            try:
                async with db_pool.postgres_connection() as conn:
                    await conn.execute("""
                        UPDATE pipelines
                        SET status = $2,
                            health = $3,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = $1
                    """, pipeline_id, PipelineStatus.FAILED, PipelineHealth.UNHEALTHY)

                    await self._log_pipeline_event(
                        pipeline_id,
                        LogLevel.ERROR,
                        f"Pipeline execution failed: {str(e)}",
                        {"error": str(e)}
                    )
            except Exception as log_error:
                logger.error(f"Error logging pipeline failure: {str(log_error)}")

        finally:
            # Cleanup
            if pipeline_id in self._running_pipelines:
                del self._running_pipelines[pipeline_id]
            if pipeline_id in self._pipeline_metrics:
                del self._pipeline_metrics[pipeline_id]

    async def _execute_etl_pipeline(
        self,
        pipeline_id: int,
        source_config: Dict[str, Any],
        dest_config: Dict[str, Any]
    ) -> None:
        """Execute ETL pipeline."""
        try:
            # Extract data from source
            data = await self._extract_data(pipeline_id, source_config)
            
            # Transform data
            transformed_data = await self._transform_data(pipeline_id, data)
            
            # Load data to destination
            await self._load_data(pipeline_id, transformed_data, dest_config)
            
        except Exception as e:
            logger.error(f"Error in ETL pipeline {pipeline_id}: {str(e)}")
            raise

    async def _execute_streaming_pipeline(
        self,
        pipeline_id: int,
        source_config: Dict[str, Any],
        dest_config: Dict[str, Any]
    ) -> None:
        """Execute streaming pipeline."""
        try:
            # Initialize streaming connection
            async with self._get_streaming_connection(source_config) as stream:
                while True:
                    # Process stream data
                    data = await stream.get_data()
                    if not data:
                        continue
                    
                    # Transform and load data
                    transformed_data = await self._transform_data(pipeline_id, data)
                    await self._load_data(pipeline_id, transformed_data, dest_config)
                    
                    # Update metrics
                    await self._update_metrics(pipeline_id, len(data), 0)
                    
        except Exception as e:
            logger.error(f"Error in streaming pipeline {pipeline_id}: {str(e)}")
            raise

    async def _execute_custom_pipeline(
        self,
        pipeline_id: int,
        config: Dict[str, Any]
    ) -> None:
        """Execute custom pipeline."""
        try:
            # Execute custom pipeline logic based on config
            custom_logic = config.get("custom_logic", {})
            if not custom_logic:
                raise ValueError("Custom pipeline requires custom_logic configuration")
            
            # Execute custom logic
            await self._execute_custom_logic(pipeline_id, custom_logic)
            
        except Exception as e:
            logger.error(f"Error in custom pipeline {pipeline_id}: {str(e)}")
            raise

    async def _extract_data(
        self,
        pipeline_id: int,
        source_config: Dict[str, Any]
    ) -> Any:
        """Extract data from source."""
        # Implement data extraction logic
        pass

    async def _transform_data(
        self,
        pipeline_id: int,
        data: Any
    ) -> Any:
        """Transform data."""
        # Implement data transformation logic
        pass

    async def _load_data(
        self,
        pipeline_id: int,
        data: Any,
        dest_config: Dict[str, Any]
    ) -> None:
        """Load data to destination."""
        # Implement data loading logic
        pass

    async def _get_streaming_connection(
        self,
        config: Dict[str, Any]
    ) -> Any:
        """Get streaming connection."""
        # Implement streaming connection logic
        pass

    async def _execute_custom_logic(
        self,
        pipeline_id: int,
        custom_logic: Dict[str, Any]
    ) -> None:
        """Execute custom pipeline logic."""
        # Implement custom logic execution
        pass

    async def _update_metrics(
        self,
        pipeline_id: int,
        processed: int,
        failed: int
    ) -> None:
        """Update pipeline metrics."""
        metrics = self._pipeline_metrics[pipeline_id]
        metrics.processed_records += processed
        metrics.failed_records += failed
        
        # Calculate rates
        total_records = metrics.processed_records + metrics.failed_records
        if total_records > 0:
            metrics.success_rate = (metrics.processed_records / total_records) * 100
            metrics.error_rate = (metrics.failed_records / total_records) * 100

    async def _log_pipeline_event(
        self,
        pipeline_id: int,
        level: LogLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log pipeline event."""
        try:
            async with db_pool.postgres_connection() as conn:
                await conn.execute("""
                    INSERT INTO pipeline_logs (
                        pipeline_id, level, message, details
                    ) VALUES ($1, $2, $3, $4)
                """, pipeline_id, level, message, details)
        except Exception as e:
            logger.error(f"Error logging pipeline event: {str(e)}")

# Create singleton instance
pipeline_executor = PipelineExecutor() 