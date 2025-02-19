from typing import Dict, Any, List, Optional
import asyncio
from .database_pool import db_pool
from ..monitoring.metrics import metrics
import logging
import time
import re

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Optimizer for database queries"""
    
    def __init__(self):
        self.query_stats: Dict[str, Dict[str, Any]] = {}
        self.slow_query_threshold = 1.0  # 1 second
        self.query_pattern = re.compile(r'\s+')
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent tracking"""
        # Remove extra whitespace and convert to lowercase
        query = self.query_pattern.sub(' ', query.strip().lower())
        return query
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query execution plan"""
        try:
            async with db_pool.get_postgres_conn() as conn:
                # Get query execution plan
                plan = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {query}")
                
                # Extract key metrics from plan
                metrics = self._extract_plan_metrics(plan[0])
                
                return {
                    "plan": plan[0],
                    "metrics": metrics,
                    "recommendations": self._generate_recommendations(metrics)
                }
        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            return {"error": str(e)}
    
    def _extract_plan_metrics(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from query execution plan"""
        metrics = {
            "total_cost": plan.get("Total Cost", 0),
            "rows": plan.get("Plan Rows", 0),
            "width": plan.get("Plan Width", 0),
            "scan_type": plan.get("Node Type", ""),
            "index_used": "Index" in plan.get("Node Type", "")
        }
        return metrics
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate query optimization recommendations"""
        recommendations = []
        
        if metrics["total_cost"] > 1000:
            recommendations.append("Consider adding indexes to reduce query cost")
        
        if not metrics["index_used"] and metrics["rows"] > 1000:
            recommendations.append("Add appropriate indexes for large table scans")
        
        if metrics["width"] > 100:
            recommendations.append("Select specific columns instead of using SELECT *")
        
        return recommendations
    
    async def track_query_performance(
        self,
        query: str,
        duration: float,
        rows_affected: int
    ):
        """Track query performance metrics"""
        normalized_query = self._normalize_query(query)
        
        if normalized_query not in self.query_stats:
            self.query_stats[normalized_query] = {
                "count": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "min_duration": float('inf'),
                "max_duration": 0,
                "total_rows": 0,
                "last_seen": 0
            }
        
        stats = self.query_stats[normalized_query]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["avg_duration"] = stats["total_duration"] / stats["count"]
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)
        stats["total_rows"] += rows_affected
        stats["last_seen"] = time.time()
        
        # Track slow queries
        if duration > self.slow_query_threshold:
            logger.warning(f"Slow query detected: {query}")
            metrics.track_db_query("postgres", "slow_query", duration)
    
    async def get_query_stats(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        return {
            "total_queries": len(self.query_stats),
            "slow_queries": sum(
                1 for stats in self.query_stats.values()
                if stats["avg_duration"] > self.slow_query_threshold
            ),
            "queries": self.query_stats
        }
    
    async def optimize_query(self, query: str) -> Dict[str, Any]:
        """Optimize query based on analysis"""
        try:
            # Analyze current query
            analysis = await self.analyze_query(query)
            
            # Generate optimized query
            optimized_query = query
            recommendations = []
            
            # Check for common optimization opportunities
            if "SELECT *" in query.upper():
                recommendations.append("Replace SELECT * with specific columns")
            
            if "WHERE" not in query.upper():
                recommendations.append("Add WHERE clause to filter results")
            
            if "JOIN" in query.upper() and "INDEX" not in analysis.get("plan", {}).get("Node Type", ""):
                recommendations.append("Add indexes for JOIN conditions")
            
            return {
                "original_query": query,
                "optimized_query": optimized_query,
                "recommendations": recommendations,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"Query optimization failed: {str(e)}")
            return {"error": str(e)}
    
    def reset_stats(self):
        """Reset query statistics"""
        self.query_stats.clear()

    async def get_table_size(self, table_name: str) -> int:
        """Get the size of a table in bytes."""
        try:
            async with db_pool.get_postgres_conn() as conn:
                size = await conn.fetchval("""
                    SELECT pg_total_relation_size($1)
                """, table_name)
                return size
        except Exception as e:
            logger.error(f"Error getting table size: {e}")
            return 0

# Create global query optimizer
query_optimizer = QueryOptimizer() 