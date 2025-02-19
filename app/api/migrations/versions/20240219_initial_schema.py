"""Initial schema setup

Revision ID: clean_schema_001
Revises: None
Create Date: 2024-02-19 04:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision: str = 'clean_schema_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create extension for UUID support
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create organizations table
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            org_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            status VARCHAR(20) CHECK (status IN ('active', 'suspended', 'deactivated')) DEFAULT 'active',
            subscription_tier VARCHAR(20) CHECK (subscription_tier IN ('free', 'starter', 'professional', 'enterprise')) DEFAULT 'free',
            settings JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            is_active BOOLEAN DEFAULT true,
            is_admin BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create organization_users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS organization_users (
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
            role VARCHAR(20) CHECK (role IN ('owner', 'admin', 'member', 'viewer')) DEFAULT 'member',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (org_id, user_id)
        )
    """)
    
    # Create data_sources table
    op.execute("""
        CREATE TABLE IF NOT EXISTS data_sources (
            source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(20) CHECK (type IN ('web', 'mobile', 'server', 'iot', 'custom')),
            config JSONB DEFAULT '{}',
            enabled BOOLEAN DEFAULT true,
            health VARCHAR(20) DEFAULT 'unknown',
            last_sync_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create pipelines table
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipelines (
            pipeline_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(20) CHECK (status IN ('active', 'paused', 'failed', 'completed')) DEFAULT 'active',
            config JSONB DEFAULT '{}',
            schedule JSONB,
            health VARCHAR(20) DEFAULT 'unknown',
            last_run_at TIMESTAMP WITH TIME ZONE,
            next_run_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create pipeline_steps table
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_steps (
            step_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            pipeline_id UUID REFERENCES pipelines(pipeline_id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            config JSONB DEFAULT '{}',
            order_index INTEGER NOT NULL,
            enabled BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create pipeline_runs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            pipeline_id UUID REFERENCES pipelines(pipeline_id) ON DELETE CASCADE,
            status VARCHAR(20) CHECK (status IN ('running', 'completed', 'failed', 'cancelled')) DEFAULT 'running',
            start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            metrics JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Create transformation_rules table
    op.execute("""
        CREATE TABLE IF NOT EXISTS transformation_rules (
            rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            type VARCHAR(50) NOT NULL,
            config JSONB DEFAULT '{}',
            enabled BOOLEAN DEFAULT true,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create data_syncs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS data_syncs (
            sync_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            source_id UUID REFERENCES data_sources(source_id) ON DELETE CASCADE,
            pipeline_id UUID REFERENCES pipelines(pipeline_id) ON DELETE SET NULL,
            status VARCHAR(20) CHECK (status IN ('pending', 'running', 'completed', 'failed')) DEFAULT 'pending',
            records_processed INTEGER DEFAULT 0,
            start_time TIMESTAMP WITH TIME ZONE,
            end_time TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            metrics JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);
        CREATE INDEX IF NOT EXISTS idx_organizations_subscription_tier ON organizations(subscription_tier);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_organization_users_user_id ON organization_users(user_id);
        CREATE INDEX IF NOT EXISTS idx_data_sources_org_id ON data_sources(org_id);
        CREATE INDEX IF NOT EXISTS idx_data_sources_health ON data_sources(health);
        CREATE INDEX IF NOT EXISTS idx_pipelines_org_id ON pipelines(org_id);
        CREATE INDEX IF NOT EXISTS idx_pipelines_health ON pipelines(health);
        CREATE INDEX IF NOT EXISTS idx_pipeline_steps_pipeline_id ON pipeline_steps(pipeline_id);
        CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON pipeline_runs(pipeline_id);
        CREATE INDEX IF NOT EXISTS idx_transformation_rules_org_id ON transformation_rules(org_id);
        CREATE INDEX IF NOT EXISTS idx_data_syncs_org_id ON data_syncs(org_id);
        CREATE INDEX IF NOT EXISTS idx_data_syncs_source_id ON data_syncs(source_id);
        CREATE INDEX IF NOT EXISTS idx_data_syncs_pipeline_id ON data_syncs(pipeline_id);
        CREATE INDEX IF NOT EXISTS idx_data_syncs_status ON data_syncs(status);
    """)
    
    # Create admin user
    op.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name, is_active, is_admin)
        VALUES (
            'admin@thedata.io',
            -- Default password is 'admin123' (should be changed in production)
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewFpxzKHWWYSLGLS',
            'Admin',
            'User',
            true,
            true
        )
        ON CONFLICT (email) DO NOTHING;
    """)

def downgrade() -> None:
    # Drop all tables in reverse order
    op.execute("""
        DROP TABLE IF EXISTS data_syncs;
        DROP TABLE IF EXISTS transformation_rules;
        DROP TABLE IF EXISTS pipeline_runs;
        DROP TABLE IF EXISTS pipeline_steps;
        DROP TABLE IF EXISTS pipelines;
        DROP TABLE IF EXISTS data_sources;
        DROP TABLE IF EXISTS organization_users;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS organizations;
    """)
    
    # Drop UUID extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"') 