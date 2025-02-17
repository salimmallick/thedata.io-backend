from dagster import schedule, RunRequest, DefaultScheduleStatus
from datetime import datetime
from ..jobs.database_validation import validate_databases

@schedule(
    job=validate_databases,
    cron_schedule="*/5 * * * *",  # Run every 5 minutes
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="UTC"
)
def database_validation_schedule(context):
    """Schedule for regular database validation."""
    return RunRequest(
        run_key=f"database_validation_{datetime.utcnow().isoformat()}",
        tags={"type": "validation", "target": "databases"}
    ) 