from dagster import job, op, Out, In, Nothing, DagsterType, RetryPolicy, Backoff
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ...api.services.materialize import materialize_service
from ...api.core.monitoring.metrics import metrics
import logging
from ...api.core.storage.database import get_clickhouse_client, get_questdb_sender, get_postgres_conn

logger = logging.getLogger(__name__)

class DataQualityMetrics:
    """Data quality metrics calculation and validation"""
    
    @staticmethod
    def calculate_completeness(df: pd.DataFrame) -> Dict[str, float]:
        """Calculate completeness metrics"""
        return {
            col: (1 - df[col].isnull().mean()) * 100
            for col in df.columns
        }
    
    @staticmethod
    def calculate_validity(df: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, float]:
        """Calculate validity metrics based on rules"""
        validity = {}
        for column, rule in rules.items():
            if column in df.columns:
                if rule["type"] == "range":
                    valid = df[column].between(rule["min"], rule["max"])
                elif rule["type"] == "regex":
                    valid = df[column].str.match(rule["pattern"])
                elif rule["type"] == "categorical":
                    valid = df[column].isin(rule["values"])
                validity[column] = (valid.mean() * 100)
        return validity
    
    @staticmethod
    def calculate_timeliness(df: pd.DataFrame, timestamp_col: str) -> float:
        """Calculate timeliness metric"""
        if timestamp_col not in df.columns:
            return 0.0
        
        current_time = pd.Timestamp.now()
        delays = (current_time - pd.to_datetime(df[timestamp_col])).dt.total_seconds()
        return delays.mean()

# Define retry policy for validation operations
validation_retry_policy = RetryPolicy(
    max_retries=3,
    delay=30,
    backoff=Backoff.EXPONENTIAL
)

@op(out=Out(Dict[str, Dict[str, Any]]))
def check_event_data_quality(context) -> Dict[str, Dict[str, Any]]:
    """Check data quality for event data"""
    query = """
    SELECT *
    FROM user_interaction_events
    WHERE timestamp >= now() - interval '1 hour'
    """
    
    # Get data from materialized view
    df = pd.DataFrame(materialize_service.execute_query(query))
    
    if df.empty:
        return {
            "completeness": {},
            "validity": {},
            "timeliness": 0.0
        }
    
    # Define validation rules
    validation_rules = {
        "event_type": {
            "type": "categorical",
            "values": ["click", "view", "submit", "error"]
        },
        "user_id": {
            "type": "regex",
            "pattern": r"^[a-f0-9]{24}$"
        }
    }
    
    # Calculate metrics
    completeness = DataQualityMetrics.calculate_completeness(df)
    validity = DataQualityMetrics.calculate_validity(df, validation_rules)
    timeliness = DataQualityMetrics.calculate_timeliness(df, "timestamp")
    
    # Track metrics
    metrics.track_data_quality("events", {
        "completeness": np.mean(list(completeness.values())),
        "validity": np.mean(list(validity.values())),
        "timeliness": timeliness
    })
    
    return {
        "completeness": completeness,
        "validity": validity,
        "timeliness": timeliness
    }

@op(out=Out(Dict[str, Dict[str, Any]]))
def check_metric_data_quality(context) -> Dict[str, Dict[str, Any]]:
    """Check data quality for metric data"""
    query = """
    SELECT *
    FROM performance_metrics
    WHERE timestamp >= now() - interval '1 hour'
    """
    
    # Get data from materialized view
    df = pd.DataFrame(materialize_service.execute_query(query))
    
    if df.empty:
        return {
            "completeness": {},
            "validity": {},
            "timeliness": 0.0
        }
    
    # Define validation rules
    validation_rules = {
        "value": {
            "type": "range",
            "min": 0,
            "max": float('inf')
        }
    }
    
    # Calculate metrics
    completeness = DataQualityMetrics.calculate_completeness(df)
    validity = DataQualityMetrics.calculate_validity(df, validation_rules)
    timeliness = DataQualityMetrics.calculate_timeliness(df, "timestamp")
    
    # Track metrics
    metrics.track_data_quality("metrics", {
        "completeness": np.mean(list(completeness.values())),
        "validity": np.mean(list(validity.values())),
        "timeliness": timeliness
    })
    
    return {
        "completeness": completeness,
        "validity": validity,
        "timeliness": timeliness
    }

