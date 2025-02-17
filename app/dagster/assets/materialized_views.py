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
import asyncio
from datetime import datetime, timedelta
import logging
from ...api.services.materialize import materialize_service
from ...api.models.timeseries import MaterializedView, MaterializedAggregation

logger = logging.getLogger(__name__)

# Partition definitions
realtime_partitions = DailyPartitionsDefinition(
    start_date="2024-01-01",
    timezone="UTC"
)

# Freshness policies
realtime_freshness = FreshnessPolicy(
    maximum_lag_minutes=1,
    cron_schedule="* * * * *"  # Check every minute
)

@asset(
    partitions_def=realtime_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "Real-time user activity metrics",
        "category": "real-time",
        "team": "analytics"
    }
)
def user_activity_view(context) -> Output[Dict[str, Any]]:
    """Asset for real-time user activity metrics view."""
    view = MaterializedView(
        name="mv_user_activity_realtime",
        query="""
        SELECT
            date_trunc('minute', timestamp) as minute,
            platform,
            event_type,
            count(*) as event_count,
            count(distinct user_id) as unique_users,
            count(distinct session_id) as unique_sessions
        FROM user_interaction_events
        WHERE timestamp >= now() - interval '1 hour'
        GROUP BY minute, platform, event_type
        """,
        refresh_interval="1 minute",
        partition_key="minute",
        indexes=["minute", "platform", "event_type"],
        cluster_key="minute_idx"
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        {"view_name": view.name},
        metadata={
            "refresh_interval": "1 minute",
            "indexes": view.indexes,
            "partition_key": view.partition_key
        }
    )

@asset(
    partitions_def=realtime_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "Real-time performance metrics",
        "category": "real-time",
        "team": "engineering"
    }
)
def performance_metrics_view(context) -> Output[Dict[str, Any]]:
    """Asset for real-time performance metrics view."""
    view = MaterializedView(
        name="mv_performance_realtime",
        query="""
        SELECT
            date_trunc('minute', timestamp) as minute,
            service,
            endpoint,
            avg(duration) as avg_duration,
            percentile_cont(0.95) within group (order by duration) as p95_duration,
            count(*) as request_count,
            count(*) filter (where status >= 500) as error_count
        FROM performance_events
        WHERE timestamp >= now() - interval '1 hour'
        GROUP BY minute, service, endpoint
        """,
        refresh_interval="30 seconds",
        partition_key="minute",
        indexes=["minute", "service", "endpoint"],
        cluster_key="minute_idx"
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        {"view_name": view.name},
        metadata={
            "refresh_interval": "30 seconds",
            "indexes": view.indexes,
            "partition_key": view.partition_key
        }
    )

@asset(
    partitions_def=realtime_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "Real-time infrastructure metrics",
        "category": "real-time",
        "team": "operations"
    }
)
def infrastructure_metrics_view(context) -> Output[Dict[str, Any]]:
    """Asset for real-time infrastructure metrics view."""
    view = MaterializedView(
        name="mv_infrastructure_realtime",
        query="""
        SELECT
            date_trunc('minute', timestamp) as minute,
            resource_type,
            region,
            avg(cpu_usage) as avg_cpu,
            max(cpu_usage) as max_cpu,
            avg(memory_usage) as avg_memory,
            max(memory_usage) as max_memory,
            sum(cost_per_hour) as total_cost
        FROM infrastructure_metrics
        WHERE timestamp >= now() - interval '1 hour'
        GROUP BY minute, resource_type, region
        """,
        refresh_interval="1 minute",
        partition_key="minute",
        indexes=["minute", "resource_type", "region"],
        cluster_key="minute_idx"
    )
    
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        {"view_name": view.name},
        metadata={
            "refresh_interval": "1 minute",
            "indexes": view.indexes,
            "partition_key": view.partition_key
        }
    )

@asset(
    partitions_def=realtime_partitions,
    freshness_policy=realtime_freshness,
    metadata={
        "description": "View optimization and maintenance",
        "category": "maintenance",
        "team": "platform"
    }
)
def optimize_views(context) -> Output[Dict[str, Any]]:
    """Asset for optimizing all materialized views."""
    # Run view optimization
    asyncio.run(materialize_service.optimize_views())
    
    # Get optimization results
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "views_optimized": len(materialize_service._views),
        "next_optimization": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    
    return Output(
        results,
        metadata={
            "views_count": len(materialize_service._views),
            "last_optimization": results["timestamp"],
            "next_optimization": results["next_optimization"]
        }
    ) 