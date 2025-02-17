from typing import List, Dict, Any
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Schema definitions
EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    event_id UUID,
    timestamp DateTime,
    event_type LowCardinality(String),
    source LowCardinality(String),
    user_id String,
    organization_id String,
    properties JSON,
    metadata JSON,
    processed_at DateTime,
    _partition_date Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(_partition_date)
ORDER BY (timestamp, event_type, event_id)
TTL timestamp + INTERVAL 3 MONTH;
"""

METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS metrics (
    metric_id UUID,
    timestamp DateTime,
    name LowCardinality(String),
    value Float64,
    labels JSON,
    source LowCardinality(String),
    organization_id String,
    _partition_date Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(_partition_date)
ORDER BY (timestamp, name, metric_id)
TTL timestamp + INTERVAL 6 MONTH;
"""

LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    log_id UUID,
    timestamp DateTime,
    level LowCardinality(String),
    message String,
    source LowCardinality(String),
    service LowCardinality(String),
    organization_id String,
    attributes JSON,
    _partition_date Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(_partition_date)
ORDER BY (timestamp, level, log_id)
TTL timestamp + INTERVAL 1 MONTH;
"""

TRACES_TABLE = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id String,
    span_id String,
    parent_span_id String,
    timestamp DateTime,
    name String,
    duration_ms Float64,
    service LowCardinality(String),
    organization_id String,
    attributes JSON,
    _partition_date Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(_partition_date)
ORDER BY (timestamp, trace_id, span_id)
TTL timestamp + INTERVAL 2 MONTH;
"""

# Views for aggregations
HOURLY_METRICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_metrics
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, name, organization_id)
AS SELECT
    toStartOfHour(timestamp) as hour,
    name,
    organization_id,
    avg(value) as avg_value,
    min(value) as min_value,
    max(value) as max_value,
    count() as sample_count
FROM metrics
GROUP BY hour, name, organization_id;
"""

ERROR_LOGS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS error_logs
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, service)
AS SELECT *
FROM logs
WHERE level IN ('ERROR', 'CRITICAL');
"""

class ClickHouseSchema:
    """Manages ClickHouse schema creation and updates"""
    
    @staticmethod
    async def initialize_schema():
        """Create all required tables and views"""
        from ..database import clickhouse
        
        schemas = [
            EVENTS_TABLE,
            METRICS_TABLE,
            LOGS_TABLE,
            TRACES_TABLE,
            HOURLY_METRICS_VIEW,
            ERROR_LOGS_VIEW
        ]
        
        for schema in schemas:
            try:
                await clickhouse.execute(schema)
                logger.info(f"Successfully created schema: {schema.split('CREATE')[1].split('(')[0]}")
            except Exception as e:
                logger.error(f"Error creating schema: {str(e)}")
                raise
    
    @staticmethod
    async def verify_schema():
        """Verify all required tables and views exist"""
        from ..database import clickhouse
        
        required_objects = [
            "events",
            "metrics",
            "logs",
            "traces",
            "hourly_metrics",
            "error_logs"
        ]
        
        for obj in required_objects:
            query = f"SHOW TABLES LIKE '{obj}'"
            result = await clickhouse.execute(query)
            if not result:
                raise Exception(f"Missing required table/view: {obj}")
        
        logger.info("Schema verification completed successfully") 