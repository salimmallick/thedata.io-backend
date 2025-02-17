from dagster import job, op, Out, In, Nothing, DagsterType
from typing import Dict, Any
import logging
from ...api.core.validation.database_validation import DatabaseValidator
from ...api.core.monitoring.metrics import metrics
from ...api.services.clickhouse import clickhouse_service
from ...api.services.questdb import questdb_service
from ...api.services.materialize import materialize_service
import asyncio

logger = logging.getLogger(__name__)

# Initialize database validator
database_validator = DatabaseValidator()

@op(out=Out(Dict[str, Any]))
async def validate_connection_pools(context) -> Dict[str, Any]:
    """Validate database connection pools"""
    context.log.info("Validating database connection pools")
    results = await database_validator.validate_connection_pools()
    
    # Log any issues found
    for db, pool_results in results.items():
        if pool_results.get("status") == "error":
            context.log.error(f"Connection pool validation failed for {db}: {pool_results['error']}")
        elif pool_results.get("connection_usage", 0) > database_validator.validation_thresholds["connection_usage"]:
            context.log.warning(f"High connection usage for {db}: {pool_results['connection_usage']:.2%}")
    
    return results

@op(out=Out(Dict[str, Any]))
async def validate_query_patterns(context) -> Dict[str, Any]:
    """Validate query patterns and performance"""
    context.log.info("Validating query patterns")
    results = await database_validator.validate_query_patterns()
    
    # Log slow queries and recommendations
    if results.get("slow_queries", 0) > 0:
        context.log.warning(f"Found {results['slow_queries']} slow queries")
        for query in results.get("problematic_patterns", []):
            context.log.info(f"Slow query: {query['query']}")
            for rec in query.get("recommendations", []):
                context.log.info(f"Recommendation: {rec}")
    
    return results

@op(out=Out(Dict[str, Any]))
async def validate_index_usage(context) -> Dict[str, Any]:
    """Validate index usage and effectiveness"""
    context.log.info("Validating index usage")
    results = await database_validator.validate_index_usage()
    
    # Log index issues
    if results.get("unused_indexes", 0) > 0:
        context.log.warning(f"Found {results['unused_indexes']} unused indexes")
    if results.get("inefficient_indexes"):
        context.log.warning(f"Found {len(results['inefficient_indexes'])} inefficient indexes")
    for rec in results.get("recommendations", []):
        context.log.info(f"Recommendation: {rec}")
    
    return results

@op(out=Out(Dict[str, Any]))
async def validate_failover_scenarios(context) -> Dict[str, Any]:
    """Validate database failover and recovery"""
    context.log.info("Validating failover scenarios")
    results = await database_validator.validate_failover_scenarios()
    
    # Log failover issues
    for db, failover_results in results.items():
        if failover_results.get("status") == "error":
            context.log.error(f"Failover validation failed for {db}: {failover_results['error']}")
        elif failover_results.get("circuit_breaker_state") != "closed":
            context.log.warning(
                f"Circuit breaker for {db} is {failover_results['circuit_breaker_state']}, "
                f"failure count: {failover_results.get('failure_count', 0)}"
            )
    
    return results

@op(
    ins={
        "connection_pools": In(Dict[str, Any]),
        "query_patterns": In(Dict[str, Any]),
        "index_usage": In(Dict[str, Any]),
        "failover_scenarios": In(Dict[str, Any])
    }
)
def evaluate_database_validation_results(
    context,
    connection_pools: Dict[str, Any],
    query_patterns: Dict[str, Any],
    index_usage: Dict[str, Any],
    failover_scenarios: Dict[str, Any]
) -> Nothing:
    """Evaluate all validation results and take necessary actions"""
    try:
        # Track overall validation status
        validation_status = "healthy"
        issues = []
        
        # Check connection pools
        for db, pool_results in connection_pools.items():
            if pool_results.get("status") == "error":
                validation_status = "unhealthy"
                issues.append(f"Connection pool error in {db}")
            elif pool_results.get("connection_usage", 0) > database_validator.validation_thresholds["connection_usage"]:
                validation_status = "degraded"
                issues.append(f"High connection usage in {db}")
        
        # Check query patterns
        if query_patterns.get("slow_queries", 0) > 0:
            validation_status = "degraded"
            issues.append(f"Found {query_patterns['slow_queries']} slow queries")
        
        # Check index usage
        if index_usage.get("unused_indexes", 0) > 0:
            issues.append(f"Found {index_usage['unused_indexes']} unused indexes")
        if index_usage.get("inefficient_indexes"):
            issues.append(f"Found {len(index_usage['inefficient_indexes'])} inefficient indexes")
        
        # Check failover scenarios
        for db, failover_results in failover_scenarios.items():
            if failover_results.get("status") == "error":
                validation_status = "unhealthy"
                issues.append(f"Failover validation error in {db}")
            elif failover_results.get("circuit_breaker_state") != "closed":
                validation_status = "degraded"
                issues.append(f"Circuit breaker issues in {db}")
        
        # Log overall status
        context.log.info(f"Database validation status: {validation_status}")
        if issues:
            context.log.warning("Validation issues found:")
            for issue in issues:
                context.log.warning(f"- {issue}")
        
        # Track metrics
        metrics.track_validation_status(validation_status, len(issues))
        
    except Exception as e:
        context.log.error(f"Error evaluating validation results: {str(e)}")
        raise

@op(out={"clickhouse_status": Out(Dict[str, Any])})
def validate_clickhouse():
    """Validate ClickHouse database connectivity and health."""
    try:
        # Test connection and basic query
        result = asyncio.run(clickhouse_service.execute_query("SELECT 1"))
        return {"status": "healthy", "message": "ClickHouse is operational"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

@op(out={"questdb_status": Out(Dict[str, Any])})
def validate_questdb():
    """Validate QuestDB database connectivity and health."""
    try:
        # Test connection and basic query
        result = asyncio.run(questdb_service.execute_query("SELECT 1"))
        return {"status": "healthy", "message": "QuestDB is operational"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

@op(out={"materialize_status": Out(Dict[str, Any])})
def validate_materialize():
    """Validate Materialize database connectivity and health."""
    try:
        # Test connection and basic query
        result = asyncio.run(materialize_service.execute_query("SELECT 1"))
        return {"status": "healthy", "message": "Materialize is operational"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

@job(
    description="Comprehensive database validation job",
    tags={"category": "maintenance"}
)
def validate_databases():
    """Job to run comprehensive database validation"""
    connection_results = validate_connection_pools()
    query_results = validate_query_patterns()
    index_results = validate_index_usage()
    failover_results = validate_failover_scenarios()
    
    evaluate_database_validation_results(
        connection_results,
        query_results,
        index_results,
        failover_results
    )

    clickhouse_result = validate_clickhouse()
    questdb_result = validate_questdb()
    materialize_result = validate_materialize() 