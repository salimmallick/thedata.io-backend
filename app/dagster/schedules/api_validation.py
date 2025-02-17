from dagster import schedule, RunRequest, DefaultScheduleStatus
from datetime import datetime
from ..jobs.api_validation import validate_api

@schedule(
    job=validate_api,
    cron_schedule="*/5 * * * *",  # Run every 5 minutes
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="UTC"
)
def api_validation_schedule(context):
    """Schedule for regular API validation."""
    return RunRequest(
        run_key=f"api_validation_{datetime.utcnow().isoformat()}",
        tags={"type": "validation", "target": "apis"}
    ) 