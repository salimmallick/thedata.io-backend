#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_success() { echo -e "${GREEN}✓ $1${NC}"; }
log_error() { echo -e "${RED}✗ $1${NC}"; return 1; }
log_warning() { echo -e "${YELLOW}! $1${NC}"; }
log_info() { echo "ℹ $1"; }

# Function to wait for service health
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=$3
    local attempt=1
    
    echo "Waiting for $service to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            log_success "$service is ready"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service is not ready yet..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_error "$service failed to become ready"
    return 1
}

# Main setup function
main() {
    # Run validation script first
    log_info "Running system validation..."
    if ! bash scripts/validate_setup.sh; then
        log_error "System validation failed. Please fix the issues and try again."
        exit 1
    fi
    
    # Create necessary directories
    log_info "Creating necessary directories..."
    mkdir -p config/{clickhouse,grafana,prometheus}
    mkdir -p logs
    mkdir -p app/tests
    log_success "Directories created"
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
    pip install pytest pytest-asyncio httpx faker
    log_success "Python dependencies installed"
    
    # Install Node.js dependencies
    log_info "Installing Node.js dependencies..."
    cd app/frontend
    npm install
    cd ../..
    log_success "Node.js dependencies installed"
    
    # Start development services
    log_info "Starting development services..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    wait_for_service "PostgreSQL" "http://localhost:5432" 12 || exit 1
    wait_for_service "ClickHouse" "http://localhost:8123" 12 || exit 1
    wait_for_service "QuestDB" "http://localhost:9000" 12 || exit 1
    wait_for_service "Redis" "http://localhost:6379" 12 || exit 1
    wait_for_service "NATS" "http://localhost:8222" 12 || exit 1
    
    # Run database migrations
    log_info "Running database migrations..."
    python -m app.api.migrations.run_migrations
    log_success "Database migrations completed"
    
    # Generate test data
    log_info "Generating test data..."
    python scripts/generate_test_data.py
    log_success "Test data generated"
    
    # Run tests
    log_info "Running tests..."
    pytest app/tests/
    log_success "Tests completed"
    
    # Start frontend development server
    log_info "Starting frontend development server..."
    cd app/frontend
    npm start &
    cd ../..
    
    log_success "Development environment setup complete!"
    echo
    echo "You can now access:"
    echo "- API: http://localhost:8000"
    echo "- Frontend: http://localhost:3000"
    echo "- Grafana: http://localhost:3001"
    echo "- Prometheus: http://localhost:9090"
    echo "- NATS monitoring: http://localhost:8222"
    echo "- ClickHouse UI: http://localhost:8123/play"
    echo "- QuestDB UI: http://localhost:9000"
    
    # Print default credentials
    echo
    echo "Default credentials:"
    echo "Admin Portal:"
    echo "- Email: admin@thedata.io"
    echo "- Password: changeme123"
    echo
    log_warning "Please change the default password after first login!"
}

# Run main function
main 