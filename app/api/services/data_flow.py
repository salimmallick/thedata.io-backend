from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import asyncio

from ..core.database import db_pool, DatabaseError

from .pipeline import pipeline_service
from .materialize import materialize_service

logger = logging.getLogger(__name__)

class DataFlowService:
    """Service for managing data flow between storage systems"""
    
    def __init__(self):
        self._running = False
        self._tasks = []
    
    async def start(self):
        """Start the data flow service"""
        if self._running:
            return
        
        self._running = True
        
        # Start pipeline service
        await pipeline_service.start()
        
        # Start data flow tasks
        self._tasks.extend([
            asyncio.create_task(self._archive_old_data()),
            asyncio.create_task(self._sync_materialized_views()),
            asyncio.create_task(self._monitor_data_flow())
        ])
    
    async def stop(self):
        """Stop the data flow service"""
        self._running = False
        
        # Stop pipeline service
        await pipeline_service.stop()
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
    
    async def _archive_old_data(self):
        """Archive old data based on retention policies"""
        while self._running:
            try:
                async with db_pool.postgres_connection() as conn:
                    # Get retention policies
                    policies = await conn.fetch(
                        "SELECT * FROM retention_policies WHERE archival_enabled = true"
                    )
                    
                    for policy in policies:
                        # Archive data older than retention period
                        archive_date = datetime.utcnow() - timedelta(days=policy['retention_days'])
                        
                        async with db_pool.clickhouse_connection() as client:
                            # Move data to archive table
                            await client.execute(f"""
                                INSERT INTO {policy['data_type']}_archive
                                SELECT *
                                FROM {policy['data_type']}
                                WHERE timestamp < %(archive_date)s
                            """, {'archive_date': archive_date})
                            
                            # Delete archived data
                            await client.execute(f"""
                                ALTER TABLE {policy['data_type']}
                                DELETE WHERE timestamp < %(archive_date)s
                            """, {'archive_date': archive_date})
                
                # Sleep for 1 hour before next archive check
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Error in data archival: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _sync_materialized_views(self):
        """Sync materialized views based on refresh intervals"""
        while self._running:
            try:
                now = datetime.utcnow()
                
                # Check each view's refresh interval
                for view in materialize_service._views.values():
                    # Parse refresh interval string to timedelta
                    interval_parts = view.refresh_interval.split()
                    if len(interval_parts) != 2:
                        logger.error(f"Invalid refresh interval format for view {view.name}: {view.refresh_interval}")
                        continue
                        
                    value = int(interval_parts[0])
                    unit = interval_parts[1].lower()
                    
                    if unit.endswith('s'):  # Remove plural 's'
                        unit = unit[:-1]
                        
                    # Convert to seconds
                    seconds = {
                        'second': 1,
                        'minute': 60,
                        'hour': 3600,
                        'day': 86400
                    }.get(unit)
                    
                    if not seconds:
                        logger.error(f"Invalid time unit in refresh interval for view {view.name}: {unit}")
                        continue
                        
                    interval = timedelta(seconds=value * seconds)
                    
                    if (not view.last_refresh or 
                        now - view.last_refresh > interval):
                        # Refresh the view
                        async with db_pool.postgres_connection() as conn:
                            await conn.execute(f"REFRESH MATERIALIZED VIEW {view.name}")
                            view.last_refresh = now
                
                # Sleep for 10 seconds before next check
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in view synchronization: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _monitor_data_flow(self):
        """Monitor data flow and report metrics"""
        while self._running:
            try:
                metrics = {
                    'timestamp': datetime.utcnow(),
                    'metrics': {}
                }
                
                # Get event counts from ClickHouse
                async with db_pool.clickhouse_connection() as client:
                    for table in ['user_interaction_events', 'performance_events', 
                                'video_events', 'log_events']:
                        count = await client.execute(f"""
                            SELECT count()
                            FROM {table}
                            WHERE timestamp >= now() - INTERVAL 5 MINUTE
                        """)
                        metrics['metrics'][f'{table}_count_5m'] = count[0][0]
                
                # Store metrics in QuestDB
                async with db_pool.questdb_connection() as sender:
                    await sender.write(
                        'data_flow_metrics',
                        symbols={'metric_type': 'event_count'},
                        columns=metrics['metrics']
                    )
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in data flow monitoring: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute

# Create global service instance
data_flow_service = DataFlowService() 