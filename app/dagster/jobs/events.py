from dagster import (
    job,
    schedule,
    ScheduleDefinition,
    DefaultScheduleStatus,
    RunRequest,
    define_asset_job,
    AssetSelection,
    Definitions,
    sensor,
    AssetKey,
    RetryRequested,
    Failure
)
from datetime import datetime, timedelta
from ..assets.events import (
    user_interactions,
    performance_metrics,
    video_analytics,
    infrastructure_analytics
)
from statistics import mean, stdev
from ..utils.metrics import get_performance_metrics, get_video_metrics
from functools import wraps

# Error handling decorator
def handle_errors(max_retries=3, retry_delay=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                context = args[0] if args else None
                if not context:
                    raise Failure(description=str(e))
                
                retry_count = context.retry_number if hasattr(context, 'retry_number') else 0
                if retry_count < max_retries:
                    raise RetryRequested(
                        max_retries=max_retries,
                        seconds_to_wait=retry_delay
                    )
                raise Failure(description=str(e))
        return wrapper
    return decorator

# Define asset jobs for different teams
product_analytics = define_asset_job(
    name="product_analytics",
    selection=AssetSelection.keys(AssetKey("user_interactions")).upstream(),
    description="Process user interaction events and generate product analytics"
)

engineering_metrics = define_asset_job(
    name="engineering_metrics",
    selection=AssetSelection.keys(AssetKey("performance_metrics")).upstream(),
    description="Process performance events and generate engineering metrics"
)

video_metrics = define_asset_job(
    name="video_metrics",
    selection=AssetSelection.keys(AssetKey("video_analytics")).upstream(),
    description="Process video events and generate quality metrics"
)

infrastructure_metrics = define_asset_job(
    name="infrastructure_metrics",
    selection=AssetSelection.keys(AssetKey("infrastructure_analytics")).upstream(),
    description="Process infrastructure events and generate cost analytics"
)

# Schedule functions
@handle_errors()
def _product_analytics_schedule(context):
    """Schedule for processing product analytics."""
    # Process last 5 minutes of data
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    return RunRequest(
        run_key=None,
        run_config={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )

product_analytics_schedule = ScheduleDefinition(
    name="product_analytics_schedule",
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    job=product_analytics,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
    run_config_fn=_product_analytics_schedule
)

# Engineering metrics schedule
@handle_errors()
def _engineering_metrics_schedule(context):
    """Schedule for processing engineering metrics."""
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    return RunRequest(
        run_key=None,
        run_config={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )

engineering_metrics_schedule = ScheduleDefinition(
    name="engineering_metrics_schedule",
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    job=engineering_metrics,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
    run_config_fn=_engineering_metrics_schedule
)

# Video metrics schedule
@handle_errors()
def _video_metrics_schedule(context):
    """Schedule for processing video metrics."""
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    return RunRequest(
        run_key=None,
        run_config={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )

video_metrics_schedule = ScheduleDefinition(
    name="video_metrics_schedule",
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    job=video_metrics,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
    run_config_fn=_video_metrics_schedule
)

# Infrastructure metrics schedule
@handle_errors()
def _infrastructure_metrics_schedule(context):
    """Schedule for processing infrastructure metrics."""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    return RunRequest(
        run_key=None,
        run_config={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )

infrastructure_metrics_schedule = ScheduleDefinition(
    name="infrastructure_metrics_schedule",
    cron_schedule="0 * * * *",  # Every hour
    job=infrastructure_metrics,
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
    run_config_fn=_infrastructure_metrics_schedule
)

# Define sensors for data quality monitoring
@sensor(job=engineering_metrics)
def performance_anomaly_sensor(context):
    """Sensor to detect performance anomalies."""
    # Get last hour's metrics
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    metrics = get_performance_metrics(start_time, end_time)
    
    # Calculate z-scores for key metrics
    for metric_name, values in metrics.items():
        if len(values) < 2:
            continue
            
        avg = mean(values)
        std = stdev(values)
        latest = values[-1]
        
        if std > 0:
            z_score = abs(latest - avg) / std
            # Alert if z-score > 3 (99.7% confidence interval)
            if z_score > 3:
                return RunRequest(
                    run_key=f"anomaly_{metric_name}_{end_time.strftime('%Y%m%d_%H%M')}",
                    run_config={
                        "ops": {
                            "performance_metrics": {
                                "config": {
                                    "start_time": start_time.isoformat(),
                                    "end_time": end_time.isoformat(),
                                    "alert": {
                                        "metric": metric_name,
                                        "value": latest,
                                        "threshold": z_score
                                    }
                                }
                            }
                        }
                    }
                )
    return None

@sensor(job=video_metrics)
def video_quality_sensor(context):
    """Sensor to detect video quality issues."""
    # Get last 15 minutes of metrics
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=15)
    metrics = get_video_metrics(start_time, end_time)
    
    # Define thresholds
    THRESHOLDS = {
        "buffering_ratio": 0.1,  # 10% buffering
        "startup_time": 3000,    # 3 seconds
        "error_rate": 0.05       # 5% errors
    }
    
    for metric_name, threshold in THRESHOLDS.items():
        if metric_name in metrics:
            value = metrics[metric_name]
            if value > threshold:
                return RunRequest(
                    run_key=f"video_quality_{metric_name}_{end_time.strftime('%Y%m%d_%H%M')}",
                    run_config={
                        "ops": {
                            "video_analytics": {
                                "config": {
                                    "start_time": start_time.isoformat(),
                                    "end_time": end_time.isoformat(),
                                    "alert": {
                                        "metric": metric_name,
                                        "value": value,
                                        "threshold": threshold
                                    }
                                }
                            }
                        }
                    }
                )
    return None

# Export all components
__all__ = [
    'product_analytics',
    'engineering_metrics',
    'video_metrics',
    'infrastructure_metrics',
    'product_analytics_schedule',
    'engineering_metrics_schedule',
    'video_metrics_schedule',
    'infrastructure_metrics_schedule',
    'performance_anomaly_sensor',
    'video_quality_sensor'
] 