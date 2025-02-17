import logging
import asyncio
from typing import List, Dict, Any
from .clickhouse import ClickHouseSchema
from .postgres import PostgresSchema
from .questdb import QuestDBSchema
from .materialize import MaterializeSchema
from ..metrics import metrics

logger = logging.getLogger(__name__)

class SchemaInitializer:
    """Manages database schema initialization across all databases"""
    
    @staticmethod
    async def initialize_all():
        """Initialize schemas for all databases"""
        try:
            # Initialize PostgreSQL (core data)
            logger.info("Initializing PostgreSQL schemas...")
            await PostgresSchema.initialize_schema()
            metrics.api_component_health.labels(component="postgres").set(1)
            
            # Initialize ClickHouse (events, metrics, logs)
            logger.info("Initializing ClickHouse schemas...")
            await ClickHouseSchema.initialize_schema()
            metrics.api_component_health.labels(component="clickhouse").set(1)
            
            # Initialize QuestDB (time-series metrics)
            logger.info("Initializing QuestDB schemas...")
            await QuestDBSchema.initialize_schema()
            metrics.api_component_health.labels(component="questdb").set(1)
            
            # Initialize Materialize (real-time analytics)
            logger.info("Initializing Materialize schemas...")
            await MaterializeSchema.initialize_schema()
            metrics.api_component_health.labels(component="materialize").set(1)
            
            logger.info("All database schemas initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing schemas: {str(e)}")
            metrics.api_component_health.labels(component="database").set(0)
            raise
    
    @staticmethod
    async def verify_all():
        """Verify schemas across all databases"""
        try:
            # Verify PostgreSQL
            logger.info("Verifying PostgreSQL schemas...")
            await PostgresSchema.verify_schema()
            
            # Verify ClickHouse
            logger.info("Verifying ClickHouse schemas...")
            await ClickHouseSchema.verify_schema()
            
            # Verify QuestDB
            logger.info("Verifying QuestDB schemas...")
            await QuestDBSchema.verify_schema()
            
            # Verify Materialize
            logger.info("Verifying Materialize schemas...")
            await MaterializeSchema.verify_schema()
            
            logger.info("All database schemas verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Schema verification failed: {str(e)}")
            return False
    
    @staticmethod
    async def health_check() -> Dict[str, bool]:
        """Check health of all databases"""
        health = {
            "postgres": False,
            "clickhouse": False,
            "questdb": False,
            "materialize": False
        }
        
        try:
            # Check PostgreSQL
            await PostgresSchema.verify_schema()
            health["postgres"] = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {str(e)}")
        
        try:
            # Check ClickHouse
            await ClickHouseSchema.verify_schema()
            health["clickhouse"] = True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {str(e)}")
        
        try:
            # Check QuestDB
            await QuestDBSchema.verify_schema()
            health["questdb"] = True
        except Exception as e:
            logger.error(f"QuestDB health check failed: {str(e)}")
        
        try:
            # Check Materialize
            await MaterializeSchema.verify_schema()
            health["materialize"] = True
        except Exception as e:
            logger.error(f"Materialize health check failed: {str(e)}")
        
        # Update metrics
        for db, status in health.items():
            metrics.api_component_health.labels(
                component=db
            ).set(1 if status else 0)
        
        return health

# Create global schema initializer instance
schema_initializer = SchemaInitializer() 