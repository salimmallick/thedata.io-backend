from typing import List, Dict, Any
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Schema definitions
PERFORMANCE_METRICS = """
CREATE TABLE IF NOT EXISTS performance_metrics (
    timestamp TIMESTAMP,
    metric_name SYMBOL,
    value DOUBLE,
    labels SYMBOL,
    host SYMBOL,
    service SYMBOL,
    environment SYMBOL
) timestamp(timestamp) PARTITION BY DAY;
"""

SYSTEM_METRICS = """
CREATE TABLE IF NOT EXISTS system_metrics (
    timestamp TIMESTAMP,
    host SYMBOL,
    cpu_usage DOUBLE,
    memory_used LONG,
    memory_total LONG,
    disk_used LONG,
    disk_total LONG,
    network_in LONG,
    network_out LONG
) timestamp(timestamp) PARTITION BY DAY;
"""

API_METRICS = """
CREATE TABLE IF NOT EXISTS api_metrics (
    timestamp TIMESTAMP,
    endpoint SYMBOL,
    method SYMBOL,
    status_code INT,
    duration_ms DOUBLE,
    client_ip SYMBOL,
    user_agent SYMBOL,
    organization_id SYMBOL
) timestamp(timestamp) PARTITION BY DAY;
"""

TRANSFORMATION_METRICS = """
CREATE TABLE IF NOT EXISTS transformation_metrics (
    timestamp TIMESTAMP,
    rule_name SYMBOL,
    rule_type SYMBOL,
    duration_ms DOUBLE,
    input_size LONG,
    output_size LONG,
    success BOOLEAN,
    error_type SYMBOL
) timestamp(timestamp) PARTITION BY DAY;
"""

# Retention policies (in SQL comments for documentation)
RETENTION_POLICIES = """
-- Performance metrics: 30 days
ALTER TABLE performance_metrics SET RETENTION 30d;

-- System metrics: 14 days
ALTER TABLE system_metrics SET RETENTION 14d;

-- API metrics: 90 days
ALTER TABLE api_metrics SET RETENTION 90d;

-- Transformation metrics: 30 days
ALTER TABLE transformation_metrics SET RETENTION 30d;
"""

class QuestDBSchema:
    """Manages QuestDB schema creation and updates"""
    
    @staticmethod
    async def initialize_schema():
        """Create all required tables with appropriate settings"""
        from ..database import questdb
        
        tables = [
            PERFORMANCE_METRICS,
            SYSTEM_METRICS,
            API_METRICS,
            TRANSFORMATION_METRICS
        ]
        
        for table in tables:
            try:
                await questdb.execute(table)
                logger.info(f"Successfully created table: {table.split('CREATE')[1].split('(')[0]}")
            except Exception as e:
                logger.error(f"Error creating table: {str(e)}")
                raise
        
        # Set retention policies
        retention_statements = RETENTION_POLICIES.split(';')
        for statement in retention_statements:
            if statement.strip() and not statement.strip().startswith('--'):
                try:
                    await questdb.execute(statement)
                    logger.info(f"Applied retention policy: {statement.strip()}")
                except Exception as e:
                    logger.error(f"Error setting retention policy: {str(e)}")
                    raise
    
    @staticmethod
    async def verify_schema():
        """Verify all required tables exist"""
        from ..database import questdb
        
        required_tables = [
            "performance_metrics",
            "system_metrics",
            "api_metrics",
            "transformation_metrics"
        ]
        
        for table in required_tables:
            try:
                result = await questdb.execute(f"SHOW COLUMNS FROM {table}")
                if not result:
                    raise Exception(f"Missing required table: {table}")
            except Exception as e:
                logger.error(f"Error verifying table {table}: {str(e)}")
                raise
        
        logger.info("Schema verification completed successfully") 