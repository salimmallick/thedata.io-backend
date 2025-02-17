from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime, timedelta
from ..monitoring.metrics import metrics
from ..storage.redis import redis
from ..auth.security import security
from ..utils.error_handling import RateLimitExceededError, error_handler
import httpx
from fastapi import Request
import json

logger = logging.getLogger(__name__)

class APIValidator:
    """Validator for API layer components"""
    
    def __init__(self):
        self.validation_thresholds = {
            "error_rate": 0.05,        # 5% error rate threshold
            "latency_p95": 1.0,        # 1 second p95 latency threshold
            "rate_limit_ratio": 0.1,   # 10% rate limit hits threshold
            "auth_failure_rate": 0.01  # 1% auth failure threshold
        }
        self.validation_interval = 300  # 5 minutes
        self.last_validation: Dict[str, datetime] = {}
    
    async def validate_rate_limiting(self) -> Dict[str, Any]:
        """Validate rate limiting functionality"""
        try:
            results = {
                "status": "healthy",
                "issues": [],
                "recommendations": []
            }
            
            # Get rate limit metrics
            rate_limit_hits = await redis.get_rate_limit_info("global")
            total_requests = metrics.http_requests_total._value.get(())
            
            if total_requests > 0:
                rate_limit_ratio = rate_limit_hits["count"] / total_requests
                
                if rate_limit_ratio > self.validation_thresholds["rate_limit_ratio"]:
                    results["status"] = "warning"
                    results["issues"].append(
                        f"High rate limit ratio: {rate_limit_ratio:.2%}"
                    )
                    results["recommendations"].append(
                        "Consider adjusting rate limit thresholds or investigating high traffic patterns"
                    )
            
            # Track metrics
            metrics.track_rate_limit_validation(rate_limit_hits["count"])
            
            return results
            
        except Exception as e:
            logger.error(f"Rate limit validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_authentication(self) -> Dict[str, Any]:
        """Validate authentication and authorization"""
        try:
            results = {
                "status": "healthy",
                "issues": [],
                "recommendations": []
            }
            
            # Get authentication metrics
            auth_failures = metrics.http_requests_total._value.get(("POST", "/auth", "401"), 0)
            total_auth_requests = sum(
                count for (method, path, status), count in metrics.http_requests_total._value.items()
                if path == "/auth"
            )
            
            if total_auth_requests > 0:
                failure_rate = auth_failures / total_auth_requests
                
                if failure_rate > self.validation_thresholds["auth_failure_rate"]:
                    results["status"] = "warning"
                    results["issues"].append(
                        f"High authentication failure rate: {failure_rate:.2%}"
                    )
                    results["recommendations"].append(
                        "Investigate potential security issues or client misconfiguration"
                    )
            
            # Check API key validation
            api_key_failures = metrics.http_requests_total._value.get(("GET", "/health", "401"), 0)
            if api_key_failures > 0:
                results["issues"].append(f"API key validation failures: {api_key_failures}")
            
            # Track metrics
            metrics.track_auth_validation(auth_failures)
            
            return results
            
        except Exception as e:
            logger.error(f"Authentication validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_request_validation(self) -> Dict[str, Any]:
        """Validate request validation and error handling"""
        try:
            results = {
                "status": "healthy",
                "issues": [],
                "recommendations": []
            }
            
            # Get validation error metrics
            validation_errors = error_handler.error_counts.get("validation", 0)
            total_requests = sum(metrics.http_requests_total._value.values())
            
            if total_requests > 0:
                error_rate = validation_errors / total_requests
                
                if error_rate > self.validation_thresholds["error_rate"]:
                    results["status"] = "warning"
                    results["issues"].append(
                        f"High validation error rate: {error_rate:.2%}"
                    )
                    results["recommendations"].append(
                        "Review client request patterns and improve validation documentation"
                    )
            
            # Check specific validation patterns
            error_patterns = await self._analyze_validation_errors()
            if error_patterns:
                results["recommendations"].extend(error_patterns)
            
            # Track metrics
            metrics.track_validation_errors(validation_errors)
            
            return results
            
        except Exception as e:
            logger.error(f"Request validation check failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_error_handling(self) -> Dict[str, Any]:
        """Validate error handling system"""
        try:
            results = {
                "status": "healthy",
                "issues": [],
                "recommendations": []
            }
            
            # Check error counts by type
            for error_type, count in error_handler.error_counts.items():
                if count > error_handler.error_thresholds.get(error_type, float('inf')):
                    results["status"] = "warning"
                    results["issues"].append(
                        f"Error threshold exceeded for {error_type}: {count} errors"
                    )
            
            # Check error response patterns
            error_responses = await self._analyze_error_responses()
            if error_responses["issues"]:
                results["issues"].extend(error_responses["issues"])
                results["recommendations"].extend(error_responses["recommendations"])
            
            # Track metrics
            metrics.track_error_handling_validation(len(results["issues"]))
            
            return results
            
        except Exception as e:
            logger.error(f"Error handling validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive API validation"""
        current_time = datetime.utcnow()
        
        # Check if validation is needed
        last_run = self.last_validation.get("api")
        if last_run and (current_time - last_run).total_seconds() < self.validation_interval:
            logger.info(f"Skipping validation, last run: {last_run}")
            return {"status": "skipped", "last_run": last_run.isoformat()}
        
        try:
            # Run all validations
            results = {
                "timestamp": current_time.isoformat(),
                "rate_limiting": await self.validate_rate_limiting(),
                "authentication": await self.validate_authentication(),
                "request_validation": await self.validate_request_validation(),
                "error_handling": await self.validate_error_handling()
            }
            
            # Update last validation time
            self.last_validation["api"] = current_time
            
            # Track validation metrics
            self._track_validation_metrics(results)
            
            return results
        except Exception as e:
            logger.error(f"API validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _analyze_validation_errors(self) -> List[str]:
        """Analyze validation error patterns"""
        recommendations = []
        
        # Analyze recent validation errors
        # This would typically involve analyzing logs or metrics
        # to identify common validation failure patterns
        
        return recommendations
    
    async def _analyze_error_responses(self) -> Dict[str, Any]:
        """Analyze error response patterns"""
        return {
            "issues": [],
            "recommendations": []
        }
    
    def _track_validation_metrics(self, results: Dict[str, Any]):
        """Track validation metrics"""
        try:
            # Track component health
            for component, result in results.items():
                if isinstance(result, dict):
                    metrics.track_api_component_health(
                        component=component,
                        status=result.get("status", "unknown")
                    )
            
            # Track issues count
            total_issues = sum(
                len(result.get("issues", []))
                for result in results.values()
                if isinstance(result, dict)
            )
            metrics.track_api_validation_issues(total_issues)
                
        except Exception as e:
            logger.error(f"Error tracking validation metrics: {str(e)}")

# Create global API validator
api_validator = APIValidator() 