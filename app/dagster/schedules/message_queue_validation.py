from dagster import schedule, RunRequest, DefaultScheduleStatus
from datetime import datetime
from ..jobs.message_queue_validation import validate_message_queue

@schedule(
    job=validate_message_queue,
    cron_schedule="*/5 * * * *",  # Run every 5 minutes
    default_status=DefaultScheduleStatus.RUNNING,
    execution_timezone="UTC"
)
def message_queue_validation_schedule(context):
    """Schedule for regular message queue validation."""
    return RunRequest(
        run_key=f"message_queue_validation_{datetime.utcnow().isoformat()}",
        tags={"type": "validation", "target": "message_queues"}
    ) 