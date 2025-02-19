"""
Script to create test database.
"""
import asyncio
import logging
from sqlalchemy import create_engine, text
from app.api.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_database():
    """Create test database if it doesn't exist."""
    try:
        # Connect to default database to create test database
        engine = create_engine(settings.POSTGRES_URL)
        
        # Get database name from URL
        db_name = settings.POSTGRES_URL.split('/')[-1] + '_test'
        
        with engine.connect() as conn:
            # Disconnect all users
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid()
            """))
            
            # Drop database if exists
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            
            # Create database
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            
            logger.info(f"Created test database: {db_name}")
        
        engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to create test database: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(create_test_database()) 