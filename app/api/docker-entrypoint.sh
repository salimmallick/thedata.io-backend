#!/bin/bash
set -e

# Run migrations
cd /app/app/api

# Check if tables exist
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')" | grep -q 't'
ALEMBIC_EXISTS=$?

if [ $ALEMBIC_EXISTS -eq 0 ]; then
    echo "Database already initialized. Checking for new migrations..."
    alembic upgrade head || {
        echo "Error running migrations. Continuing anyway..."
    }
else
    echo "Initializing database..."
    alembic upgrade head
fi

# Start the application
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload 