from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime, timedelta
from ..storage.nats import nats_client
from ..monitoring.circuit_breaker import circuit_breakers
from ..monitoring.metrics import metrics
import nats
from nats.js.api import StreamConfig, ConsumerConfig, DeliverPolicy
import json

logger = logging.getLogger(__name__)

class MessageQueueValidator:
    """Comprehensive NATS message queue validation"""
    
    def __init__(self):
        self.validation_interval = 300  # 5 minutes
        self.last_validation: Dict[str, datetime] = {}
        self.validation_thresholds = {
            "message_lag": 100,        # Maximum acceptable message lag
            "ack_latency": 1.0,        # Maximum acceptable ack latency (seconds)
            "delivery_rate": 0.99,     # Minimum acceptable delivery rate (99%)
            "memory_usage": 0.8,       # Maximum memory usage (80%)
            "consumer_inactive": 300    # Maximum consumer inactivity (seconds)
        }
    
    async def validate_streams(self) -> Dict[str, Any]:
        """Validate NATS streams health and performance"""
        try:
            nc = await nats.connect()
            js = nc.jetstream()
            
            results = {
                "streams": {},
                "issues": [],
                "recommendations": []
            }
            
            # Get all streams
            streams = await js.streams_info()
            
            for stream in streams:
                stream_info = await js.stream_info(stream.config.name)
                
                # Calculate stream metrics
                messages_stored = stream_info.state.messages
                bytes_stored = stream_info.state.bytes
                consumers = len(stream_info.state.consumer_count)
                
                stream_status = {
                    "name": stream.config.name,
                    "messages": messages_stored,
                    "bytes": bytes_stored,
                    "consumers": consumers,
                    "subjects": stream.config.subjects,
                    "retention": stream.config.retention.name,
                    "storage": stream.config.storage.name,
                    "health": "healthy"
                }
                
                # Check for issues
                if messages_stored == 0 and consumers > 0:
                    stream_status["health"] = "warning"
                    results["issues"].append(f"Stream {stream.config.name} has no messages but has active consumers")
                
                if bytes_stored > stream.config.max_bytes * self.validation_thresholds["memory_usage"]:
                    stream_status["health"] = "warning"
                    results["recommendations"].append(
                        f"Stream {stream.config.name} is approaching storage limit"
                    )
                
                results["streams"][stream.config.name] = stream_status
                
                # Track metrics
                metrics.track_stream_stats(
                    stream=stream.config.name,
                    messages=messages_stored,
                    bytes=bytes_stored,
                    consumers=consumers
                )
            
            await nc.close()
            return results
            
        except Exception as e:
            logger.error(f"Stream validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_consumers(self) -> Dict[str, Any]:
        """Validate consumer groups and their performance"""
        try:
            nc = await nats.connect()
            js = nc.jetstream()
            
            results = {
                "consumers": {},
                "issues": [],
                "recommendations": []
            }
            
            # Get all streams
            streams = await js.streams_info()
            
            for stream in streams:
                # Get consumers for each stream
                consumers = await js.consumers_info(stream.config.name)
                
                for consumer in consumers:
                    consumer_info = await js.consumer_info(
                        stream.config.name,
                        consumer.name
                    )
                    
                    # Calculate consumer metrics
                    num_pending = consumer_info.num_pending
                    num_ack_pending = consumer_info.num_ack_pending
                    delivery_count = consumer_info.delivered.consumer_seq
                    ack_count = consumer_info.ack_floor.consumer_seq
                    
                    if delivery_count > 0:
                        delivery_rate = ack_count / delivery_count
                    else:
                        delivery_rate = 1.0
                    
                    consumer_status = {
                        "name": consumer.name,
                        "stream": stream.config.name,
                        "pending": num_pending,
                        "ack_pending": num_ack_pending,
                        "delivery_rate": delivery_rate,
                        "last_active": consumer_info.last_active,
                        "health": "healthy"
                    }
                    
                    # Check for issues
                    if delivery_rate < self.validation_thresholds["delivery_rate"]:
                        consumer_status["health"] = "warning"
                        results["issues"].append(
                            f"Consumer {consumer.name} has low delivery rate: {delivery_rate:.2%}"
                        )
                    
                    if num_pending > self.validation_thresholds["message_lag"]:
                        consumer_status["health"] = "warning"
                        results["issues"].append(
                            f"Consumer {consumer.name} has high message lag: {num_pending} messages"
                        )
                    
                    inactive_time = (datetime.utcnow() - consumer_info.last_active).total_seconds()
                    if inactive_time > self.validation_thresholds["consumer_inactive"]:
                        consumer_status["health"] = "warning"
                        results["issues"].append(
                            f"Consumer {consumer.name} has been inactive for {inactive_time:.0f} seconds"
                        )
                    
                    results["consumers"][f"{stream.config.name}/{consumer.name}"] = consumer_status
                    
                    # Track metrics
                    metrics.track_consumer_stats(
                        stream=stream.config.name,
                        consumer=consumer.name,
                        pending=num_pending,
                        delivery_rate=delivery_rate
                    )
            
            await nc.close()
            return results
            
        except Exception as e:
            logger.error(f"Consumer validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_message_delivery(self) -> Dict[str, Any]:
        """Validate message delivery and performance"""
        try:
            nc = await nats.connect()
            js = nc.jetstream()
            
            results = {
                "delivery_stats": {},
                "issues": [],
                "recommendations": []
            }
            
            # Test message delivery for each stream
            streams = await js.streams_info()
            
            for stream in streams:
                # Send test message
                subject = f"_VALIDATION_.{stream.config.name}"
                message = {
                    "validation_id": str(datetime.utcnow().timestamp()),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                start_time = asyncio.get_event_loop().time()
                
                # Publish message
                ack = await js.publish(subject, json.dumps(message).encode())
                
                # Subscribe and wait for message
                sub = await js.subscribe(subject)
                msg = await sub.next_msg(timeout=5.0)
                
                delivery_time = asyncio.get_event_loop().time() - start_time
                
                # Acknowledge message
                await msg.ack()
                
                delivery_stats = {
                    "stream": stream.config.name,
                    "delivery_time": delivery_time,
                    "sequence": ack.sequence,
                    "health": "healthy"
                }
                
                # Check for issues
                if delivery_time > self.validation_thresholds["ack_latency"]:
                    delivery_stats["health"] = "warning"
                    results["issues"].append(
                        f"High delivery latency in stream {stream.config.name}: {delivery_time:.3f}s"
                    )
                
                results["delivery_stats"][stream.config.name] = delivery_stats
                
                # Track metrics
                metrics.track_delivery_time(
                    stream=stream.config.name,
                    delivery_time=delivery_time
                )
                
                # Cleanup test message
                await js.purge_stream(stream.config.name, subject=subject)
            
            await nc.close()
            return results
            
        except Exception as e:
            logger.error(f"Message delivery validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def validate_backpressure(self) -> Dict[str, Any]:
        """Validate backpressure handling"""
        try:
            nc = await nats.connect()
            js = nc.jetstream()
            
            results = {
                "backpressure_stats": {},
                "issues": [],
                "recommendations": []
            }
            
            # Test backpressure for each stream
            streams = await js.streams_info()
            
            for stream in streams:
                # Calculate current usage
                info = await js.stream_info(stream.config.name)
                current_size = info.state.bytes
                max_size = stream.config.max_bytes
                
                if max_size > 0:
                    usage_ratio = current_size / max_size
                else:
                    usage_ratio = 0
                
                backpressure_stats = {
                    "stream": stream.config.name,
                    "current_size": current_size,
                    "max_size": max_size,
                    "usage_ratio": usage_ratio,
                    "health": "healthy"
                }
                
                # Check for issues
                if usage_ratio > self.validation_thresholds["memory_usage"]:
                    backpressure_stats["health"] = "warning"
                    results["issues"].append(
                        f"High memory usage in stream {stream.config.name}: {usage_ratio:.2%}"
                    )
                    results["recommendations"].append(
                        f"Consider increasing max_bytes for stream {stream.config.name}"
                    )
                
                results["backpressure_stats"][stream.config.name] = backpressure_stats
                
                # Track metrics
                metrics.track_stream_usage(
                    stream=stream.config.name,
                    usage_ratio=usage_ratio
                )
            
            await nc.close()
            return results
            
        except Exception as e:
            logger.error(f"Backpressure validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive message queue validation"""
        current_time = datetime.utcnow()
        
        # Check if validation is needed
        last_run = self.last_validation.get("nats")
        if last_run and (current_time - last_run).total_seconds() < self.validation_interval:
            logger.info(f"Skipping validation, last run: {last_run}")
            return {"status": "skipped", "last_run": last_run.isoformat()}
        
        try:
            # Run all validations
            results = {
                "timestamp": current_time.isoformat(),
                "streams": await self.validate_streams(),
                "consumers": await self.validate_consumers(),
                "delivery": await self.validate_message_delivery(),
                "backpressure": await self.validate_backpressure()
            }
            
            # Update last validation time
            self.last_validation["nats"] = current_time
            
            # Track validation metrics
            self._track_validation_metrics(results)
            
            return results
        except Exception as e:
            logger.error(f"Message queue validation failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _track_validation_metrics(self, results: Dict[str, Any]):
        """Track validation metrics"""
        try:
            # Track stream metrics
            for stream_name, stream_stats in results["streams"].get("streams", {}).items():
                metrics.track_stream_health(
                    stream=stream_name,
                    health=stream_stats["health"]
                )
            
            # Track consumer metrics
            for consumer_key, consumer_stats in results["consumers"].get("consumers", {}).items():
                metrics.track_consumer_health(
                    stream=consumer_stats["stream"],
                    consumer=consumer_stats["name"],
                    health=consumer_stats["health"]
                )
            
            # Track delivery metrics
            for stream_name, delivery_stats in results["delivery"].get("delivery_stats", {}).items():
                metrics.track_delivery_health(
                    stream=stream_name,
                    health=delivery_stats["health"]
                )
            
            # Track backpressure metrics
            for stream_name, bp_stats in results["backpressure"].get("backpressure_stats", {}).items():
                metrics.track_backpressure(
                    stream=stream_name,
                    usage_ratio=bp_stats["usage_ratio"]
                )
                
        except Exception as e:
            logger.error(f"Error tracking validation metrics: {str(e)}")

# Create global message queue validator
message_queue_validator = MessageQueueValidator() 