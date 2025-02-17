from dagster import (
    asset,
    AssetIn,
    MetadataValue,
    Output,
    DailyPartitionsDefinition,
    TimeWindowPartitionMapping
)
from ...api.models.timeseries import (
    MetricData,
    EventData,
    MaterializedView,
    MaterializedAggregation,
    TimeWindow
)
from ...api.services.materialize import materialize_service
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

# Partition definition for daily data processing
daily_partitions = DailyPartitionsDefinition(
    start_date="2024-01-01",  # Adjust based on your needs
)

@asset(
    partitions_def=daily_partitions,
    metadata={
        "description": "Raw metrics data from various sources",
        "schema": MetricData.schema()
    }
)
def raw_metrics(context) -> Output[pd.DataFrame]:
    """Asset representing raw metrics data."""
    # This would typically read from QuestDB for the partition's time range
    partition_date = context.partition_key
    
    # Example query to QuestDB
    query = f"""
    SELECT *
    FROM metrics
    WHERE timestamp >= '{partition_date}'
    AND timestamp < dateadd('d', 1, '{partition_date}')
    """
    
    # TODO: Implement actual QuestDB query
    # For now, return example data
    df = pd.DataFrame({
        'timestamp': pd.date_range(partition_date, periods=24, freq='H'),
        'name': ['example_metric'] * 24,
        'value': np.random.randn(24)
    })
    
    return Output(
        df,
        metadata={
            "num_records": len(df),
            "preview": MetadataValue.md(df.head().to_markdown())
        }
    )

@asset(
    partitions_def=daily_partitions,
    metadata={
        "description": "Raw events data from various sources",
        "schema": EventData.schema()
    }
)
def raw_events(context) -> Output[pd.DataFrame]:
    """Asset representing raw events data."""
    partition_date = context.partition_key
    
    # Example query to QuestDB
    query = f"""
    SELECT *
    FROM events
    WHERE timestamp >= '{partition_date}'
    AND timestamp < dateadd('d', 1, '{partition_date}')
    """
    
    # TODO: Implement actual QuestDB query
    df = pd.DataFrame({
        'timestamp': pd.date_range(partition_date, periods=24, freq='H'),
        'name': ['example_event'] * 24,
        'event_type': ['system'] * 24,
        'severity': ['info'] * 24
    })
    
    return Output(
        df,
        metadata={
            "num_records": len(df),
            "preview": MetadataValue.md(df.head().to_markdown())
        }
    )

@asset(
    ins={
        "raw_metrics": AssetIn(
            partition_mapping=TimeWindowPartitionMapping(
                start_offset=-1,  # Previous day
                end_offset=0      # Current day
            )
        )
    },
    metadata={
        "description": "Hourly aggregated metrics",
    }
)
def hourly_metrics(context, raw_metrics: pd.DataFrame) -> Output[pd.DataFrame]:
    """Asset representing hourly aggregated metrics."""
    # Compute hourly aggregations
    hourly = raw_metrics.groupby(
        [pd.Grouper(key='timestamp', freq='H'), 'name']
    ).agg({
        'value': ['mean', 'min', 'max', 'count']
    }).reset_index()
    
    # Create materialized view in Materialize
    view = MaterializedView(
        name=f"hourly_metrics_{context.partition_key}",
        query=f"""
        SELECT
            timestamp_bin('1 hour', timestamp) as hour,
            name,
            avg(value) as avg_value,
            min(value) as min_value,
            max(value) as max_value,
            count(*) as sample_count
        FROM raw_metrics
        WHERE timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY hour, name
        """
    )
    
    # Use asyncio to create the view
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        hourly,
        metadata={
            "num_records": len(hourly),
            "preview": MetadataValue.md(hourly.head().to_markdown()),
            "materialized_view": view.name
        }
    )

@asset(
    ins={
        "raw_events": AssetIn(
            partition_mapping=TimeWindowPartitionMapping(
                start_offset=-1,  # Previous day
                end_offset=0      # Current day
            )
        )
    },
    metadata={
        "description": "Error events detection and aggregation",
    }
)
def error_events(context, raw_events: pd.DataFrame) -> Output[pd.DataFrame]:
    """Asset representing error event detection and aggregation."""
    # Filter and aggregate error events
    errors = raw_events[raw_events['severity'] == 'error'].copy()
    error_counts = errors.groupby(
        [pd.Grouper(key='timestamp', freq='5T'), 'name']
    ).size().reset_index(name='error_count')
    
    # Create materialized view for error detection
    view = MaterializedView(
        name=f"error_events_{context.partition_key}",
        query=f"""
        SELECT
            timestamp_bin('5 minutes', timestamp) as window,
            name,
            count(*) as error_count
        FROM raw_events
        WHERE severity = 'error'
        AND timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY window, name
        HAVING count(*) > 5
        """
    )
    
    # Use asyncio to create the view
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        error_counts,
        metadata={
            "num_records": len(error_counts),
            "preview": MetadataValue.md(error_counts.head().to_markdown()),
            "materialized_view": view.name
        }
    )

@asset(
    ins={
        "hourly_metrics": AssetIn(),
        "error_events": AssetIn()
    },
    metadata={
        "description": "Daily summary combining metrics and events",
    }
)
def daily_summary(
    context,
    hourly_metrics: pd.DataFrame,
    error_events: pd.DataFrame
) -> Output[Dict[str, Any]]:
    """Asset representing daily summary of metrics and events."""
    # Compute daily statistics
    daily_stats = {
        "date": context.partition_key,
        "total_metrics": len(hourly_metrics),
        "total_errors": len(error_events),
        "metrics_summary": hourly_metrics['value'].describe().to_dict(),
        "error_patterns": error_events.groupby('name')['error_count'].sum().to_dict()
    }
    
    # Create materialized view for daily summary
    view = MaterializedView(
        name=f"daily_summary_{context.partition_key}",
        query=f"""
        SELECT
            date_trunc('day', timestamp) as day,
            count(*) as total_metrics,
            avg(value) as avg_value,
            min(value) as min_value,
            max(value) as max_value
        FROM raw_metrics
        WHERE timestamp >= '{context.partition_key}'
        AND timestamp < dateadd('d', 1, '{context.partition_key}')
        GROUP BY day
        """
    )
    
    # Use asyncio to create the view
    asyncio.run(materialize_service.create_materialized_view(view))
    
    return Output(
        daily_stats,
        metadata={
            "date": context.partition_key,
            "metrics_count": daily_stats["total_metrics"],
            "errors_count": daily_stats["total_errors"],
            "materialized_view": view.name
        }
    ) 