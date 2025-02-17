#!/bin/bash

# Don't exit on error as we want to try all cleanup steps
set +e

echo "🛑 Stopping TheData.io Platform Development Environment..."
echo "==================================================="

# Force kill all related processes first
echo "🧹 Force killing all related processes..."
pkill -9 -f "react-scripts start" >/dev/null 2>&1 || true
pkill -9 -f "docker-compose" >/dev/null 2>&1 || true
pkill -9 -f "uvicorn" >/dev/null 2>&1 || true
pkill -9 -f "dagster" >/dev/null 2>&1 || true

# Force remove all project containers
echo "🧹 Force removing all project containers..."
docker ps -a --filter name=thedata -q | xargs -r docker rm -f >/dev/null 2>&1 || true

# Force cleanup with no timeout
echo "🧹 Force cleaning up Docker resources..."
docker-compose -f docker-compose.dev.yml down --remove-orphans -v -t 0 >/dev/null 2>&1 || true

# Remove any lingering Docker networks
echo "🧹 Cleaning up Docker networks..."
docker network ls --filter name=thedata -q | xargs -r docker network rm >/dev/null 2>&1 || true

# Clean up temporary files
echo "🧹 Cleaning up temporary files..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
find . -type f -name "*.log" -delete 2>/dev/null || true
find . -type f -name "*.pid" -delete 2>/dev/null || true

# Verify cleanup
echo "🔍 Verifying cleanup..."
remaining_containers=$(docker ps -a --filter name=thedata -q | wc -l | tr -d ' ')
if [ "$remaining_containers" -gt 0 ]; then
    echo "⚠️  Warning: $remaining_containers containers still exist, forcing removal..."
    docker ps -a --filter name=thedata -q | xargs -r docker rm -f
fi

echo -e "\n✨ Development environment forcefully stopped!"
echo "Run './scripts/start_dev.sh' to start the environment again" 