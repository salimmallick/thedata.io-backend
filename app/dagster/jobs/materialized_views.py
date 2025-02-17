from dagster import (
    job,
    schedule,
    ScheduleDefinition,
    DefaultScheduleStatus,
    RunRequest,
    define_asset_job,
    AssetSelection,
    Definitions,
    AssetKey
)
from datetime import datetime, timedelta

# Define asset jobs for different view categories
realtime_views = define_asset_job(
    name="realtime_views",
    selection=AssetSelection.keys(
        AssetKey("user_activity_view"),
        AssetKey("performance_metrics_view"),
        AssetKey("infrastructure_metrics_view")
    ),
    description="Manage and refresh real-time materialized views"
)

view_optimization = define_asset_job(
    name="view_optimization",
    selection=AssetSelection.keys(AssetKey("optimize_views")),
    description="Optimize materialized views and perform maintenance"
)

# Schedule for real-time view management
@schedule(
    job=realtime_views,
    cron_schedule="* * * * *",  # Run every minute
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="UTC"
)
def realtime_views_schedule(context):
    """Schedule for managing real-time materialized views."""
    return RunRequest(
        run_key=f"realtime_views_{datetime.utcnow().isoformat()}",
        tags={"category": "real-time"}
    )

# Schedule for view optimization
@schedule(
    job=view_optimization,
    cron_schedule="0 * * * *",  # Run every hour
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="UTC"
)
def view_optimization_schedule(context):
    """Schedule for optimizing materialized views."""
    return RunRequest(
        run_key=f"view_optimization_{datetime.utcnow().isoformat()}",
        tags={"category": "maintenance"}
    )

# Export all components
__all__ = [
    'realtime_views',
    'view_optimization',
    'realtime_views_schedule',
    'view_optimization_schedule'
] 