#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Dagster services..."

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL..."
    until nc -z $DAGSTER_POSTGRES_HOST $DAGSTER_POSTGRES_PORT; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 1
    done
    echo "PostgreSQL is up"
}

# Function to handle process cleanup
cleanup() {
    echo "Shutting down Dagster services..."
    pkill -f "dagster-daemon"
    pkill -f "dagster-webserver"
    wait
    echo "Shutdown complete"
}

# Set up signal handling
trap cleanup SIGTERM SIGINT SIGQUIT

# Wait for dependencies
wait_for_postgres

# Create necessary directories
mkdir -p "${DAGSTER_HOME}/logs"
mkdir -p "${DAGSTER_HOME}/storage"
mkdir -p "${DAGSTER_HOME}/compute_logs"

# Verify Dagster installation
echo "Verifying Dagster installation..."
python -c "import dagster; print('Dagster version:', dagster.__version__)"

# Start Dagster daemon
echo "Starting Dagster daemon..."
cd /opt/dagster
dagster-daemon run &

# Start Dagster webserver
echo "Starting Dagster webserver..."
dagster-webserver \
    -h 0.0.0.0 \
    -p 3000 \
    -w "${DAGSTER_HOME}/workspace.yaml" &

echo "✨ All Dagster services started"

# Monitor service health
while true; do
    sleep 30
    
    # Check Dagster daemon
    if ! pgrep -f "dagster-daemon" > /dev/null; then
        echo "❌ Dagster daemon is not running!"
        exit 1
    fi
    
    # Check Dagster webserver
    if ! pgrep -f "dagster-webserver" > /dev/null; then
        echo "❌ Dagster webserver is not running!"
        exit 1
    fi
    
    # Log status
    echo "✅ All services running ($(date))"
done 