@op(out=Out(Dict[str, Any]))
def validate_data_freshness(context) -> Dict[str, Any]:
    """Validate data freshness across all data sources"""
    async def _validate():
        results = {
            "clickhouse": {"status": "unknown", "delay": 0},
            "questdb": {"status": "unknown", "delay": 0},
            "postgres": {"status": "unknown", "delay": 0}
        }
        
        try:
            # Check ClickHouse freshness
            ch_client = get_clickhouse_client()
            ch_result = ch_client.execute("""
                SELECT max(timestamp) as last_event
                FROM user_interaction_events
            """)
            if ch_result and ch_result[0][0]:
                delay = (datetime.utcnow() - ch_result[0][0]).total_seconds()
                results["clickhouse"] = {
                    "status": "healthy" if delay < 300 else "delayed",
                    "delay": delay
                }
            
            # Check QuestDB freshness
            qdb_sender = get_questdb_sender()
            qdb_result = qdb_sender.execute("""
                SELECT max(ts) as last_metric
                FROM performance_metrics
            """)
            if qdb_result and qdb_result[0][0]:
                delay = (datetime.utcnow() - qdb_result[0][0]).total_seconds()
                results["questdb"] = {
                    "status": "healthy" if delay < 300 else "delayed",
                    "delay": delay
                }
            
            # Check PostgreSQL freshness
            pg_conn = get_postgres_conn()
            pg_result = pg_conn.fetchrow("""
                SELECT max(created_at) as last_record
                FROM organizations
            """)
            if pg_result and pg_result['last_record']:
                delay = (datetime.utcnow() - pg_result['last_record']).total_seconds()
                results["postgres"] = {
                    "status": "healthy" if delay < 300 else "delayed",
                    "delay": delay
                }
            
            # Track metrics
            for source, data in results.items():
                metrics.track_data_freshness(source, data["delay"])
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating data freshness: {str(e)}")
            raise
    
    return context.resources.io_manager.run_async(_validate)

