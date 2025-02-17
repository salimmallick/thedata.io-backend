from typing import List, Dict, Any
import logging
from ..config import settings

logger = logging.getLogger(__name__)

# Schema definitions
ORGANIZATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'active',
    quota_limit INTEGER,
    api_keys TEXT[]
);
"""

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    settings JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'active'
);
"""

API_KEYS_TABLE = """
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active'
);
"""

RATE_LIMITS_TABLE = """
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    resource VARCHAR(255) NOT NULL,
    limit_per_minute INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

TRANSFORMATION_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS transformation_rules (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    UNIQUE(organization_id, name)
);
"""

# Indexes
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_org_tier ON organizations(tier);",
    "CREATE INDEX IF NOT EXISTS idx_user_org ON users(organization_id);",
    "CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(organization_id);",
    "CREATE INDEX IF NOT EXISTS idx_rate_limits_org ON rate_limits(organization_id);",
    "CREATE INDEX IF NOT EXISTS idx_transform_rules_org ON transformation_rules(organization_id);"
]

# Functions
UPDATE_TIMESTAMP_FUNCTION = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
"""

# Triggers
TRIGGERS = [
    """
    CREATE TRIGGER update_organizations_timestamp
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    """
    CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """,
    """
    CREATE TRIGGER update_transformation_rules_timestamp
    BEFORE UPDATE ON transformation_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
]

class PostgresSchema:
    """Manages PostgreSQL schema creation and updates"""
    
    @staticmethod
    async def initialize_schema():
        """Create all required tables, indexes, and triggers"""
        from ..database import postgres
        
        # Create tables
        tables = [
            ORGANIZATIONS_TABLE,
            USERS_TABLE,
            API_KEYS_TABLE,
            RATE_LIMITS_TABLE,
            TRANSFORMATION_RULES_TABLE
        ]
        
        async with postgres.transaction() as conn:
            # Create tables
            for table in tables:
                try:
                    await conn.execute(table)
                    logger.info(f"Successfully created table: {table.split('CREATE')[1].split('(')[0]}")
                except Exception as e:
                    logger.error(f"Error creating table: {str(e)}")
                    raise
            
            # Create function for timestamp updates
            try:
                await conn.execute(UPDATE_TIMESTAMP_FUNCTION)
                logger.info("Created timestamp update function")
            except Exception as e:
                logger.error(f"Error creating function: {str(e)}")
                raise
            
            # Create indexes
            for index in INDEXES:
                try:
                    await conn.execute(index)
                    logger.info(f"Created index: {index}")
                except Exception as e:
                    logger.error(f"Error creating index: {str(e)}")
                    raise
            
            # Create triggers
            for trigger in TRIGGERS:
                try:
                    await conn.execute(trigger)
                    logger.info(f"Created trigger: {trigger}")
                except Exception as e:
                    logger.error(f"Error creating trigger: {str(e)}")
                    raise
    
    @staticmethod
    async def verify_schema():
        """Verify all required database objects exist"""
        from ..database import postgres
        
        required_tables = [
            "organizations",
            "users",
            "api_keys",
            "rate_limits",
            "transformation_rules"
        ]
        
        async with postgres.transaction() as conn:
            for table in required_tables:
                result = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if not result:
                    raise Exception(f"Missing required table: {table}")
        
        logger.info("Schema verification completed successfully") 