#!/bin/bash

# Exit on any error
set -e

echo "🚀 Setting up and Starting TheData.io Platform..."
echo "=============================================="

# Function to print section header
print_header() {
    echo -e "\n📌 $1"
    echo "$(printf '=%.0s' {1..${#1}})"
}

# Function to handle errors
handle_error() {
    echo "❌ Error occurred in section: $1"
    echo "Error message: $2"
    echo "Please fix the issues and try again."
    exit 1
}

# 1. Environment Validation
print_header "Validating Development Environment"
./scripts/validate_dev_env.sh || handle_error "Environment Validation" "Failed to validate development environment"

# 2. Clean up existing environment
print_header "Cleaning Up Existing Environment"
./scripts/stop_dev.sh || true  # Don't fail if nothing to clean up

# 3. Pull latest images
print_header "Pulling Latest Docker Images"
docker-compose -f docker-compose.dev.yml pull || handle_error "Docker Pull" "Failed to pull latest images"

# 4. Start core infrastructure
print_header "Starting Core Infrastructure"
docker-compose -f docker-compose.dev.yml up -d postgres redis nats || handle_error "Core Infrastructure" "Failed to start core services"

# Wait for core services
sleep 10

# 5. Run database validations
# print_header "Validating Databases"
# ./scripts/validate_databases.sh || handle_error "Database Validation" "Failed to validate databases"

# 6. Run message queue validations
# print_header "Validating Message Queue"
# ./scripts/validate_message_queue.sh || handle_error "Message Queue Validation" "Failed to validate message queue"

# 7. Start remaining services
print_header "Starting Remaining Services"
docker-compose -f docker-compose.dev.yml up -d || handle_error "Service Startup" "Failed to start all services"

# 8. Run health checks
print_header "Running Health Checks"
./scripts/health_check.sh || handle_error "Health Check" "Failed health checks"

# 9. Start development servers
print_header "Starting Development Servers"

# Start API in development mode
echo "Starting API server..."
docker-compose -f docker-compose.dev.yml logs -f api &

# Start frontend development server
echo "Starting frontend server..."
(cd app/frontend && npm start) &

# Start Dagster development server
echo "Starting Dagster server..."
docker-compose -f docker-compose.dev.yml logs -f dagster &

# Print success message and instructions
print_header "Setup Complete! 🎉"
echo "
Development Environment is Ready!

📍 Access Points:
----------------
API:              http://localhost:8000
API Docs:         http://localhost:8000/docs
Frontend:         http://localhost:3000
Dagster:          http://localhost:3002
Grafana:          http://localhost:3001
Prometheus:       http://localhost:9090
QuestDB Console:  http://localhost:9000
Traefik:          http://localhost:8080

📝 Useful Commands:
----------------
• View API logs:        docker-compose logs -f api
• View frontend logs:   cd app/frontend && npm run logs
• View Dagster logs:    docker-compose logs -f dagster
• Stop environment:     ./scripts/stop_dev.sh
• Run tests:           ./scripts/run_tests.sh

🔍 Monitoring:
------------
• Check service health: ./scripts/health_check.sh
• Monitor databases:    ./scripts/validate_databases.sh
• Monitor queues:       ./scripts/validate_message_queue.sh

For more information, check the documentation in /docs
"

# Start monitoring logs
echo "📊 Monitoring for errors (press Ctrl+C to stop)..."
docker-compose -f docker-compose.dev.yml logs -f | grep -i "error" 