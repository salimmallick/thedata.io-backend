"""
Base health check functionality without metrics dependencies.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseHealthChecker:
    """Base health checker without metrics dependencies."""
    
    def __init__(self):
        self.components = {
            'postgres': False,
            'clickhouse': False,
            'questdb': False,
            'nats': False,
            'redis': False
        }
    
    async def check_postgres(self, db_pool) -> bool:
        """Check PostgreSQL database health."""
        try:
            async with db_pool.get_postgres_conn() as conn:
                await conn.execute('SELECT 1')
            self.components['postgres'] = True
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
            self.components['postgres'] = False
            return False

    async def check_clickhouse(self, db_pool) -> bool:
        """Check ClickHouse database health."""
        try:
            async with db_pool.get_clickhouse_client() as client:
                client.command('SELECT 1')
            self.components['clickhouse'] = True
            return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {str(e)}")
            self.components['clickhouse'] = False
            return False

    async def check_questdb(self, db_pool) -> bool:
        """Check QuestDB health."""
        try:
            async with db_pool.get_questdb_sender() as sender:
                await sender.ping()
            self.components['questdb'] = True
            return True
        except Exception as e:
            logger.error(f"QuestDB health check failed: {str(e)}")
            self.components['questdb'] = False
            return False

    async def check_nats(self, db_pool) -> bool:
        """Check NATS health."""
        try:
            async with db_pool.get_nats_client() as nc:
                await nc.ping()
            self.components['nats'] = True
            return True
        except Exception as e:
            logger.error(f"NATS health check failed: {str(e)}")
            self.components['nats'] = False
            return False

    async def check_redis(self, db_pool) -> bool:
        """Check Redis health."""
        try:
            async with db_pool.redis_connection() as redis:
                await redis.ping()
            self.components['redis'] = True
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            self.components['redis'] = False
            return False

    async def check_all(self, db_pool) -> Dict[str, Any]:
        """Check health of all components."""
        results = {}
        
        # Run all checks
        results['postgres'] = await self.check_postgres(db_pool)
        results['clickhouse'] = await self.check_clickhouse(db_pool)
        results['questdb'] = await self.check_questdb(db_pool)
        results['nats'] = await self.check_nats(db_pool)
        results['redis'] = await self.check_redis(db_pool)
        
        # Overall status
        results['status'] = all(results.values())
        
        return results 