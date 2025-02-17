from typing import Dict, Any, Optional
import psutil
import asyncio
import logging
from datetime import datetime, timedelta
from .metrics import metrics
import time
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

class ResourceTracker:
    """Comprehensive system resource tracking and monitoring"""
    
    def __init__(self):
        self.tracking_interval = 60  # seconds
        self.history_retention = timedelta(days=7)
        self.cpu_threshold = 80  # 80% CPU usage threshold
        self.memory_threshold = 85  # 85% memory usage threshold
        
        self.resource_history: Dict[str, list] = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
        self._tracking_task = None
        self.process = psutil.Process()
        self.system_metrics = {
            "cpu_percent": Gauge(
                "system_cpu_percent",
                "System CPU usage percentage"
            ),
            "memory_percent": Gauge(
                "system_memory_percent",
                "System memory usage percentage"
            ),
            "disk_usage": Gauge(
                "system_disk_usage_percent",
                "System disk usage percentage"
            ),
            "open_files": Gauge(
                "system_open_files",
                "Number of open files"
            ),
            "network_connections": Gauge(
                "system_network_connections",
                "Number of network connections"
            )
        }
    
    async def start_tracking(self):
        """Start resource tracking"""
        self._tracking_task = asyncio.create_task(self._tracking_loop())
        logger.info("Resource tracking started")
    
    async def stop_tracking(self):
        """Stop resource tracking"""
        if self._tracking_task:
            self._tracking_task.cancel()
            try:
                await self._tracking_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource tracking stopped")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics snapshot"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "above_threshold": cpu_percent > self.cpu_threshold
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                    "above_threshold": memory.percent > self.memory_threshold
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {
                "error": "Failed to get system metrics",
                "message": str(e)
            }
    
    def check_resource_health(self) -> Dict[str, bool]:
        """Check if resources are within healthy thresholds"""
        metrics = self.get_current_metrics()
        
        if "error" in metrics:
            return {"healthy": False, "error": metrics["error"]}
        
        return {
            "healthy": not (
                metrics["cpu"]["above_threshold"] or 
                metrics["memory"]["above_threshold"]
            ),
            "cpu_healthy": not metrics["cpu"]["above_threshold"],
            "memory_healthy": not metrics["memory"]["above_threshold"]
        }
    
    async def _tracking_loop(self):
        """Main tracking loop"""
        while True:
            try:
                await self._collect_metrics()
                await self._cleanup_history()
                await asyncio.sleep(self.tracking_interval)
            except Exception as e:
                logger.error(f"Error in resource tracking: {str(e)}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _collect_metrics(self):
        """Collect detailed system resource metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_times = psutil.cpu_times()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # Network metrics
        network = psutil.net_io_counters()
        
        # Store metrics
        timestamp = datetime.utcnow()
        metrics_data = {
            "timestamp": timestamp,
            "cpu": {
                "usage_percent": cpu_percent,
                "user_time": cpu_times.user,
                "system_time": cpu_times.system,
                "idle_time": cpu_times.idle,
                "above_threshold": any(p > self.cpu_threshold for p in cpu_percent if isinstance(cpu_percent, list))
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "swap_used": swap.used,
                "swap_percent": swap.percent,
                "above_threshold": memory.percent > self.memory_threshold
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        }
        
        # Update history and metrics
        self._update_history(metrics_data)
        self._update_prometheus_metrics(metrics_data)
    
    def _update_history(self, metrics_data: Dict[str, Any]):
        """Update resource history"""
        for resource_type in self.resource_history:
            if resource_type in metrics_data:
                self.resource_history[resource_type].append({
                    "timestamp": metrics_data["timestamp"],
                    "data": metrics_data[resource_type]
                })
    
    def _update_prometheus_metrics(self, metrics_data: Dict[str, Any]):
        """Update Prometheus metrics"""
        # CPU metrics
        if isinstance(metrics_data["cpu"]["usage_percent"], list):
            for i, cpu_percent in enumerate(metrics_data["cpu"]["usage_percent"]):
                metrics.cpu_usage_percent.labels(cpu=f"cpu{i}").set(cpu_percent)
        else:
            metrics.cpu_usage_percent.labels(cpu="total").set(metrics_data["cpu"]["usage_percent"])
        
        # Memory metrics
        metrics.memory_usage_bytes.set(metrics_data["memory"]["used"])
        metrics.memory_usage_percent.set(metrics_data["memory"]["percent"])
        
        # Disk metrics
        metrics.disk_usage_bytes.set(metrics_data["disk"]["used"])
        metrics.disk_usage_percent.set(metrics_data["disk"]["percent"])
        
        # Network metrics
        metrics.network_bytes_sent.set(metrics_data["network"]["bytes_sent"])
        metrics.network_bytes_received.set(metrics_data["network"]["bytes_recv"])
    
    async def _cleanup_history(self):
        """Clean up old history entries"""
        cutoff_time = datetime.utcnow() - self.history_retention
        for resource_type in self.resource_history:
            self.resource_history[resource_type] = [
                entry for entry in self.resource_history[resource_type]
                if entry["timestamp"] > cutoff_time
            ]
    
    async def get_resource_usage(
        self,
        resource_type: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get historical resource usage data"""
        if time_range is None:
            time_range = self.history_retention
        
        cutoff_time = datetime.utcnow() - time_range
        
        if resource_type:
            if resource_type not in self.resource_history:
                raise ValueError(f"Invalid resource type: {resource_type}")
            
            return {
                resource_type: [
                    entry for entry in self.resource_history[resource_type]
                    if entry["timestamp"] > cutoff_time
                ]
            }
        
        return {
            resource_type: [
                entry for entry in history
                if entry["timestamp"] > cutoff_time
            ]
            for resource_type, history in self.resource_history.items()
        }
    
    async def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of current resource usage"""
        current_metrics = self.get_current_metrics()
        health_status = self.check_resource_health()
        
        return {
            "current_metrics": current_metrics,
            "health_status": health_status,
            "history_size": {
                resource_type: len(history)
                for resource_type, history in self.resource_history.items()
            }
        }

    def track_resources(self) -> Dict[str, Any]:
        """Track current system resource usage."""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent()
            self.system_metrics["cpu_percent"].set(cpu_percent)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            self.system_metrics["memory_percent"].set(memory.percent)
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            self.system_metrics["disk_usage"].set(disk.percent)
            
            # Get number of open files
            open_files = len(self.process.open_files())
            self.system_metrics["open_files"].set(open_files)
            
            # Get number of network connections
            connections = len(self.process.connections())
            self.system_metrics["network_connections"].set(connections)
            
            return {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_usage_percent": disk.percent,
                "open_files": open_files,
                "network_connections": connections
            }
            
        except Exception as e:
            logger.error(f"Error tracking resources: {str(e)}")
            return {}

# Create global instance
resource_tracker = ResourceTracker() 