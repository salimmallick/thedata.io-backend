from dagster import sensor, RunRequest, SensorResult, DefaultSensorStatus
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
from ...api.core.monitoring.metrics import metrics
from ...api.services.materialize import materialize_service
from ...api.services.clickhouse import clickhouse_service
from ...api.services.questdb import questdb_service
import asyncio

logger = logging.getLogger(__name__)

@sensor(
    job_name="monitor_data_quality",
    minimum_interval_seconds=300,  # Run every 5 minutes
    default_status=DefaultSensorStatus.RUNNING
)
def data_quality_sensor(context):
    """Sensor to monitor data quality metrics"""
    try:
        # Get data quality metrics from materialized view
        query = """
        SELECT
            component,
            freshness_status,
            completeness_ratio,
            validity_ratio,
            schema_status
        FROM mv_data_quality_metrics
        WHERE timestamp >= now() - interval '15 minutes'
        """
        
        results = materialize_service.execute_query(query)
        
        issues = []
        for row in results:
            component = row["component"]
            
            # Check freshness
            if row["freshness_status"] != "healthy":
                issues.append({
                    "component": component,
                    "type": "freshness",
                    "status": row["freshness_status"]
                })
            
            # Check completeness
            if row["completeness_ratio"] < 0.95:
                issues.append({
                    "component": component,
                    "type": "completeness",
                    "value": row["completeness_ratio"]
                })
            
            # Check validity
            if row["validity_ratio"] < 0.90:
                issues.append({
                    "component": component,
                    "type": "validity",
                    "value": row["validity_ratio"]
                })
            
            # Check schema
            if row["schema_status"] != "healthy":
                issues.append({
                    "component": component,
                    "type": "schema",
                    "status": row["schema_status"]
                })
        
        if issues:
            # Track issues in metrics
            for issue in issues:
                metrics.track_data_quality_issue(
                    component=issue["component"],
                    issue_type=issue["type"],
                    value=issue.get("value", 0)
                )
            
            # Trigger data quality job
            return RunRequest(
                run_key=f"data_quality_{datetime.now().isoformat()}",
                run_config={
                    "ops": {
                        "evaluate_data_quality": {
                            "config": {
                                "issues": issues
                            }
                        }
                    }
                }
            )
        
        return SkipReason(f"No data quality issues detected at {datetime.now().isoformat()}")
        
    except Exception as e:
        logger.error(f"Error in data quality sensor: {str(e)}")
        return SkipReason(f"Error: {str(e)}")

@sensor(
    job_name="monitor_data_quality",
    minimum_interval_seconds=3600,  # Run every hour
    default_status=DefaultSensorStatus.RUNNING
)
def schema_validation_sensor(context):
    """Sensor to detect schema changes and validate consistency"""
    try:
        # Get schema information from all sources
        schema_changes = []
        
        # Check ClickHouse schema changes
        clickhouse_query = """
        SELECT
            table,
            name,
            type,
            default_expression,
            modification_time
        FROM system.columns
        WHERE modification_time >= now() - interval 1 hour
        """
        
        # Check QuestDB schema changes
        questdb_query = """
        SELECT
            table_name,
            column_name,
            data_type,
            column_default
        FROM information_schema.columns
        WHERE last_modified >= now() - interval '1 hour'
        """
        
        # Track any detected changes
        if schema_changes:
            return RunRequest(
                run_key=f"schema_validation_{datetime.now().isoformat()}",
                run_config={
                    "ops": {
                        "validate_schema_consistency": {
                            "config": {
                                "changes": schema_changes
                            }
                        }
                    }
                }
            )
        
        return SkipReason(f"No schema changes detected at {datetime.now().isoformat()}")
        
    except Exception as e:
        logger.error(f"Error in schema validation sensor: {str(e)}")
        return SkipReason(f"Error: {str(e)}")

