from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime, timedelta
from ..storage.database_pool import db_pool
from ..storage.query_optimizer import query_optimizer
from ..monitoring.metrics import metrics
from ..utils.circuit_breaker import circuit_breakers

logger = logging.getLogger(__name__)

class DatabaseValidator:
    """Comprehensive database validation and monitoring"""
    
    def __init__(self):
        self.validation_interval = 300  # 5 minutes
        self.last_validation: Dict[str, datetime] = {}
        self.validation_thresholds = {
            "connection_usage": 0.8,     # 80% connection usage
            "query_latency": 1.0,        # 1 second
            "index_usage": 0.7,          # 70% index usage
            "cache_hit_rate": 0.6        # 60% cache hit rate
        }
    
    async def validate_connection_pools(self) -> Dict[str, Any]:
        """Validate database connection pools"""
        results = {}
        
        for db in ["postgres", "clickhouse"]:
            try:
                # Check pool health
                health = await db_pool.check_pool_health(db)
                stats = await db_pool.get_pool_stats(db)
                
                # Calculate connection usage
                if db == "postgres":
                    usage = stats["used_connections"] / stats["total_connections"]
                    results[db] = {
                        "status": health["status"],
                        "connection_usage": usage,
                        "latency": health["latency"],
                        "pool_stats": stats
                    }
                    
                    # Track metrics
                    metrics.track_db_connections(db, usage)
                    
                    # Check if usage is too high
                    if usage > self.validation_thresholds["connection_usage"]:
                        logger.warning(f"High connection usage for {db}: {usage:.2%}")
                        await db_pool.optimize_pool_size(db)
                
                elif db == "clickhouse":
                    results[db] = {
                        "status": health["status"],
                        "pool_size": stats["pool_size"],
                        "latency": health["latency"]
                    }
            except Exception as e:
                logger.error(f"Connection pool validation failed for {db}: {str(e)}")
                results[db] = {"status": "error", "error": str(e)}
        
        return results
    
    async def validate_query_patterns(self) -> Dict[str, Any]:
        """Validate query patterns and performance"""
        try:
            # Get query statistics
            stats = await query_optimizer.get_query_stats()
            
            # Analyze slow queries
            slow_queries = []
            for query, query_stats in stats["queries"].items():
                if query_stats["avg_duration"] > self.validation_thresholds["query_latency"]:
                    # Get optimization recommendations
                    optimization = await query_optimizer.optimize_query(query)
                    slow_queries.append({
                        "query": query,
                        "stats": query_stats,
                        "recommendations": optimization["recommendations"]
                    })
            
            return {
                "total_queries": stats["total_queries"],
                "slow_queries": len(slow_queries),
                "problematic_patterns": slow_queries,
                "optimization_recommendations": [
                    rec for q in slow_queries for rec in q["recommendations"]
                ]
            }
        except Exception as e:
            logger.error(f"Query pattern validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_index_usage(self) -> Dict[str, Any]:
        """Validate index usage and effectiveness"""
        try:
            async with db_pool.postgres_connection() as conn:
                # Check index usage statistics
                index_stats = await conn.fetch("""
                    SELECT
                        schemaname,
                        tablename,
                        indexrelname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        (idx_scan::float / (seq_scan + idx_scan + 1)) as index_usage_ratio
                    FROM pg_stat_all_indexes
                    WHERE idx_scan > 0
                    ORDER BY index_usage_ratio DESC
                """)
                
                # Identify unused and inefficient indexes
                unused_indexes = await conn.fetch("""
                    SELECT
                        schemaname,
                        tablename,
                        indexrelname,
                        idx_scan,
                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                    FROM pg_stat_all_indexes
                    WHERE idx_scan = 0
                    AND indexrelname NOT LIKE '%_pkey'
                    AND indexrelname NOT LIKE '%_unique'
                """)
                
                results = {
                    "total_indexes": len(index_stats),
                    "unused_indexes": len(unused_indexes),
                    "inefficient_indexes": [
                        {
                            "table": row["tablename"],
                            "index": row["indexrelname"],
                            "usage_ratio": float(row["index_usage_ratio"])
                        }
                        for row in index_stats
                        if float(row["index_usage_ratio"]) < self.validation_thresholds["index_usage"]
                    ],
                    "recommendations": []
                }
                
                # Generate recommendations
                if results["unused_indexes"] > 0:
                    results["recommendations"].append(
                        "Consider dropping unused indexes to improve write performance"
                    )
                if results["inefficient_indexes"]:
                    results["recommendations"].append(
                        "Analyze and optimize inefficient indexes"
                    )
                
                return results
        except Exception as e:
            logger.error(f"Index usage validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_failover_scenarios(self) -> Dict[str, Any]:
        """Validate database failover and recovery"""
        results = {}
        
        for db in ["postgres", "clickhouse"]:
            try:
                circuit_breaker = circuit_breakers[db]
                
                # Check circuit breaker state
                state = circuit_breaker.get_state()
                results[db] = {
                    "circuit_breaker_state": state["state"],
                    "failure_count": state["failure_count"],
                    "last_failure": state["last_failure"],
                    "last_success": state["last_success"]
                }
                
                # Test connection recovery if in half-open state
                if state["state"] == "half_open":
                    if db == "postgres":
                        async with db_pool.postgres_connection() as conn:
                            await conn.fetchval("SELECT 1")
                    elif db == "clickhouse":
                        async with db_pool.clickhouse_connection() as client:
                            await client.execute("SELECT 1")
                    
                    results[db]["recovery_test"] = "successful"
            except Exception as e:
                logger.error(f"Failover validation failed for {db}: {str(e)}")
                results[db] = {"status": "error", "error": str(e)}
        
        return results
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive database validation"""
        current_time = datetime.utcnow()
        
        # Check if validation is needed
        for db in ["postgres", "clickhouse"]:
            last_run = self.last_validation.get(db)
            if last_run and (current_time - last_run).total_seconds() < self.validation_interval:
                logger.info(f"Skipping validation for {db}, last run: {last_run}")
                continue
        
        try:
            # Run all validations
            results = {
                "timestamp": current_time.isoformat(),
                "connection_pools": await self.validate_connection_pools(),
                "query_patterns": await self.validate_query_patterns(),
                "index_usage": await self.validate_index_usage(),
                "failover_scenarios": await self.validate_failover_scenarios()
            }
            
            # Update last validation time
            for db in ["postgres", "clickhouse"]:
                self.last_validation[db] = current_time
            
            # Track validation metrics
            self._track_validation_metrics(results)
            
            return results
        except Exception as e:
            logger.error(f"Database validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _track_validation_metrics(self, results: Dict[str, Any]):
        """Track validation metrics"""
        try:
            # Track connection pool metrics
            for db, pool_results in results["connection_pools"].items():
                if "connection_usage" in pool_results:
                    metrics.track_db_connections(db, pool_results["connection_usage"])
            
            # Track query pattern metrics
            query_results = results["query_patterns"]
            metrics.track_slow_queries(query_results["slow_queries"])
            
            # Track index usage metrics
            index_results = results["index_usage"]
            metrics.track_unused_indexes(index_results["unused_indexes"])
            
            # Track failover metrics
            for db, failover_results in results["failover_scenarios"].items():
                if "failure_count" in failover_results:
                    metrics.track_db_failures(db, failover_results["failure_count"])
        except Exception as e:
            logger.error(f"Error tracking validation metrics: {str(e)}")

# Create global database validator
database_validator = DatabaseValidator() 