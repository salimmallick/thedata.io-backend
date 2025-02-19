import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import HTTPException
import logging
import psutil

from ..models.admin import SystemConfig, MetricsConfig, AlertConfig
from ..core.config import settings
from ..core.database import db_pool
from ..core.monitoring.instances import metrics
from ..core.monitoring.resource_tracking import resource_tracker
from ..core.storage.query_optimization import QueryOptimizer

logger = logging.getLogger(__name__)

class AdminService:
    """Service for handling administration tasks"""
    
    def __init__(self):
        self.config_path = os.getenv("CONFIG_PATH", "config/system_config.json")
        self._load_config()
        self.query_optimizer = QueryOptimizer()
        self.metrics_collector = metrics
        self._resource_tracker_initialized = False
        
    async def _ensure_resource_tracker(self):
        """Ensure resource tracker is initialized"""
        if not self._resource_tracker_initialized:
            try:
                await resource_tracker.start_tracking()
                self._resource_tracker_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize resource tracker: {e}")
                
    def _get_basic_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics without resource tracker"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "above_threshold": cpu_percent > 80
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                    "above_threshold": memory.percent > 85
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logger.error(f"Error getting basic metrics: {e}")
            return {
                "error": "Failed to get system metrics",
                "message": str(e)
            }
            
    async def get_system_status(self) -> dict:
        """Get the current system status."""
        try:
            # Try to ensure resource tracker is running
            await self._ensure_resource_tracker()
            
            if self._resource_tracker_initialized:
                try:
                    metrics = resource_tracker.get_current_metrics()
                    health = resource_tracker.check_resource_health()
                    return {
                        "status": "ok" if health else "warning",
                        "metrics": metrics,
                        "health": health
                    }
                except Exception as tracker_error:
                    logger.warning(f"Resource tracker failed, falling back to basic metrics: {tracker_error}")
            
            # Fallback to basic metrics if resource tracker is not available
            basic_metrics = self._get_basic_metrics()
            return {
                "status": "ok" if "error" not in basic_metrics else "warning",
                "metrics": basic_metrics,
                "health": True if "error" not in basic_metrics else False
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get system status"
            )
        
    def _load_config(self) -> None:
        """Load system configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = SystemConfig(**json.load(f))
        except FileNotFoundError:
            # Initialize with default config if file doesn't exist
            self.config = self._get_default_config()
            self._save_config()
            
    def _save_config(self) -> None:
        """Save current configuration to file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config.dict(), f, indent=2)
            
    def _get_default_config(self) -> SystemConfig:
        """Get default system configuration"""
        return SystemConfig(
            resource_tracking={
                "interval": 60,
                "retention": 7
            },
            query_optimization={
                "slow_query_threshold": 1.0,
                "pattern_retention": 30
            },
            metrics={
                "collection_enabled": True,
                "intervals": {
                    "resource": 60,
                    "query": 60,
                    "system": 60
                },
                "retention": {
                    "resource": 7,
                    "query": 30,
                    "system": 7
                }
            },
            alerts={
                "enabled": True,
                "channels": ["email"],
                "thresholds": {
                    "cpu": 80.0,
                    "memory": 85.0,
                    "disk": 85.0,
                    "network": 100.0
                },
                "notification_settings": {
                    "email": {},
                    "slack": {},
                    "pagerduty": {}
                }
            }
        )
            
    def get_config(self) -> SystemConfig:
        """Get current system configuration"""
        return self.config
        
    def update_config(self, new_config: SystemConfig) -> SystemConfig:
        """Update system configuration"""
        self.config = new_config
        self._save_config()
        
        # Apply new configuration
        resource_tracker.update_config(new_config.resource_tracking)
        self.query_optimizer.update_config(new_config.query_optimization)
        self.metrics_collector.update_config(new_config.metrics)
        
        return self.config
        
    def get_metrics_config(self) -> MetricsConfig:
        """Get metrics configuration"""
        return self.config.metrics
        
    def update_metrics_config(self, new_config: MetricsConfig) -> MetricsConfig:
        """Update metrics configuration"""
        self.config.metrics = new_config
        self._save_config()
        self.metrics_collector.update_config(new_config)
        return new_config
        
    def get_alerts_config(self) -> AlertConfig:
        """Get alerts configuration"""
        return self.config.alerts
        
    def update_alerts_config(self, new_config: AlertConfig) -> AlertConfig:
        """Update alerts configuration"""
        self.config.alerts = new_config
        self._save_config()
        return new_config
        
    def _get_system_uptime(self) -> float:
        """Get system uptime in seconds"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
        except:
            return 0.0

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active system alerts"""
        alerts = []
        
        # Check system metrics
        metrics = resource_tracker.get_system_metrics()
        if "error" not in metrics:
            if metrics["cpu"]["above_threshold"]:
                alerts.append({
                    "id": "cpu_usage",
                    "type": "system",
                    "severity": "warning",
                    "message": f"CPU usage is high ({metrics['cpu']['usage_percent']}%)",
                    "timestamp": datetime.now().isoformat()
                })
                
            if metrics["memory"]["above_threshold"]:
                alerts.append({
                    "id": "memory_usage",
                    "type": "system",
                    "severity": "warning",
                    "message": f"Memory usage is high ({metrics['memory']['percent']}%)",
                    "timestamp": datetime.now().isoformat()
                })
                
            if metrics["disk"]["percent"] > 85:
                alerts.append({
                    "id": "disk_usage",
                    "type": "system",
                    "severity": "warning",
                    "message": f"Disk usage is high ({metrics['disk']['percent']}%)",
                    "timestamp": datetime.now().isoformat()
                })
        
        return alerts

    def acknowledge_alert(self, alert_id: str) -> None:
        """Acknowledge a system alert"""
        # For now, just validate the alert ID
        valid_alert_ids = ["cpu_usage", "memory_usage", "disk_usage"]
        if alert_id not in valid_alert_ids:
            raise ValueError(f"Invalid alert ID: {alert_id}")
        # In a real implementation, we would update the alert status in a database 