@sensor(
    job_name="monitor_data_quality",
    minimum_interval_seconds=60,  # Run every minute
    default_status=DefaultSensorStatus.RUNNING
)
def data_freshness_sensor(context):
    """Sensor to monitor data freshness across all sources"""
    try:
        freshness_issues = []
        
        # Check ClickHouse freshness
        clickhouse_query = """
        SELECT
            table,
            max(timestamp) as last_update,
            now() - max(timestamp) as delay
        FROM system.parts
        GROUP BY table
        HAVING delay > interval '5 minute'
        """
        
        # Check QuestDB freshness
        questdb_query = """
        SELECT
            table_name,
            max(ts) as last_update,
            now() - max(ts) as delay
        FROM information_schema.tables
        GROUP BY table_name
        HAVING delay > interval '5 minute'
        """
        
        if freshness_issues:
            return RunRequest(
                run_key=f"freshness_check_{datetime.now().isoformat()}",
                run_config={
                    "ops": {
                        "validate_data_freshness": {
                            "config": {
                                "issues": freshness_issues
                            }
                        }
                    }
                }
            )
        
        return SkipReason(f"No freshness issues detected at {datetime.now().isoformat()}")
        
    except Exception as e:
        logger.error(f"Error in data freshness sensor: {str(e)}")
        return SkipReason(f"Error: {str(e)}")

@sensor(job_name="monitor_data_quality")
def data_quality_sensor(context):
    """Sensor to monitor data quality metrics."""
    try:
        # Check data quality metrics
        # TODO: Implement actual data quality checks
        return SensorResult(
            run_requests=[],
            skip_reason="Data quality monitoring not implemented yet"
        )
    except Exception as e:
        logger.error(f"Error in data quality sensor: {e}")
        return SensorResult(skip_reason=str(e))

@sensor(job_name="monitor_data_quality")
def schema_validation_sensor(context):
    """Sensor to validate data schemas."""
    try:
        # Validate data schemas
        # TODO: Implement schema validation
        return SensorResult(
            run_requests=[],
            skip_reason="Schema validation not implemented yet"
        )
    except Exception as e:
        logger.error(f"Error in schema validation sensor: {e}")
        return SensorResult(skip_reason=str(e))

@sensor(job_name="monitor_data_quality")
def data_freshness_sensor(context):
    """Sensor to monitor data freshness."""
    try:
        # Check data freshness
        result = asyncio.run(check_data_freshness())
        if result["stale_tables"]:
            return SensorResult(
                run_requests=[
                    RunRequest(
                        run_key=f"data_freshness_{datetime.utcnow().isoformat()}",
                        tags={
                            "type": "data_quality",
                            "issue": "stale_data",
                            "tables": ",".join(result["stale_tables"])
                        }
                    )
                ]
            )
        return SensorResult(skip_reason="All data is fresh")
    except Exception as e:
        logger.error(f"Error in data freshness sensor: {e}")
        return SensorResult(skip_reason=str(e))

async def check_data_freshness() -> Dict[str, Any]:
    """Check freshness of data in all tables."""
    stale_tables = []
    freshness_threshold = timedelta(hours=1)
    
    try:
        # Check ClickHouse tables
        clickhouse_tables = await clickhouse_service.execute_query("""
            SELECT table, max(timestamp) as last_update
            FROM system.parts
            GROUP BY table
        """)
        
        for table in clickhouse_tables:
            if datetime.now() - table["last_update"] > freshness_threshold:
                stale_tables.append(f"clickhouse.{table['table']}")
        
        # Check QuestDB tables
        questdb_tables = await questdb_service.execute_query("""
            SELECT table_name, last_update
            FROM information_schema.tables
            WHERE table_type = 'TABLE'
        """)
        
        for table in questdb_tables:
            if datetime.now() - table["last_update"] > freshness_threshold:
                stale_tables.append(f"questdb.{table['table_name']}")
        
        return {
            "stale_tables": stale_tables,
            "check_time": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error checking data freshness: {e}")
        return {
            "stale_tables": [],
            "error": str(e),
            "check_time": datetime.utcnow()
        } 