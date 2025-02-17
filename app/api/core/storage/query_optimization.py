from typing import Dict, Any, List, Optional, Tuple
import asyncio
import time
import re
import logging
from datetime import datetime, timedelta
from ..monitoring.metrics import metrics
from .database_pool import db_pool

logger = logging.getLogger(__name__)

class QueryPattern:
    """Represents a query pattern with its performance characteristics"""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.executions = 0
        self.total_duration = 0.0
        self.min_duration = float('inf')
        self.max_duration = 0.0
        self.last_seen = None
        self.table_access = set()
        self.index_usage = {}
        self.optimization_history = []
    
    def record_execution(self, duration: float, plan_data: Dict[str, Any]):
        """Record query execution statistics"""
        self.executions += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.last_seen = datetime.utcnow()
        
        # Extract table and index information
        if "table_access" in plan_data:
            self.table_access.update(plan_data["table_access"])
        if "index_usage" in plan_data:
            for idx, count in plan_data["index_usage"].items():
                self.index_usage[idx] = self.index_usage.get(idx, 0) + count
    
    @property
    def avg_duration(self) -> float:
        """Calculate average execution duration"""
        return self.total_duration / self.executions if self.executions > 0 else 0

class QueryOptimizer:
    """Advanced query optimization system"""
    
    def __init__(self):
        self.patterns: Dict[str, QueryPattern] = {}
        self.slow_query_threshold = 1.0  # seconds
        self.pattern_expiry = timedelta(days=7)
        self.optimization_rules = self._load_optimization_rules()
        self.last_analysis = None
        self.optimization_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "failed_optimizations": 0
        }
    
    def _load_optimization_rules(self) -> List[Dict[str, Any]]:
        """Load query optimization rules"""
        return [
            {
                "pattern": r"SELECT \* FROM",
                "recommendation": "Specify required columns instead of using SELECT *",
                "priority": "high"
            },
            {
                "pattern": r"(?i)WHERE .+ LIKE '%",
                "recommendation": "Leading wildcard LIKE causes full table scan",
                "priority": "medium"
            },
            {
                "pattern": r"(?i)OR.*OR",
                "recommendation": "Multiple OR conditions may prevent index usage",
                "priority": "medium"
            },
            {
                "pattern": r"(?i)ORDER BY RANDOM\(\)",
                "recommendation": "Random sorting is expensive, consider alternatives",
                "priority": "high"
            }
        ]
    
    async def analyze_query(
        self,
        query: str,
        duration: float,
        database: str = "postgres"
    ) -> Dict[str, Any]:
        """Analyze query execution and gather performance data"""
        try:
            # Get query execution plan
            plan_data = await self._get_execution_plan(query, database)
            
            # Normalize and store pattern
            pattern = self._normalize_query(query)
            if pattern not in self.patterns:
                self.patterns[pattern] = QueryPattern(pattern)
            
            # Record execution
            self.patterns[pattern].record_execution(duration, plan_data)
            
            # Track metrics
            self._track_query_metrics(pattern, duration, database)
            
            # Check for optimization opportunities
            recommendations = await self.get_optimization_recommendations(query, plan_data)
            
            return {
                "pattern": pattern,
                "duration": duration,
                "plan": plan_data,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            return {"error": str(e)}
    
    async def _get_execution_plan(
        self,
        query: str,
        database: str
    ) -> Dict[str, Any]:
        """Get query execution plan with detailed statistics"""
        plan_data = {"table_access": set(), "index_usage": {}}
        
        if database == "postgres":
            async with db_pool.postgres_connection() as conn:
                explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE) {query}"
                result = await conn.fetchval(explain_query)
                plan = result[0]["Plan"]
                
                # Extract table and index information
                self._extract_plan_info(plan, plan_data)
        
        return plan_data
    
    def _extract_plan_info(
        self,
        plan: Dict[str, Any],
        plan_data: Dict[str, Any]
    ):
        """Extract relevant information from execution plan"""
        if "Relation Name" in plan:
            plan_data["table_access"].add(plan["Relation Name"])
        
        if "Index Name" in plan:
            index_name = plan["Index Name"]
            plan_data["index_usage"][index_name] = \
                plan_data["index_usage"].get(index_name, 0) + 1
        
        if "Plans" in plan:
            for subplan in plan["Plans"]:
                self._extract_plan_info(subplan, plan_data)
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching"""
        # Remove literal values
        query = re.sub(r"'[^']*'", "'?'", query)
        query = re.sub(r"\d+", "?", query)
        
        # Normalize whitespace
        query = " ".join(query.split())
        
        return query.lower()
    
    def _track_query_metrics(
        self,
        pattern: str,
        duration: float,
        database: str
    ):
        """Track query performance metrics"""
        metrics.track_db_query(database, "query", duration)
        
        if duration > self.slow_query_threshold:
            metrics.track_db_query(database, "slow_query", duration)
    
    async def get_optimization_recommendations(
        self,
        query: str,
        plan_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate query optimization recommendations"""
        recommendations = []
        
        # Check against optimization rules
        for rule in self.optimization_rules:
            if re.search(rule["pattern"], query, re.IGNORECASE):
                recommendations.append({
                    "type": "pattern",
                    "recommendation": rule["recommendation"],
                    "priority": rule["priority"]
                })
        
        # Analyze execution plan
        if plan_data.get("table_access"):
            for table in plan_data["table_access"]:
                if not plan_data["index_usage"]:
                    recommendations.append({
                        "type": "index",
                        "recommendation": f"Consider adding index for table {table}",
                        "priority": "high"
                    })
        
        return recommendations
    
    async def optimize_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Attempt to optimize a query"""
        try:
            # Analyze current query
            analysis = await self.analyze_query(query, 0.0)
            
            # Generate optimized query
            optimized_query = query
            changes_made = []
            
            # Apply optimization rules
            for recommendation in analysis.get("recommendations", []):
                if recommendation["type"] == "pattern":
                    new_query, change = self._apply_pattern_optimization(
                        optimized_query,
                        recommendation
                    )
                    if change:
                        optimized_query = new_query
                        changes_made.append(change)
            
            # Track optimization attempt
            self.optimization_stats["total_optimizations"] += 1
            if changes_made:
                self.optimization_stats["successful_optimizations"] += 1
            
            return {
                "original_query": query,
                "optimized_query": optimized_query,
                "changes": changes_made,
                "recommendations": analysis.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Query optimization failed: {str(e)}")
            self.optimization_stats["failed_optimizations"] += 1
            return {"error": str(e)}
    
    def _apply_pattern_optimization(
        self,
        query: str,
        recommendation: Dict[str, Any]
    ) -> Tuple[str, Optional[str]]:
        """Apply pattern-based query optimization"""
        if "SELECT *" in query.upper():
            # Replace SELECT * with specific columns
            return query.replace("*", "id, name, created_at"), \
                   "Replaced SELECT * with specific columns"
        
        return query, None
    
    async def get_optimization_stats(self) -> Dict[str, Any]:
        """Get query optimization statistics"""
        stats = {
            "patterns": len(self.patterns),
            "optimization_stats": self.optimization_stats,
            "slow_queries": sum(
                1 for p in self.patterns.values()
                if p.avg_duration > self.slow_query_threshold
            )
        }
        
        # Add pattern statistics
        stats["pattern_stats"] = {
            pattern: {
                "executions": p.executions,
                "avg_duration": p.avg_duration,
                "min_duration": p.min_duration,
                "max_duration": p.max_duration,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None
            }
            for pattern, p in self.patterns.items()
        }
        
        return stats
    
    async def cleanup_patterns(self):
        """Clean up expired query patterns"""
        cutoff = datetime.utcnow() - self.pattern_expiry
        expired = [
            pattern for pattern, data in self.patterns.items()
            if data.last_seen and data.last_seen < cutoff
        ]
        
        for pattern in expired:
            del self.patterns[pattern]

# Create global query optimizer
query_optimizer = QueryOptimizer() 