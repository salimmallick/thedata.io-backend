"""
Pipeline service for managing data pipelines.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from fastapi import HTTPException, status

from ..core.database import db_pool, DatabaseError
from ..models.pipeline import (
    Pipeline, PipelineCreate, PipelineUpdate,
    PipelineStatus, PipelineHealth, PipelineStatusResponse,
    PipelineLogs, PipelineLog
)
from .pipeline_executor import pipeline_executor

logger = logging.getLogger(__name__)

class PipelineService:
    """Service for managing data pipelines."""

    async def list_pipelines(self, user_id: int) -> List[Dict[str, Any]]:
        """List all pipelines for user's organizations."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get user's organizations
                org_ids = await conn.fetch("""
                    SELECT organization_id
                    FROM organization_members
                    WHERE user_id = $1
                """, user_id)
                
                if not org_ids:
                    return []
                
                # Get pipelines for these organizations
                pipelines = await conn.fetch("""
                    SELECT p.id, p.name, p.description, p.config, p.type,
                           p.schedule, p.status, p.health, p.version,
                           p.organization_id, p.data_source_id,
                           p.created_at, p.updated_at, p.last_run
                    FROM pipelines p
                    JOIN data_sources ds ON p.data_source_id = ds.id
                    WHERE ds.organization_id = ANY($1::bigint[])
                    ORDER BY p.created_at DESC
                """, [org["organization_id"] for org in org_ids])
                
                # Add running status from executor
                result = []
                for pipeline in pipelines:
                    pipeline_dict = dict(pipeline)
                    pipeline_dict["is_running"] = pipeline["id"] in pipeline_executor._running_pipelines
                    result.append(pipeline_dict)
                
                return result
        except DatabaseError as e:
            logger.error(f"Database error listing pipelines: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def create_pipeline(
        self, pipeline: PipelineCreate, user_id: int
    ) -> Dict[str, Any]:
        """Create a new pipeline."""
        try:
            async with db_pool.postgres_connection() as conn:
                async with conn.transaction():
                    # Check if user has access to the data source
                    access = await conn.fetchrow("""
                        SELECT ds.id, ds.organization_id
                        FROM data_sources ds
                        JOIN organization_members om ON ds.organization_id = om.organization_id
                        WHERE ds.id = $1 AND om.user_id = $2
                    """, pipeline.data_source_id, user_id)
                    
                    if not access:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="No access to this data source"
                        )
                    
                    # Create pipeline
                    new_pipeline = await conn.fetchrow("""
                        INSERT INTO pipelines (
                            name, description, config, type, schedule,
                            status, health, version, data_source_id,
                            organization_id
                        )
                        VALUES ($1, $2, $3, $4, $5, 'created', 'unknown', '1.0', $6, $7)
                        RETURNING id, name, description, config, type,
                                  schedule, status, health, version,
                                  organization_id, data_source_id,
                                  created_at, updated_at, last_run
                    """, pipeline.name, pipeline.description, pipeline.config.dict(),
                         pipeline.type, pipeline.schedule, pipeline.data_source_id,
                         access["organization_id"])
                    
                    # Initialize pipeline metrics
                    await conn.execute("""
                        INSERT INTO pipeline_metrics (
                            pipeline_id, throughput, latency, error_rate,
                            success_rate, processed_records, failed_records
                        )
                        VALUES ($1, 0, 0, 0, 0, 0, 0)
                    """, new_pipeline["id"])
                    
                    return dict(new_pipeline)
        except DatabaseError as e:
            logger.error(f"Database error creating pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def get_pipeline(
        self, pipeline_id: int, user_id: int
    ) -> Dict[str, Any]:
        """Get a specific pipeline."""
        try:
            async with db_pool.postgres_connection() as conn:
                pipeline = await conn.fetchrow("""
                    SELECT p.id, p.name, p.description, p.config, p.type,
                           p.schedule, p.status, p.health, p.version,
                           p.organization_id, p.data_source_id,
                           p.created_at, p.updated_at, p.last_run
                    FROM pipelines p
                    JOIN data_sources ds ON p.data_source_id = ds.id
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE p.id = $1 AND om.user_id = $2
                """, pipeline_id, user_id)
                
                if not pipeline:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pipeline not found or access denied"
                    )
                
                # Add running status from executor
                pipeline_dict = dict(pipeline)
                pipeline_dict["is_running"] = pipeline_id in pipeline_executor._running_pipelines
                
                return pipeline_dict
        except DatabaseError as e:
            logger.error(f"Database error getting pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def update_pipeline(
        self, pipeline_id: int, pipeline_update: PipelineUpdate, user_id: int
    ) -> Dict[str, Any]:
        """Update a pipeline."""
        try:
            async with db_pool.postgres_connection() as conn:
                async with conn.transaction():
                    # Check access
                    existing = await conn.fetchrow("""
                        SELECT p.id, p.status
                        FROM pipelines p
                        JOIN data_sources ds ON p.data_source_id = ds.id
                        JOIN organization_members om ON ds.organization_id = om.organization_id
                        WHERE p.id = $1 AND om.user_id = $2
                    """, pipeline_id, user_id)
                    
                    if not existing:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Pipeline not found or access denied"
                        )
                    
                    # Validate status transition if status is being updated
                    if pipeline_update.status:
                        self._validate_status_transition(
                            existing["status"], pipeline_update.status
                        )
                        
                        # Handle pipeline execution based on status
                        if pipeline_update.status == PipelineStatus.RUNNING:
                            await pipeline_executor.start_pipeline(pipeline_id)
                        elif pipeline_update.status == PipelineStatus.STOPPED:
                            await pipeline_executor.stop_pipeline(pipeline_id)
                    
                    # Update pipeline
                    update_data = pipeline_update.dict(exclude_unset=True)
                    if update_data:
                        if "config" in update_data:
                            update_data["config"] = update_data["config"].dict()
                        
                        fields = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(update_data.keys()))
                        values = list(update_data.values())
                        query = f"""
                            UPDATE pipelines 
                            SET {fields}, updated_at = CURRENT_TIMESTAMP
                            WHERE id = $1
                            RETURNING id, name, description, config, type,
                                      schedule, status, health, version,
                                      organization_id, data_source_id,
                                      created_at, updated_at, last_run
                        """
                        updated = await conn.fetchrow(query, pipeline_id, *values)
                        
                        # Add running status from executor
                        updated_dict = dict(updated)
                        updated_dict["is_running"] = pipeline_id in pipeline_executor._running_pipelines
                        
                        return updated_dict
                    
                    # If no updates, return current state
                    current = await conn.fetchrow("""
                        SELECT id, name, description, config, type,
                               schedule, status, health, version,
                               organization_id, data_source_id,
                               created_at, updated_at, last_run
                        FROM pipelines
                        WHERE id = $1
                    """, pipeline_id)
                    
                    # Add running status from executor
                    current_dict = dict(current)
                    current_dict["is_running"] = pipeline_id in pipeline_executor._running_pipelines
                    
                    return current_dict
        except DatabaseError as e:
            logger.error(f"Database error updating pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def delete_pipeline(self, pipeline_id: int, user_id: int) -> None:
        """Delete a pipeline."""
        try:
            async with db_pool.postgres_connection() as conn:
                async with conn.transaction():
                    # Check access
                    existing = await conn.fetchrow("""
                        SELECT p.id
                        FROM pipelines p
                        JOIN data_sources ds ON p.data_source_id = ds.id
                        JOIN organization_members om ON ds.organization_id = om.organization_id
                        WHERE p.id = $1 AND om.user_id = $2
                    """, pipeline_id, user_id)
                    
                    if not existing:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Pipeline not found or access denied"
                        )
                    
                    # Stop pipeline if running
                    if pipeline_id in pipeline_executor._running_pipelines:
                        await pipeline_executor.stop_pipeline(pipeline_id)
                    
                    # Delete pipeline metrics
                    await conn.execute("""
                        DELETE FROM pipeline_metrics WHERE pipeline_id = $1
                    """, pipeline_id)
                    
                    # Delete pipeline logs
                    await conn.execute("""
                        DELETE FROM pipeline_logs WHERE pipeline_id = $1
                    """, pipeline_id)
                    
                    # Delete pipeline
                    await conn.execute("""
                        DELETE FROM pipelines WHERE id = $1
                    """, pipeline_id)
        except DatabaseError as e:
            logger.error(f"Database error deleting pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def start_pipeline(
        self, pipeline_id: int, user_id: int
    ) -> PipelineStatusResponse:
        """Start a pipeline."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Check access and get pipeline
                pipeline = await conn.fetchrow("""
                    SELECT p.id, p.status, p.config, p.health
                    FROM pipelines p
                    JOIN data_sources ds ON p.data_source_id = ds.id
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE p.id = $1 AND om.user_id = $2
                """, pipeline_id, user_id)
                
                if not pipeline:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pipeline not found or access denied"
                    )
                
                # Start pipeline execution
                await pipeline_executor.start_pipeline(pipeline_id)
                
                # Get updated status
                return await pipeline_executor.get_pipeline_status(pipeline_id)
        except DatabaseError as e:
            logger.error(f"Database error starting pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def stop_pipeline(
        self, pipeline_id: int, user_id: int
    ) -> PipelineStatusResponse:
        """Stop a pipeline."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Check access and get pipeline
                pipeline = await conn.fetchrow("""
                    SELECT p.id, p.status, p.config, p.health
                    FROM pipelines p
                    JOIN data_sources ds ON p.data_source_id = ds.id
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE p.id = $1 AND om.user_id = $2
                """, pipeline_id, user_id)
                
                if not pipeline:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pipeline not found or access denied"
                    )
                
                # Stop pipeline execution
                await pipeline_executor.stop_pipeline(pipeline_id)
                
                # Get updated status
                return await pipeline_executor.get_pipeline_status(pipeline_id)
        except DatabaseError as e:
            logger.error(f"Database error stopping pipeline: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def get_pipeline_logs(
        self,
        pipeline_id: int,
        user_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> PipelineLogs:
        """Get pipeline logs."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Check access
                access = await conn.fetchrow("""
                    SELECT p.id
                    FROM pipelines p
                    JOIN data_sources ds ON p.data_source_id = ds.id
                    JOIN organization_members om ON ds.organization_id = om.organization_id
                    WHERE p.id = $1 AND om.user_id = $2
                """, pipeline_id, user_id)
                
                if not access:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Pipeline not found or access denied"
                    )
                
                # Build query conditions
                conditions = ["pipeline_id = $1"]
                params = [pipeline_id]
                if start_time:
                    conditions.append(f"timestamp >= ${len(params) + 1}")
                    params.append(start_time)
                if end_time:
                    conditions.append(f"timestamp <= ${len(params) + 1}")
                    params.append(end_time)
                
                where_clause = " AND ".join(conditions)
                
                # Get logs
                logs = await conn.fetch(f"""
                    SELECT timestamp, level, message, details
                    FROM pipeline_logs
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT $%s
                """ % (len(params) + 1), *params, limit)
                
                # Get total count for the time range
                total = await conn.fetchval(f"""
                    SELECT COUNT(*)
                    FROM pipeline_logs
                    WHERE {where_clause}
                """, *params)
                
                return PipelineLogs(
                    logs=[PipelineLog(**dict(log)) for log in logs],
                    start_time=start_time or logs[-1]["timestamp"] if logs else None,
                    end_time=end_time or logs[0]["timestamp"] if logs else None,
                    total_entries=total
                )
        except DatabaseError as e:
            logger.error(f"Database error getting pipeline logs: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    def _validate_status_transition(
        self, current_status: str, new_status: str
    ) -> None:
        """Validate pipeline status transition."""
        valid_transitions = {
            PipelineStatus.CREATED: [
                PipelineStatus.RUNNING,
                PipelineStatus.FAILED
            ],
            PipelineStatus.RUNNING: [
                PipelineStatus.STOPPED,
                PipelineStatus.COMPLETED,
                PipelineStatus.FAILED,
                PipelineStatus.PAUSED
            ],
            PipelineStatus.STOPPED: [
                PipelineStatus.RUNNING,
                PipelineStatus.FAILED
            ],
            PipelineStatus.FAILED: [
                PipelineStatus.RUNNING
            ],
            PipelineStatus.COMPLETED: [
                PipelineStatus.RUNNING
            ],
            PipelineStatus.PAUSED: [
                PipelineStatus.RUNNING,
                PipelineStatus.STOPPED,
                PipelineStatus.FAILED
            ]
        }
        
        if (
            current_status not in valid_transitions or
            new_status not in valid_transitions[current_status]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status} to {new_status}"
            )

    async def get_pipeline_status(self, user_id: int) -> Dict[str, Any]:
        """Get overall pipeline status."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get user's organizations
                org_ids = await conn.fetch("""
                    SELECT organization_id
                    FROM organization_members
                    WHERE user_id = $1
                """, user_id)
                
                if not org_ids:
                    return {
                        "status": "unknown",
                        "pipelines": [],
                        "metrics": {
                            "total": 0,
                            "running": 0,
                            "failed": 0,
                            "completed": 0
                        }
                    }
                
                # Get pipelines for these organizations
                pipelines = await conn.fetch("""
                    SELECT p.id, p.name, p.status, p.health,
                           p.last_run, pm.throughput, pm.error_rate,
                           pm.processed_records, pm.failed_records
                    FROM pipelines p
                    LEFT JOIN pipeline_metrics pm ON p.id = pm.pipeline_id
                    JOIN data_sources ds ON p.data_source_id = ds.id
                    WHERE ds.organization_id = ANY($1::bigint[])
                    ORDER BY p.last_run DESC NULLS LAST
                """, [org["organization_id"] for org in org_ids])
                
                # Calculate metrics
                total = len(pipelines)
                running = sum(1 for p in pipelines if p["status"] == "running")
                failed = sum(1 for p in pipelines if p["status"] == "failed")
                completed = sum(1 for p in pipelines if p["status"] == "completed")
                
                # Calculate overall health
                if total == 0:
                    overall_status = "unknown"
                elif failed > 0:
                    overall_status = "degraded"
                elif running > 0:
                    overall_status = "running"
                else:
                    overall_status = "healthy"
                
                return {
                    "status": overall_status,
                    "pipelines": [dict(p) for p in pipelines],
                    "metrics": {
                        "total": total,
                        "running": running,
                        "failed": failed,
                        "completed": completed,
                        "throughput": sum(p["throughput"] or 0 for p in pipelines),
                        "error_rate": sum(p["error_rate"] or 0 for p in pipelines) / total if total > 0 else 0,
                        "processed_records": sum(p["processed_records"] or 0 for p in pipelines),
                        "failed_records": sum(p["failed_records"] or 0 for p in pipelines)
                    }
                }
                
        except DatabaseError as e:
            logger.error(f"Database error getting pipeline status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def list_components(self) -> List[Dict[str, Any]]:
        """List all pipeline components with their status."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get all pipeline components
                components = await conn.fetch("""
                    SELECT p.id, p.name, p.status, p.health, p.version,
                           p.config, p.description, p.updated_at as last_updated,
                           pm.throughput, pm.latency, pm.error_rate,
                           pm.success_rate, pm.processed_records, pm.failed_records
                    FROM pipelines p
                    LEFT JOIN pipeline_metrics pm ON p.id = pm.pipeline_id
                    ORDER BY p.created_at DESC
                """)
                
                result = []
                for comp in components:
                    metrics = {
                        "throughput": comp["throughput"],
                        "latency": comp["latency"],
                        "error_rate": comp["error_rate"],
                        "success_rate": comp["success_rate"],
                        "processed_records": comp["processed_records"],
                        "failed_records": comp["failed_records"]
                    }
                    
                    result.append({
                        "id": str(comp["id"]),
                        "name": comp["name"],
                        "status": comp["status"],
                        "health": comp["health"],
                        "metrics": metrics,
                        "config": comp["config"],
                        "description": comp["description"],
                        "version": comp["version"],
                        "last_updated": comp["last_updated"]
                    })
                
                return result
        except DatabaseError as e:
            logger.error(f"Database error listing pipeline components: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def list_alerts(self) -> List[Dict[str, Any]]:
        """List all active pipeline alerts."""
        try:
            async with db_pool.postgres_connection() as conn:
                alerts = await conn.fetch("""
                    SELECT id, severity, message, pipeline_id as component_id,
                           created_at as timestamp, resolved
                    FROM pipeline_alerts
                    WHERE resolved = false
                    ORDER BY created_at DESC
                """)
                
                return [dict(alert) for alert in alerts]
        except DatabaseError as e:
            logger.error(f"Database error listing pipeline alerts: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def get_overall_health(self) -> str:
        """Get overall pipeline system health."""
        try:
            async with db_pool.postgres_connection() as conn:
                # Get health stats
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE health = 'healthy') as healthy,
                        COUNT(*) FILTER (WHERE health = 'degraded') as degraded,
                        COUNT(*) FILTER (WHERE health = 'unhealthy') as unhealthy
                    FROM pipelines
                """)
                
                if not stats["total"]:
                    return "unknown"
                
                healthy_ratio = stats["healthy"] / stats["total"]
                degraded_ratio = stats["degraded"] / stats["total"]
                
                if healthy_ratio >= 0.9:
                    return "healthy"
                elif healthy_ratio + degraded_ratio >= 0.7:
                    return "degraded"
                else:
                    return "unhealthy"
        except DatabaseError as e:
            logger.error(f"Database error getting overall health: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    async def get_overall_metrics(self) -> Dict[str, float]:
        """Get aggregated metrics for all pipelines."""
        try:
            async with db_pool.postgres_connection() as conn:
                metrics = await conn.fetchrow("""
                    SELECT 
                        AVG(throughput) as avg_throughput,
                        AVG(latency) as avg_latency,
                        AVG(error_rate) as avg_error_rate,
                        AVG(success_rate) as avg_success_rate,
                        SUM(processed_records) as total_processed,
                        SUM(failed_records) as total_failed
                    FROM pipeline_metrics
                """)
                
                return {
                    "average_throughput": float(metrics["avg_throughput"] or 0),
                    "average_latency": float(metrics["avg_latency"] or 0),
                    "average_error_rate": float(metrics["avg_error_rate"] or 0),
                    "average_success_rate": float(metrics["avg_success_rate"] or 0),
                    "total_processed_records": int(metrics["total_processed"] or 0),
                    "total_failed_records": int(metrics["total_failed"] or 0)
                }
        except DatabaseError as e:
            logger.error(f"Database error getting overall metrics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

# Create singleton instance
pipeline_service = PipelineService() 