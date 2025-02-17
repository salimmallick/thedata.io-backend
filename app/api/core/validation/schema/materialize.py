from typing import List, Dict, Any
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Schema definitions for real-time analytics
REAL_TIME_METRICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS rt_metrics AS
SELECT
    timestamp,
    name,
    value,
    labels,
    organization_id,
    source,
    toStartOfMinute(timestamp) as minute,
    avg(value) OVER (
        PARTITION BY name, organization_id
        ORDER BY timestamp
        ROWS BETWEEN 60 PRECEDING AND CURRENT ROW
    ) as moving_avg_1m,
    avg(value) OVER (
        PARTITION BY name, organization_id
        ORDER BY timestamp
        ROWS BETWEEN 300 PRECEDING AND CURRENT ROW
    ) as moving_avg_5m
FROM metrics
WHERE timestamp >= now() - INTERVAL '1 hour';
"""

EVENT_ANALYTICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS rt_events AS
SELECT
    timestamp,
    event_type,
    source,
    organization_id,
    count(*) as event_count,
    count(DISTINCT user_id) as unique_users,
    toStartOfMinute(timestamp) as minute
FROM events
WHERE timestamp >= now() - INTERVAL '1 hour'
GROUP BY
    minute,
    event_type,
    source,
    organization_id;
"""

ERROR_ANALYTICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS rt_errors AS
SELECT
    timestamp,
    level,
    service,
    organization_id,
    count(*) as error_count,
    array_agg(message) as error_messages,
    toStartOfMinute(timestamp) as minute
FROM logs
WHERE 
    level IN ('ERROR', 'CRITICAL') 
    AND timestamp >= now() - INTERVAL '1 hour'
GROUP BY
    minute,
    level,
    service,
    organization_id;
"""

TRACE_ANALYTICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS rt_traces AS
SELECT
    timestamp,
    service,
    name as operation,
    organization_id,
    avg(duration_ms) as avg_duration,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration,
    count(*) as operation_count,
    toStartOfMinute(timestamp) as minute
FROM traces
WHERE timestamp >= now() - INTERVAL '1 hour'
GROUP BY
    minute,
    service,
    operation,
    organization_id;
"""

API_ANALYTICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS rt_api_metrics AS
SELECT
    timestamp,
    endpoint,
    method,
    organization_id,
    avg(duration_ms) as avg_duration,
    count(*) as request_count,
    count(*) FILTER (WHERE status_code >= 400) as error_count,
    count(DISTINCT client_ip) as unique_clients,
    toStartOfMinute(timestamp) as minute
FROM api_metrics
WHERE timestamp >= now() - INTERVAL '1 hour'
GROUP BY
    minute,
    endpoint,
    method,
    organization_id;
"""

TRANSFORMATION_ANALYTICS_VIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS rt_transformations AS
SELECT
    timestamp,
    rule_name,
    rule_type,
    avg(duration_ms) as avg_duration,
    sum(input_size) as total_input_size,
    sum(output_size) as total_output_size,
    count(*) as transformation_count,
    count(*) FILTER (WHERE success = false) as error_count,
    toStartOfMinute(timestamp) as minute
FROM transformation_metrics
WHERE timestamp >= now() - INTERVAL '1 hour'
GROUP BY
    minute,
    rule_name,
    rule_type;
"""

# Sink configurations for real-time alerts
ALERT_SINKS = """
-- Error rate alert sink
CREATE SINK IF NOT EXISTS error_rate_alerts
FROM (
    SELECT
        minute,
        organization_id,
        error_count,
        request_count,
        (error_count::float / NULLIF(request_count, 0)) as error_rate
    FROM rt_api_metrics
    WHERE (error_count::float / NULLIF(request_count, 0)) > 0.1
)
INTO kafka_broker ('alerts')
WITH (
    kafka_topic = 'error_rate_alerts',
    consistency = 'at_least_once'
);

-- High latency alert sink
CREATE SINK IF NOT EXISTS latency_alerts
FROM (
    SELECT
        minute,
        endpoint,
        organization_id,
        avg_duration
    FROM rt_api_metrics
    WHERE avg_duration > 1000  -- 1 second threshold
)
INTO kafka_broker ('alerts')
WITH (
    kafka_topic = 'latency_alerts',
    consistency = 'at_least_once'
);
"""

class MaterializeSchema:
    """Manages Materialize schema creation and updates"""
    
    @staticmethod
    async def initialize_schema():
        """Create all required materialized views and sinks"""
        from ..database import materialize
        
        views = [
            REAL_TIME_METRICS_VIEW,
            EVENT_ANALYTICS_VIEW,
            ERROR_ANALYTICS_VIEW,
            TRACE_ANALYTICS_VIEW,
            API_ANALYTICS_VIEW,
            TRANSFORMATION_ANALYTICS_VIEW
        ]
        
        # Create views
        for view in views:
            try:
                await materialize.execute(view)
                logger.info(f"Successfully created view: {view.split('CREATE')[1].split('AS')[0]}")
            except Exception as e:
                logger.error(f"Error creating view: {str(e)}")
                raise
        
        # Create alert sinks
        try:
            await materialize.execute(ALERT_SINKS)
            logger.info("Successfully created alert sinks")
        except Exception as e:
            logger.error(f"Error creating alert sinks: {str(e)}")
            raise
    
    @staticmethod
    async def verify_schema():
        """Verify all required views and sinks exist"""
        from ..database import materialize
        
        required_objects = [
            "rt_metrics",
            "rt_events",
            "rt_errors",
            "rt_traces",
            "rt_api_metrics",
            "rt_transformations",
            "error_rate_alerts",
            "latency_alerts"
        ]
        
        for obj in required_objects:
            try:
                result = await materialize.execute(f"SHOW MATERIALIZED VIEWS LIKE '{obj}'")
                if not result and not await materialize.execute(f"SHOW SINKS LIKE '{obj}'"):
                    raise Exception(f"Missing required object: {obj}")
            except Exception as e:
                logger.error(f"Error verifying object {obj}: {str(e)}")
                raise
        
        logger.info("Schema verification completed successfully") 