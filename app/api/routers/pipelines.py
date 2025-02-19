"""
Pipelines router.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status
from datetime import datetime
from ..models.pipeline import (
    Pipeline, PipelineCreate, PipelineUpdate,
    PipelineStatus, PipelineLogs
)
from ..core.auth.security import get_current_user_token
from ..services.pipeline import pipeline_service

router = APIRouter(tags=["Pipelines"])

@router.get("/")
async def list_pipelines(current_user: Dict[str, Any] = Depends(get_current_user_token)):
    """List all pipelines."""
    return await pipeline_service.list_pipelines(current_user["id"])

@router.post("", response_model=Pipeline, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    pipeline: PipelineCreate,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Create a new pipeline."""
    return await pipeline_service.create_pipeline(pipeline, current_user["id"])

@router.get("/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(
    pipeline_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Get a specific pipeline."""
    return await pipeline_service.get_pipeline(pipeline_id, current_user["id"])

@router.put("/{pipeline_id}", response_model=Pipeline)
async def update_pipeline(
    pipeline_id: int,
    pipeline_update: PipelineUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Update a pipeline."""
    return await pipeline_service.update_pipeline(
        pipeline_id, pipeline_update, current_user["id"]
    )

@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> None:
    """Delete a pipeline."""
    await pipeline_service.delete_pipeline(pipeline_id, current_user["id"])

@router.post("/{pipeline_id}/start", response_model=PipelineStatus)
async def start_pipeline(
    pipeline_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Start a pipeline."""
    return await pipeline_service.start_pipeline(pipeline_id, current_user["id"])

@router.post("/{pipeline_id}/stop", response_model=PipelineStatus)
async def stop_pipeline(
    pipeline_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Stop a pipeline."""
    return await pipeline_service.stop_pipeline(pipeline_id, current_user["id"])

@router.get("/{pipeline_id}/logs", response_model=PipelineLogs)
async def get_pipeline_logs(
    pipeline_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """Get pipeline logs."""
    return await pipeline_service.get_pipeline_logs(
        pipeline_id,
        current_user["id"],
        start_time=start_time,
        end_time=end_time,
        limit=limit
    ) 