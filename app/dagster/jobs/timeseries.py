from dagster import (
    job,
    schedule,
    ScheduleDefinition,
    DefaultScheduleStatus,
    RunRequest,
    define_asset_job,
    AssetSelection
)
from datetime import datetime, timedelta
from ..assets.timeseries import (
    raw_metrics,
    raw_events,
    hourly_metrics,
    error_events,
    daily_summary
)

# Define asset jobs
daily_processing = define_asset_job(
    name="daily_processing",
    selection=AssetSelection.all(),
    description="Process all time-series data for the previous day"
)

# Define schedules
@schedule(
    job=daily_processing,
    cron_schedule="0 1 * * *",  # Run at 1 AM every day
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="UTC"
)
def daily_processing_schedule(context):
    """Schedule for daily data processing."""
    # Process previous day's data
    date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return RunRequest(
        run_key=f"daily_processing_{date}",
        run_config={
            "ops": {
                "raw_metrics": {"config": {"date": date}},
                "raw_events": {"config": {"date": date}},
            }
        },
        tags={"date": date}
    )

# Define real-time processing job
realtime_processing = define_asset_job(
    name="realtime_processing",
    selection=AssetSelection.keys(
        "hourly_metrics",
        "error_events"
    ),
    description="Real-time processing job that runs continuously"
)

# Define cleanup job
cleanup_old_data = define_asset_job(
    name="cleanup_old_data",
    selection=AssetSelection.all(),
    description="Job to clean up old data and maintain system health"
)

# Define monitoring job
monitor_data_quality = define_asset_job(
    name="monitor_data_quality",
    selection=AssetSelection.all(),
    description="Job to monitor data quality and system health"
)

# Schedule definitions
daily_cleanup = ScheduleDefinition(
    job=cleanup_old_data,
    cron_schedule="0 2 * * *",  # Run at 2 AM every day
    default_status=DefaultScheduleStatus.RUNNING
)

hourly_monitoring = ScheduleDefinition(
    job=monitor_data_quality,
    cron_schedule="0 * * * *",  # Run every hour
    default_status=DefaultScheduleStatus.RUNNING
) 