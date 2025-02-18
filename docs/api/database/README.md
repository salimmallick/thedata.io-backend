# Database Migration System

## Overview
This directory contains the complete database migration system for theData.io platform. The system uses Alembic for managing database schema changes and provides automated migration handling through Docker.

## Directory Structure
```
app/api/
├── docker-entrypoint.sh  # Docker container initialization and migration script
├── migrations/
│   ├── env.py           # Alembic environment configuration
│   └── versions/        # Migration version files
│       ├── 20240217_initial_schema.py     # Initial database schema
│       ├── 20240218_fix_schema.py         # Schema fixes and missing tables
│       ├── 20240218_add_user_roles.py     # User roles implementation
│       └── 20240218_update_organizations_001.py  # Updated organizations table
└── models/
    ├── base.py          # Base SQLAlchemy model
    ├── user.py          # User and authentication models
    ├── organization.py  # Organization and related models
    └── ...             # Other model files
```

## Components

### 1. Base Model
Located at `app/api/models/base.py`, this provides the base SQLAlchemy model that all other models inherit from. It includes:
- `created_at` timestamp
- `updated_at` timestamp
- Dictionary conversion method

### 2. Schema Evolution
The database schema has evolved through several migrations:

#### a. Initial Schema (20240217_initial_schema.py)
- Users table
- Organizations table
- Data Sources table
- Pipelines table
- Metrics tables
- Logs tables
- All necessary indexes

#### b. Schema Fixes (20240218_fix_schema.py)
- Fixed users table structure
- Added permissions table
- Added role_permissions table
- Added organization_members table
- Added data_syncs table

#### c. User Roles (20240218_add_user_roles.py)
- Added user_roles table
- Implemented role-based access control
- Added default admin role

#### d. Organization Updates (20240218_update_organizations_001.py)
- Updated organizations table structure
- Added status and subscription_tier fields
- Added settings and metadata JSON fields
- Implemented proper constraints

## Automatic Migration Process

### Docker-based Migration
The system handles migrations automatically through Docker:

1. **Container Startup**:
   - `docker-entrypoint.sh` checks if migrations are needed
   - Automatically runs `alembic upgrade head` for pending migrations
   - Handles database initialization

2. **When Migrations Run**:
   - On container first start
   - After pulling new code with schema changes
   - After container rebuild
   - When manually triggered through Docker commands

### Creating New Migrations
To create a new migration:
```bash
# Connect to the running API container
docker exec -it thedataio-backend-api-1 bash

# Create a new migration
alembic revision -m "description_of_changes"

# The new migration file will be created in app/api/migrations/versions/
```

### Manual Migration Commands (if needed)
```bash
# Apply all pending migrations
docker exec thedataio-backend-api-1 alembic upgrade head

# Rollback last migration
docker exec thedataio-backend-api-1 alembic downgrade -1

# View migration history
docker exec thedataio-backend-api-1 alembic history
```

## Prerequisites
1. Docker and Docker Compose installed
2. Environment variables configured in docker-compose.yml:
   - POSTGRES_DSN
   - POSTGRES_HOST
   - POSTGRES_PORT
   - POSTGRES_USER
   - POSTGRES_PASSWORD
   - POSTGRES_DB

## Best Practices
1. Always test migrations in development environment first
2. Back up your database before applying migrations to production
3. Review migration files before applying them
4. Use meaningful names for migration files
5. Include both upgrade and downgrade paths in migrations
6. Document schema changes
7. Use transactions for safety

## Troubleshooting

### Common Issues
1. **Migration failed during container startup**
   - Check the container logs: `docker logs thedataio-backend-api-1`
   - Verify database connection settings
   - Ensure database user has necessary permissions

2. **Database connection failed**
   - Verify PostgreSQL container is running
   - Check environment variables in docker-compose.yml
   - Ensure database user has necessary permissions

3. **Migration conflicts**
   - View migration history: `docker exec thedataio-backend-api-1 alembic history`
   - Consider rolling back: `docker exec thedataio-backend-api-1 alembic downgrade -1`
   - Review migration files for dependencies

4. **Enum type conflicts**
   - Use string fields with CHECK constraints instead
   - Drop existing enum types if necessary
   - Handle existing enum types in migrations

### Getting Help
1. Check the container logs for detailed error messages
2. Review Alembic documentation for migration-specific issues
3. Contact the development team for assistance

## Contributing
1. Create new migrations using `alembic revision -m "description"`
2. Always include both upgrade() and downgrade() implementations
3. Test migrations thoroughly in development environment
4. Update this documentation when adding new features
5. Follow the established naming conventions
6. Add appropriate constraints and indexes 