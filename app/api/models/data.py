"""
Data models for source and sync operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class SourceType(str, Enum):
    """Type of data source."""
    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"

class DataSource(BaseModel):
    """Data source model."""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Source name")
    type: SourceType = Field(..., description="Source type")
    config: Dict[str, Any] = Field(..., description="Source configuration")
    last_sync_status: Optional[SyncStatus] = Field(None, description="Status of last sync")
    last_sync_error: Optional[str] = Field(None, description="Error from last sync")
    last_sync_started_at: Optional[datetime] = Field(None, description="Start time of last sync")
    last_successful_sync: Optional[datetime] = Field(None, description="Time of last successful sync")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DataSync(BaseModel):
    """Data sync operation model."""
    id: str = Field(..., description="Unique identifier")
    source_id: str = Field(..., description="ID of the data source")
    status: SyncStatus = Field(..., description="Sync status")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

__all__ = ['DataSource', 'DataSync', 'SyncStatus', 'SourceType'] 