@op(out=Out(Dict[str, Any]))
def validate_schema_consistency(context) -> Dict[str, Any]:
    """Validate schema consistency across all data stores"""
    async def _validate():
        results = {
            "clickhouse": {"status": "unknown", "issues": []},
            "questdb": {"status": "unknown", "issues": []},
            "postgres": {"status": "unknown", "issues": []}
        }
        
        try:
            # Check ClickHouse schema
            ch_client = get_clickhouse_client()
            ch_schema = ch_client.execute("""
                SELECT 
                    name,
                    type,
                    default_expression
                FROM system.columns
                WHERE table = 'user_interaction_events'
            """)
            
            # Check QuestDB schema
            qdb_sender = get_questdb_sender()
            qdb_schema = qdb_sender.execute("""
                SELECT 
                    column_name,
                    data_type,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'performance_metrics'
            """)
            
            # Check PostgreSQL schema
            pg_conn = get_postgres_conn()
            pg_schema = pg_conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'organizations'
            """)
            
            # Validate schemas against expected structure
            expected_schemas = {
                "clickhouse": {
                    "user_interaction_events": {
                        "event_id": "String",
                        "timestamp": "DateTime64",
                        "event_type": "String",
                        "event_name": "String",
                        "properties": "String",
                        "context": "String"
                    }
                },
                "questdb": {
                    "performance_metrics": {
                        "ts": "TIMESTAMP",
                        "metric_name": "SYMBOL",
                        "value": "DOUBLE",
                        "tags": "SYMBOL[]"
                    }
                }
            }
            
            # Compare and record issues
            for source, schema_data in expected_schemas.items():
                for table, expected_columns in schema_data.items():
                    actual_schema = None
                    if source == "clickhouse":
                        actual_schema = {row[0]: row[1] for row in ch_schema}
                    elif source == "questdb":
                        actual_schema = {row[0]: row[1] for row in qdb_schema}
                    
                    if actual_schema:
                        for col, exp_type in expected_columns.items():
                            if col not in actual_schema:
                                results[source]["issues"].append(f"Missing column: {col}")
                            elif actual_schema[col] != exp_type:
                                results[source]["issues"].append(
                                    f"Type mismatch for {col}: expected {exp_type}, got {actual_schema[col]}"
                                )
            
            # Update status based on issues
            for source in results:
                results[source]["status"] = "healthy" if not results[source]["issues"] else "inconsistent"
            
            # Track metrics
            for source, data in results.items():
                metrics.track_schema_changes(source, len(data["issues"]))
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating schema consistency: {str(e)}")
            raise
    
    return context.resources.io_manager.run_async(_validate)

@op(
    ins={
        "event_metrics": In(Dict[str, Dict[str, Any]]),
        "metric_metrics": In(Dict[str, Dict[str, Any]]),
        "freshness": In(Dict[str, Any]),
        "schema": In(Dict[str, Any])
    }
)
def evaluate_data_quality(
    context,
    event_metrics: Dict[str, Dict[str, Any]],
    metric_metrics: Dict[str, Dict[str, Any]],
    freshness: Dict[str, Any],
    schema: Dict[str, Any]
) -> Nothing:
    """Evaluate overall data quality and take necessary actions"""
    try:
        # Track overall quality status
        quality_status = "healthy"
        issues = []
        
        # Check data freshness
        for source, data in freshness.items():
            if data["status"] != "healthy":
                quality_status = "degraded"
                issues.append(f"Data freshness issue in {source}: {data['delay']}s delay")
        
        # Check schema consistency
        for source, data in schema.items():
            if data["status"] != "healthy":
                quality_status = "degraded"
                issues.extend(data["issues"])
        
        # Check event data quality
        for metric_type, metrics in event_metrics.items():
            if metric_type == "completeness":
                for field, value in metrics.items():
                    if value < 95:  # Less than 95% completeness
                        quality_status = "degraded"
                        issues.append(f"Low completeness for event {field}: {value}%")
            elif metric_type == "validity":
                for field, value in metrics.items():
                    if value < 90:  # Less than 90% validity
                        quality_status = "degraded"
                        issues.append(f"Low validity for event {field}: {value}%")
            elif metric_type == "timeliness" and metrics > 300:  # More than 5 minutes delay
                quality_status = "degraded"
                issues.append(f"High event data latency: {metrics}s")
        
        # Check metric data quality
        for metric_type, metrics in metric_metrics.items():
            if metric_type == "completeness":
                for field, value in metrics.items():
                    if value < 95:  # Less than 95% completeness
                        quality_status = "degraded"
                        issues.append(f"Low completeness for metric {field}: {value}%")
            elif metric_type == "validity":
                for field, value in metrics.items():
                    if value < 90:  # Less than 90% validity
                        quality_status = "degraded"
                        issues.append(f"Low validity for metric {field}: {value}%")
            elif metric_type == "timeliness" and metrics > 300:  # More than 5 minutes delay
                quality_status = "degraded"
                issues.append(f"High metric data latency: {metrics}s")
        
        # Log quality status
        context.log.info(f"Data quality status: {quality_status}")
        if issues:
            context.log.warning("Quality issues found:")
            for issue in issues:
                context.log.warning(f"- {issue}")
        
        # Track metrics
        metrics.track_data_quality_status(quality_status, len(issues))
        
    except Exception as e:
        context.log.error(f"Error evaluating data quality: {str(e)}")
        raise

@job(
    description="Enhanced data quality monitoring job",
    tags={"category": "monitoring"}
)
def monitor_data_quality():
    """Job to monitor comprehensive data quality"""
    event_metrics = check_event_data_quality()
    metric_metrics = check_metric_data_quality()
    freshness = validate_data_freshness()
    schema = validate_schema_consistency()
    
    evaluate_data_quality(
        event_metrics=event_metrics,
        metric_metrics=metric_metrics,
        freshness=freshness,
        schema=schema
    ) 