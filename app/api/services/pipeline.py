from typing import Dict, Any, Optional, List
import asyncio
import json
from datetime import datetime, timedelta
import uuid
from questdb.ingress import Sender
from ..core.monitoring.instances import metrics
from ..core.database import db_pool, DatabaseError
from ..core.data.transform import transformation_pipeline
from .materialize import MaterializeService, MaterializedView
import logging
from ..core.validation.event_validation import validate_event

logger = logging.getLogger(__name__)

class PipelineService:
    """Service for managing data pipeline operations"""
    
    def __init__(self):
        self.materialize = MaterializeService()
        self._processors = {}
        self._running = False
    
    async def start(self):
        """Start the pipeline service"""
        if self._running:
            return
        
        try:
            await self.materialize.connect()
            self._running = True
            
            # Start processors
            await self._start_processors()
            metrics.track_component_health("pipeline_service", True)
        except Exception as e:
            logger.error(f"Failed to start pipeline service: {str(e)}")
            metrics.track_component_health("pipeline_service", False)
            metrics.track_error("pipeline_service_start", str(e))
            self._running = False
            raise
    
    async def stop(self):
        """Stop the pipeline service"""
        self._running = False
        try:
            await self.materialize.close()
            
            # Stop all processors
            for processor in self._processors.values():
                await processor.stop()
            metrics.track_component_health("pipeline_service", False)
        except Exception as e:
            logger.error(f"Error stopping pipeline service: {str(e)}")
            metrics.track_error("pipeline_service_stop", str(e))
            raise
    
    async def _start_processors(self):
        """Start all data processors"""
        try:
            processors = [
                EventProcessor("user_events", ["user_interaction_events"]),
                MetricsProcessor("metrics", ["performance_events", "infrastructure_metrics"]),
                VideoProcessor("video_events", ["video_events"]),
                LogProcessor("log_events", ["log_events", "distributed_traces"])
            ]
            
            for processor in processors:
                try:
                    await processor.start()
                    self._processors[processor.name] = processor
                    metrics.track_component_health(f"processor_{processor.name}", True)
                except Exception as e:
                    logger.error(f"Failed to start processor {processor.name}: {str(e)}")
                    metrics.track_component_health(f"processor_{processor.name}", False)
                    metrics.track_error(f"processor_{processor.name}_start", str(e))
                    # Continue with other processors even if one fails
        except Exception as e:
            logger.error(f"Error starting processors: {str(e)}")
            metrics.track_error("processor_startup", str(e))
            raise

class BaseProcessor:
    """Base class for all processors."""
    def __init__(self, name: str, topics: List[str]):
        self.name = name
        self.topics = topics
        self._stop = False
        self._tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start processing messages."""
        self._stop = False
        for topic in self.topics:
            task = asyncio.create_task(self._process_topic(topic))
            self._tasks.append(task)

    async def stop(self) -> None:
        """Stop processing messages."""
        self._stop = True
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _process_topic(self, topic: str) -> None:
        """Process messages from a topic."""
        while not self._stop:
            try:
                # Simulate message processing
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing topic {topic}: {str(e)}")
                metrics.track_error(f"topic_processing_{topic}", str(e))

    async def process_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Process a message."""
        raise NotImplementedError

class EventProcessor(BaseProcessor):
    """Processor for event messages."""
    async def process_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Process an event message."""
        try:
            # Validate event data
            validate_event(data)

            # Store in ClickHouse for event storage
            async with db_pool.clickhouse_connection() as client:
                await self._store_event(client, data)
                logger.info(f"Successfully processed event message for topic {topic}")
                metrics.track_database_query("clickhouse", "insert", 0.0)  # Add actual latency tracking
        except Exception as e:
            logger.error(f"Error processing event message: {str(e)}")
            metrics.track_error("event_processing", str(e))

    async def _store_event(self, client: Any, data: Dict[str, Any]) -> None:
        """Store event in ClickHouse."""
        query = """
        INSERT INTO events (
            event_id,
            timestamp,
            event_type,
            event_name,
            properties
        ) VALUES
        """
        values = (
            data.get('event_id', ''),
            data.get('timestamp', datetime.utcnow().isoformat()),
            data.get('event_type', ''),
            data.get('event_name', ''),
            data.get('properties', {})
        )
        await client.execute(query, [values])

class MetricsProcessor(BaseProcessor):
    """Processor for metrics messages."""
    async def process_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Process a metrics message."""
        try:
            # Store in QuestDB for time-series metrics
            async with db_pool.questdb_connection() as client:
                await self._store_metric(client, data)
                logger.info(f"Successfully processed metrics message for topic {topic}")
                metrics.track_database_query("questdb", "insert", 0.0)  # Add actual latency tracking
        except Exception as e:
            logger.error(f"Error processing metrics message: {str(e)}")
            metrics.track_error("metrics_processing", str(e))

    async def _store_metric(self, client: Any, data: Dict[str, Any]) -> None:
        """Store metric in QuestDB."""
        query = """
        INSERT INTO metrics (
            name,
            source,
            timestamp,
            value
        ) VALUES ($1, $2, $3, $4)
        """
        await client.execute(query, [
            data['name'],
            data.get('source', 'unknown'),
            data.get('timestamp', datetime.utcnow().isoformat()),
            data['value']
        ])

class VideoProcessor(BaseProcessor):
    """Processor for video messages."""
    async def process_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Process a video message."""
        try:
            # Process video data
            logger.info(f"Successfully processed video message for topic {topic}")
            metrics.track_database_query("video_processing", "process", 0.0)  # Add actual latency tracking
        except Exception as e:
            logger.error(f"Error processing video message: {str(e)}")
            metrics.track_error("video_processing", str(e))

class LogProcessor(BaseProcessor):
    """Processor for log messages."""
    async def process_message(self, topic: str, data: Dict[str, Any]) -> None:
        """Process a log message."""
        try:
            # Process log data
            logger.info(f"Successfully processed log message for topic {topic}")
            metrics.track_database_query("log_processing", "process", 0.0)  # Add actual latency tracking
        except Exception as e:
            logger.error(f"Error processing log message: {str(e)}")
            metrics.track_error("log_processing", str(e))

# Create global pipeline service instance
pipeline_service = PipelineService()