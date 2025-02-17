from dagster import (
    asset,
    AssetIn,
    MetadataValue,
    Output,
    DailyPartitionsDefinition,
    TimeWindowPartitionMapping,
    FreshnessPolicy
)
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging
from ...api.services.materialize import materialize_service

logger = logging.getLogger(__name__)

# Partition definition for hourly and daily processing
hourly_partitions = DailyPartitionsDefinition(
    start_date="2024-01-01",
    timezone="UTC"
)

# Freshness policies
realtime_freshness = FreshnessPolicy(
    maximum_lag_minutes=5,
    cron_schedule="*/5 * * * *"  # Check every 5 minutes
)

hourly_freshness = FreshnessPolicy(
    maximum_lag_minutes=60,
    cron_schedule="0 * * * *"  # Check every hour
)

@asset(
    partitions_def=hourly_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "User interaction events from all platforms",
        "category": "events",
        "team": "product"
    }
)
def user_interactions(context) -> Output[pd.DataFrame]:
    """Process user interaction events."""
    query = f"""
    SELECT *
    FROM user_interaction_events
    WHERE timestamp >= toDateTime('{context.partition_key}')
    AND timestamp < toDateTime('{context.partition_key}') + INTERVAL 1 DAY
    """
    
    # TODO: Implement actual ClickHouse query
    df = pd.DataFrame()  # Placeholder
    
    # Create materialized view for real-time analytics
    view = MaterializedView(
        name=f"user_interactions_{context.partition_key}",
        query=f"""
        SELECT
            timestamp_bin('5 minutes', timestamp) as window,
            platform,
            event_type,
            count(*) as event_count,
            count(distinct session_id) as unique_sessions,
            count(distinct user_id) as unique_users
        FROM user_interaction_events
        WHERE timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY window, platform, event_type
        """
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        df,
        metadata={
            "row_count": len(df),
            "materialized_view": view.name
        }
    )

@asset(
    partitions_def=hourly_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "Performance events and metrics",
        "category": "performance",
        "team": "engineering"
    }
)
def performance_metrics(context) -> Output[pd.DataFrame]:
    """Process performance events and metrics."""
    query = f"""
    SELECT *
    FROM performance_events
    WHERE timestamp >= toDateTime('{context.partition_key}')
    AND timestamp < toDateTime('{context.partition_key}') + INTERVAL 1 DAY
    """
    
    # TODO: Implement actual ClickHouse query
    df = pd.DataFrame()  # Placeholder
    
    # Create materialized view for performance monitoring
    view = MaterializedView(
        name=f"performance_metrics_{context.partition_key}",
        query=f"""
        SELECT
            timestamp_bin('1 minute', timestamp) as window,
            category,
            measurements.name,
            avg(measurements.value) as avg_value,
            min(measurements.value) as min_value,
            max(measurements.value) as max_value,
            percentile_cont(0.95) within group (order by measurements.value) as p95
        FROM performance_events
        WHERE timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY window, category, measurements.name
        """
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        df,
        metadata={
            "row_count": len(df),
            "materialized_view": view.name
        }
    )

@asset(
    partitions_def=hourly_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "Video playback analytics",
        "category": "video",
        "team": "video-engineering"
    }
)
def video_analytics(context) -> Output[pd.DataFrame]:
    """Process video analytics events."""
    query = f"""
    SELECT *
    FROM video_events
    WHERE timestamp >= toDateTime('{context.partition_key}')
    AND timestamp < toDateTime('{context.partition_key}') + INTERVAL 1 DAY
    """
    
    # TODO: Implement actual ClickHouse query
    df = pd.DataFrame()  # Placeholder
    
    # Create materialized view for video quality monitoring
    view = MaterializedView(
        name=f"video_quality_{context.partition_key}",
        query=f"""
        SELECT
            timestamp_bin('1 minute', timestamp) as window,
            video_id,
            player_type,
            avg(quality_metrics.video_quality_score) as avg_quality_score,
            avg(quality_metrics.buffering_ratio) as avg_buffering_ratio,
            avg(measurements.startup_time) as avg_startup_time,
            count(*) filter (where event_name = 'error') as error_count
        FROM video_events
        WHERE timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY window, video_id, player_type
        """
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        df,
        metadata={
            "row_count": len(df),
            "materialized_view": view.name
        }
    )

@asset(
    partitions_def=hourly_partitions,
    freshness_policy=hourly_freshness,
    metadata={
        "description": "Infrastructure and cost analytics",
        "category": "infrastructure",
        "team": "operations"
    }
)
def infrastructure_analytics(context) -> Output[Dict[str, Any]]:
    """Process infrastructure metrics and cost data."""
    query = f"""
    SELECT
        resource_type,
        provider,
        region,
        avg(measurements.cpu_usage) as avg_cpu,
        avg(measurements.memory_usage) as avg_memory,
        sum(cost_data.cost_per_hour) as total_cost
    FROM infrastructure_metrics
    WHERE timestamp >= toDateTime('{context.partition_key}')
    AND timestamp < toDateTime('{context.partition_key}') + INTERVAL 1 DAY
    GROUP BY resource_type, provider, region
    """
    
    # TODO: Implement actual ClickHouse query
    results = {}  # Placeholder
    
    # Create materialized view for cost monitoring
    view = MaterializedView(
        name=f"infrastructure_costs_{context.partition_key}",
        query=f"""
        SELECT
            timestamp_bin('1 hour', timestamp) as window,
            resource_type,
            provider,
            region,
            sum(cost_data.cost_per_hour) as hourly_cost,
            avg(measurements.cpu_usage) as avg_cpu_usage,
            avg(measurements.memory_usage) as avg_memory_usage
        FROM infrastructure_metrics
        WHERE timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY window, resource_type, provider, region
        """
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        results,
        metadata={
            "materialized_view": view.name,
            "cost_centers": list(results.keys()) if results else []
        }
    ) 