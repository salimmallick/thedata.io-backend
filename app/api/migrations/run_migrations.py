import asyncio
import asyncpg
import os
import logging
from pathlib import Path
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_postgres_connection():
    """Get a PostgreSQL connection"""
    return await asyncpg.connect(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "thedata"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432"))
    )

async def execute_sql_safely(conn, sql: str, migration_name: str) -> bool:
    """Execute SQL statements safely by splitting them and handling errors"""
    # Split SQL into individual statements
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    success = True
    
    for statement in statements:
        try:
            # Execute each statement in its own transaction
            async with conn.transaction():
                await conn.execute(statement)
        except asyncpg.DuplicateObjectError:
            # Log warning but continue if object already exists
            logger.warning(f"Object already exists in {migration_name}: {statement[:100]}...")
        except Exception as e:
            # Log error but continue with next statement
            logger.error(f"Error executing statement in {migration_name}: {statement[:100]}...")
            logger.error(f"Error details: {str(e)}")
            success = False
    
    return success

async def run_migrations():
    """Run all SQL migrations in order"""
    conn = None
    try:
        conn = await get_postgres_connection()
        logger.info("Connected to PostgreSQL")
        
        # Create migrations table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Get list of applied migrations
        applied_migrations = set(
            filename for (filename,) in await conn.fetch(
                "SELECT filename FROM migrations"
            )
        )
        
        # Get all migration files
        migrations_dir = Path(__file__).parent
        migration_files = sorted([
            f for f in migrations_dir.glob("*.sql")
            if f.name not in applied_migrations
        ])
        
        # Apply each migration in order
        for migration_file in migration_files:
            logger.info(f"Applying migration: {migration_file.name}")
            
            # Read and execute migration
            sql = migration_file.read_text()
            success = await execute_sql_safely(conn, sql, migration_file.name)
            
            if success:
                # Record migration as applied
                await conn.execute(
                    "INSERT INTO migrations (filename) VALUES ($1)",
                    migration_file.name
                )
                logger.info(f"Successfully applied migration: {migration_file.name}")
            else:
                logger.warning(f"Migration {migration_file.name} had some errors but continued")
        
        logger.info("All migrations completed")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        if conn:
            await conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(run_migrations()) 