#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting TheData.io Platform Development Environment..."
echo "====================================================="

# Function to wait for service health
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=$3
    local wait_seconds=$4
    local attempt=1

    echo -n "Waiting for $service to be ready... "
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port >/dev/null 2>&1; then
            echo "✅"
            return 0
        fi
        echo -n "."
        sleep $wait_seconds
        attempt=$((attempt + 1))
    done
    echo "❌"
    echo "Error: $service failed to start after $((max_attempts * wait_seconds)) seconds"
    return 1
}

# Function to check service logs for errors
check_service_logs() {
    local service=$1
    local lines=$2
    echo "Checking $service logs for errors..."
    docker-compose logs --tail=$lines $service | grep -i "error" || echo "No errors found in $service logs"
}

# Validate environment first
echo "🔍 Validating environment..."
./scripts/validate_dev_env.sh || {
    echo "❌ Environment validation failed. Please fix the issues and try again."
    exit 1
}

# Clean up any existing containers
echo "🧹 Cleaning up existing development environment..."
docker-compose -f docker-compose.dev.yml down --remove-orphans

# Pull latest images
echo "📥 Pulling latest Docker images..."
docker-compose -f docker-compose.dev.yml pull

# Start core services first
echo "🔄 Starting core services..."
docker-compose -f docker-compose.dev.yml up -d postgres redis nats

# Wait for core services
wait_for_service "PostgreSQL" 5432 30 2
wait_for_service "Redis" 6379 30 2
wait_for_service "NATS" 4222 30 2

# Run database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.dev.yml run --rm api python -m alembic upgrade head

# Start remaining services
echo "🚀 Starting remaining services..."
docker-compose -f docker-compose.dev.yml up -d

# Wait for all services
wait_for_service "API" 8000 60 2
wait_for_service "Dagster" 3002 60 2
wait_for_service "QuestDB" 8812 60 2
wait_for_service "ClickHouse" 8123 60 2
wait_for_service "Materialize" 6875 60 2
wait_for_service "Grafana" 3001 60 2
wait_for_service "Prometheus" 9090 60 2

# Verify service health
echo "🏥 Verifying service health..."
./scripts/health_check.sh

# Start development processes
echo "💻 Starting development processes..."

# Start API in development mode
echo "🔄 Starting API in development mode..."
docker-compose -f docker-compose.dev.yml logs -f api &

# Start frontend development server
echo "🔄 Starting frontend development server..."
(cd app/frontend && npm start) &

# Start Dagster development server
echo "🔄 Starting Dagster development server..."
docker-compose -f docker-compose.dev.yml logs -f dagster &

# Print access URLs
echo -e "\n🌐 Development Environment URLs:"
echo "----------------------------"
echo "API:              http://localhost:8000"
echo "API Docs:         http://localhost:8000/docs"
echo "Frontend:         http://localhost:3000"
echo "Dagster:          http://localhost:3002"
echo "Grafana:          http://localhost:3001"
echo "Prometheus:       http://localhost:9090"
echo "QuestDB Console:  http://localhost:9000"
echo "Traefik:          http://localhost:8080"

# Print development instructions
echo -e "\n📝 Development Instructions:"
echo "------------------------"
echo "1. API logs:        docker-compose logs -f api"
echo "2. Frontend logs:   cd app/frontend && npm run logs"
echo "3. Dagster logs:    docker-compose logs -f dagster"
echo "4. Run tests:       ./scripts/run_tests.sh"
echo "5. Stop env:        ./scripts/stop_dev.sh"

# Monitor for errors
echo -e "\n👀 Monitoring for errors (press Ctrl+C to stop)..."
docker-compose -f docker-compose.dev.yml logs -f | grep -i "error" 