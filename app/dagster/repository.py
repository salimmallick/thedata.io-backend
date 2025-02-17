from dagster import (
    Definitions,
    RepositoryDefinition,
    with_resources,
    define_asset_job,
    AssetSelection,
    load_assets_from_modules
)
from app.dagster.jobs.materialized_views import (
    realtime_views,
    view_optimization,
    realtime_views_schedule,
    view_optimization_schedule
)
from app.dagster.jobs.events import (
    product_analytics,
    engineering_metrics,
    video_metrics,
    infrastructure_metrics,
    product_analytics_schedule,
    engineering_metrics_schedule,
    video_metrics_schedule,
    infrastructure_metrics_schedule,
    performance_anomaly_sensor,
    video_quality_sensor
)
from app.dagster.jobs.timeseries import (
    daily_processing,
    realtime_processing,
    cleanup_old_data,
    monitor_data_quality,
    daily_cleanup,
    hourly_monitoring
)
from app.dagster.jobs.data_quality import (
    check_event_data_quality,
    check_metric_data_quality,
    validate_data_freshness,
    validate_schema_consistency,
    evaluate_data_quality
)
from app.dagster.assets import materialized_views, events, timeseries
from app.api.services.materialize import materialize_service
from app.api.services.clickhouse import clickhouse_service
from app.api.services.questdb import questdb_service
from app.api.services.pipeline import pipeline_service
from app.dagster.jobs.database_validation import validate_databases
from app.dagster.schedules.database_validation import database_validation_schedule
from app.dagster.jobs.message_queue_validation import validate_message_queue
from app.dagster.schedules.message_queue_validation import message_queue_validation_schedule
from app.dagster.jobs.api_validation import validate_api
from app.dagster.schedules.api_validation import api_validation_schedule
from app.dagster.sensors.data_quality import (
    data_quality_sensor,
    schema_validation_sensor,
    data_freshness_sensor
)

# Load all assets from modules
all_assets = load_assets_from_modules([
    materialized_views,
    events,
    timeseries
])

# Define the main pipeline job that shows the complete data flow
main_pipeline = define_asset_job(
    name="complete_data_pipeline",
    selection=AssetSelection.all(),
    description="Complete data pipeline showing all components and their relationships"
)

# Resource configuration
resources = {
    "materialize": materialize_service,
    "clickhouse": clickhouse_service,
    "questdb": questdb_service,
    "pipeline": pipeline_service
}

# Create the repository definition
defs = Definitions(
    assets=all_assets,
    jobs=[
        # Main pipeline
        main_pipeline,
        # Materialized views jobs
        realtime_views,
        view_optimization,
        # Event processing jobs
        product_analytics,
        engineering_metrics,
        video_metrics,
        infrastructure_metrics,
        # Timeseries jobs
        daily_processing,
        realtime_processing,
        cleanup_old_data,
        monitor_data_quality,
        # Validation jobs
        validate_databases,
        validate_message_queue,
        validate_api
    ],
    schedules=[
        # Materialized views schedules
        realtime_views_schedule,
        view_optimization_schedule,
        # Event processing schedules
        product_analytics_schedule,
        engineering_metrics_schedule,
        video_metrics_schedule,
        infrastructure_metrics_schedule,
        # Validation schedules
        database_validation_schedule,
        message_queue_validation_schedule,
        api_validation_schedule,
        # Timeseries schedules
        daily_cleanup,
        hourly_monitoring
    ],
    sensors=[
        # Data quality sensors
        data_quality_sensor,
        schema_validation_sensor,
        data_freshness_sensor,
        # Event monitoring sensors
        performance_anomaly_sensor,
        video_quality_sensor
    ],
    resources=resources
) 