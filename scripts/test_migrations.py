"""
Script to test database migrations.
"""
import asyncio
import logging
from pathlib import Path
import sys
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.api.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_migrations():
    """Test the database migrations."""
    try:
        # Create a test database
        test_db_url = settings.POSTGRES_URL + "_test"
        engine = create_engine(test_db_url)
        Session = sessionmaker(bind=engine)

        logger.info("Starting migration tests")

        # Get the path to alembic.ini
        alembic_ini_path = Path(__file__).parent.parent / 'alembic.ini'
        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")

        # Create Alembic configuration
        alembic_cfg = Config(str(alembic_ini_path))
        migrations_path = Path(__file__).parent.parent / 'app' / 'api' / 'migrations'
        alembic_cfg.set_main_option('script_location', str(migrations_path))
        alembic_cfg.set_main_option('sqlalchemy.url', test_db_url)

        # Test upgrade
        logger.info("Testing upgrade")
        command.upgrade(alembic_cfg, "head")
        
        # Verify tables exist
        session = Session()
        for table in [
            'users', 'organizations', 'data_sources', 'pipelines',
            'data_source_metrics', 'pipeline_metrics',
            'data_source_logs', 'pipeline_logs'
        ]:
            result = session.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = result.scalar()
            assert exists, f"Table {table} was not created"
            logger.info(f"Verified table {table} exists")

        # Test downgrade
        logger.info("Testing downgrade")
        command.downgrade(alembic_cfg, "base")
        
        # Verify tables are dropped
        for table in [
            'users', 'organizations', 'data_sources', 'pipelines',
            'data_source_metrics', 'pipeline_metrics',
            'data_source_logs', 'pipeline_logs'
        ]:
            result = session.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = result.scalar()
            assert not exists, f"Table {table} was not dropped"
            logger.info(f"Verified table {table} was dropped")

        # Test upgrade again
        logger.info("Testing upgrade again")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Migration tests completed successfully")
        
        # Clean up
        session.close()
        engine.dispose()

    except Exception as e:
        logger.error(f"Migration tests failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_migrations()) 