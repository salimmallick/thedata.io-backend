from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class DataType(str, Enum):
    METRIC = "metric"
    EVENT = "event"
    LOG = "log"
    TRACE = "trace"

class DataSource(str, Enum):
    API = "api"
    SYSTEM = "system"
    APPLICATION = "application"
    CUSTOM = "custom"

class TimeseriesData(BaseModel):
    """Base model for all time-series data"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: DataType
    source: DataSource
    name: str
    value: float
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MetricData(TimeseriesData):
    """Specific model for metric data"""
    type: DataType = DataType.METRIC
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

class EventData(TimeseriesData):
    """Specific model for event data"""
    type: DataType = DataType.EVENT
    event_type: str
    severity: str = "info"
    description: Optional[str] = None

class MaterializedView(BaseModel):
    """Model for defining materialized views"""
    name: str
    query: str
    refresh_interval: Optional[str] = None  # e.g., '1 minute', '5 minutes'
    dependencies: List[str] = []
    description: Optional[str] = None

class AggregationType(str, Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    DISTINCT_COUNT = "distinct_count"
    PERCENTILE = "percentile"

class TimeWindow(str, Enum):
    MINUTE = "1 minute"
    FIVE_MINUTES = "5 minutes"
    FIFTEEN_MINUTES = "15 minutes"
    HOUR = "1 hour"
    DAY = "1 day"

class MaterializedAggregation(BaseModel):
    """Model for defining real-time aggregations"""
    name: str
    metric_name: str
    aggregation_type: AggregationType
    window: TimeWindow
    group_by: List[str] = []
    filters: Dict[str, Any] = Field(default_factory=dict)
    having: Optional[Dict[str, Any]] = None 