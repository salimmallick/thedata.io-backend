from dagster import sensor, RunRequest, SensorResult, DefaultSensorStatus
from typing import Dict, Any, List
import numpy as np
from datetime import datetime, timedelta
import logging
from ...api.services.materialize import materialize_service
from ...api.core.metrics import metrics

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Anomaly detection using statistical methods"""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.thresholds: Dict[str, Dict[str, float]] = {}
    
    async def calculate_thresholds(self, metric_name: str, values: List[float]) -> Dict[str, float]:
        """Calculate dynamic thresholds using statistical methods"""
        if len(values) < self.window_size:
            return {}
            
        # Calculate basic statistics
        mean = np.mean(values)
        std = np.std(values)
        
        return {
            "upper_bound": mean + 3 * std,  # 3-sigma rule
            "lower_bound": mean - 3 * std,
            "mean": mean,
            "std": std
        }
    
    async def detect_anomalies(
        self,
        metric_name: str,
        current_value: float,
        historical_values: List[float]
    ) -> Dict[str, Any]:
        """Detect anomalies using multiple methods"""
        # Update thresholds
        self.thresholds[metric_name] = await self.calculate_thresholds(
            metric_name,
            historical_values
        )
        
        if not self.thresholds[metric_name]:
            return {"is_anomaly": False, "reason": "insufficient_data"}
        
        thresholds = self.thresholds[metric_name]
        
        # Check for anomalies
        is_anomaly = False
        reasons = []
        
        # Statistical anomaly
        if current_value > thresholds["upper_bound"] or current_value < thresholds["lower_bound"]:
            is_anomaly = True
            reasons.append("statistical_threshold")
        
        # Sudden change detection
        if len(historical_values) >= 2:
            last_value = historical_values[-1]
            change_rate = abs((current_value - last_value) / last_value) if last_value != 0 else float('inf')
            if change_rate > 0.5:  # 50% change
                is_anomaly = True
                reasons.append("sudden_change")
        
        return {
            "is_anomaly": is_anomaly,
            "reasons": reasons,
            "thresholds": thresholds,
            "current_value": current_value
        }

# Create global anomaly detector
anomaly_detector = AnomalyDetector()

@sensor(
    job_name="engineering_metrics",
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.RUNNING
)
def performance_anomaly_sensor(context):
    """Sensor to detect performance anomalies"""
    try:
        # Get performance metrics from materialized view
        query = """
        SELECT
            window,
            avg_duration,
            error_count,
            request_count
        FROM mv_performance_realtime
        ORDER BY window DESC
        LIMIT 60
        """
        
        results = materialize_service.execute_query(query)
        
        anomalies = []
        for metric in ["avg_duration", "error_rate"]:
            values = [row[metric] for row in results]
            current_value = values[0]
            historical_values = values[1:]
            
            analysis = anomaly_detector.detect_anomalies(
                metric,
                current_value,
                historical_values
            )
            
            if analysis["is_anomaly"]:
                anomalies.append({
                    "metric": metric,
                    "analysis": analysis
                })
        
        if anomalies:
            # Track anomaly metrics
            for anomaly in anomalies:
                metrics.track_anomaly(
                    metric=anomaly["metric"],
                    value=anomaly["analysis"]["current_value"],
                    reasons=anomaly["analysis"]["reasons"]
                )
            
            # Trigger investigation job
            return RunRequest(
                run_key=f"performance_anomaly_{datetime.now().isoformat()}",
                run_config={
                    "ops": {
                        "investigate_anomalies": {
                            "config": {
                                "anomalies": anomalies
                            }
                        }
                    }
                }
            )
        
        return SkipReason(f"No anomalies detected at {datetime.now().isoformat()}")
        
    except Exception as e:
        logger.error(f"Error in performance anomaly sensor: {str(e)}")
        return SkipReason(f"Error: {str(e)}")

@sensor(
    job_name="video_metrics",
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.RUNNING
)
def video_quality_sensor(context):
    """Sensor to detect video quality issues"""
    try:
        # Get video quality metrics from materialized view
        query = """
        SELECT
            window,
            avg_quality_score,
            avg_buffering_ratio,
            error_count
        FROM mv_video_quality_realtime
        ORDER BY window DESC
        LIMIT 60
        """
        
        results = materialize_service.execute_query(query)
        
        anomalies = []
        for metric in ["avg_quality_score", "avg_buffering_ratio", "error_count"]:
            values = [row[metric] for row in results]
            current_value = values[0]
            historical_values = values[1:]
            
            analysis = anomaly_detector.detect_anomalies(
                metric,
                current_value,
                historical_values
            )
            
            if analysis["is_anomaly"]:
                anomalies.append({
                    "metric": metric,
                    "analysis": analysis
                })
        
        if anomalies:
            # Track video quality issues
            for anomaly in anomalies:
                metrics.track_video_quality_issue(
                    metric=anomaly["metric"],
                    value=anomaly["analysis"]["current_value"],
                    reasons=anomaly["analysis"]["reasons"]
                )
            
            # Trigger investigation job
            return RunRequest(
                run_key=f"video_quality_issue_{datetime.now().isoformat()}",
                run_config={
                    "ops": {
                        "investigate_video_quality": {
                            "config": {
                                "anomalies": anomalies
                            }
                        }
                    }
                }
            )
        
        return SkipReason(f"No video quality issues detected at {datetime.now().isoformat()}")
        
    except Exception as e:
        logger.error(f"Error in video quality sensor: {str(e)}")
        return SkipReason(f"Error: {str(e)}") 