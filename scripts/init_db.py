import asyncio
import sys
import os
import asyncpg
from app.api.core.config import Settings
from app.api.core.auth.security import get_password_hash

settings = Settings()

async def init_db():
    """Initialize database with required tables and default admin user."""
    # Create connection
    conn = await asyncpg.connect(settings.POSTGRES_URL)
    
    try:
        # Drop existing tables
        await conn.execute('''
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS organizations CASCADE;
        ''')
        
        # Create tables
        await conn.execute('''
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(50) DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT true,
                is_superuser BOOLEAN DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                api_key VARCHAR(255) UNIQUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Create default admin user
        hashed_password = get_password_hash('admin123')
        await conn.execute('''
            INSERT INTO users (email, hashed_password, full_name, role, is_superuser)
            VALUES ($1, $2, $3, $4, $5)
        ''', 'admin@thedata.io', hashed_password, 'Admin User', 'admin', True)
        print("Created default admin user")
        
        print("Database initialization complete!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_db()) 