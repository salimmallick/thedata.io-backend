# theData.io Platform Status Document

## System Overview
theData.io is a data synchronization and analytics platform built with FastAPI and React. The system consists of several components working together to provide a robust data management solution.

## Database Structure

### Key Database Files
1. **Migration Files** (`app/api/migrations/versions/`):
   - `20240217_initial_schema.py`: Initial database schema
   - `20240218_fix_schema.py`: Schema fixes and missing tables
   - `20240218_add_user_roles.py`: User roles implementation
   - `20240218_update_organizations_001.py`: Updated organizations table

2. **Models** (`app/api/models/`):
   - `base.py`: Base SQLAlchemy model
   - `user.py`: User and authentication models
   - `organization.py`: Organization and related models
   - Other model files for different entities

3. **Database Configuration**:
   - `app/api/core/database/pool.py`: Database connection pool
   - `app/api/core/storage/config.py`: Database configuration
   - `alembic.ini`: Alembic migration configuration
   - `app/api/docker-entrypoint.sh`: Container initialization and migration script

## API Services

### Authentication (`/api/v1/auth/`)
- Login: POST `/login`
- Register: POST `/register`
- Current User: GET `/me`
- Logout: POST `/logout`

### Users (`/api/v1/users/`)
- List Users: GET `/`
- Get User: GET `/{user_id}`
- Update User: PUT `/{user_id}`
- Delete User: DELETE `/{user_id}`

### Organizations (`/api/v1/organizations/`)
- List Organizations: GET `/`
- Create Organization: POST `/`
- Get Organization: GET `/{org_id}`
- Update Organization: PUT `/{org_id}`
- Delete Organization: DELETE `/{org_id}`
- List Members: GET `/{org_id}/members`
- Add Member: POST `/{org_id}/members`

### Data Sources (`/api/v1/data-sources/`)
- List Sources: GET `/`
- Create Source: POST `/`
- Update Source: PUT `/{source_id}`
- Delete Source: DELETE `/{source_id}`
- Get Metrics: GET `/{source_id}/metrics`

### Pipelines (`/api/v1/pipelines/`)
- List Pipelines: GET `/`
- Create Pipeline: POST `/`
- Update Pipeline: PUT `/{pipeline_id}`
- Delete Pipeline: DELETE `/{pipeline_id}`
- Start Pipeline: POST `/{pipeline_id}/start`
- Stop Pipeline: POST `/{pipeline_id}/stop`
- Get Logs: GET `/{pipeline_id}/logs`

### Analytics (`/api/v1/analytics/`)
- Get Metrics: GET `/metrics`
- Get Events: GET `/events`
- Real-time Metrics: GET `/realtime/{view_name}`
- Historical Data: GET `/historical/{table_name}`

### Admin (`/api/v1/admin/`)
- System Status: GET `/system/status`
- System Config: GET/PUT `/system/config`
- Metrics Config: GET/PUT `/metrics/config`
- Alerts Config: GET/PUT `/alerts/config`
- Active Alerts: GET `/alerts/active`

## Database Migration Process

### Automated Migration System
The platform uses an automated Docker-based migration system:

1. **Container Startup**:
   - Docker entrypoint script automatically checks database state
   - Runs pending migrations using Alembic
   - Ensures database schema is up-to-date

2. **Development Workflow**:
   - Migrations automatically run when containers start
   - No manual migration steps required
   - Changes tracked in version control

3. **Creating New Migrations**:
   ```bash
   # Connect to API container
   docker exec -it thedataio-backend-api-1 bash
   
   # Create new migration
   alembic revision -m "description"
   ```

4. **Manual Controls (if needed)**:
   ```bash
   # Apply migrations
   docker exec thedataio-backend-api-1 alembic upgrade head
   
   # Rollback
   docker exec thedataio-backend-api-1 alembic downgrade -1
   ```

### Best Practices
1. Test migrations in development environment
2. Include both upgrade and downgrade paths
3. Use meaningful migration names
4. Document schema changes
5. Use transactions for safety

## Frontend Integration
The frontend (`app/frontend/`) communicates with these endpoints through:
- `src/services/api.ts`: Main API service
- `src/services/apiClient.ts`: Axios client configuration
- `src/services/adminService.ts`: Admin-specific services
- `src/services/dataManagementService.ts`: Data management services

## Current Status
- All core database tables implemented
- Authentication system working
- Organization management updated
- User roles implemented
- API endpoints functional
- Frontend integration ready

## Next Steps
1. Implement remaining analytics features
2. Add more comprehensive testing
3. Enhance error handling
4. Improve monitoring and logging
5. Add performance optimizations 