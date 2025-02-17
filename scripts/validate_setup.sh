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

# Function to check if a command exists
check_command() {
    local cmd=$1
    local min_version=$2
    local required=$3
    
    if ! command -v "$cmd" >/dev/null 2>&1; then
        if [ "$required" = "true" ]; then
            log_error "$cmd is not installed"
            return 1
        else
            log_warning "$cmd is not installed (optional)"
            return 0
        fi
    fi
    
    if [ -n "$min_version" ]; then
        local version
        case "$cmd" in
            docker)
                version=$(docker --version | awk '{print $3}' | tr -d ',')
                ;;
            python)
                version=$(python --version 2>&1 | awk '{print $2}')
                ;;
            node)
                version=$(node --version | tr -d 'v')
                ;;
            *)
                version=$($cmd --version 2>&1 | awk '{print $1}')
                ;;
        esac
        
        if ! printf '%s\n%s\n' "$min_version" "$version" | sort -V -C; then
            if [ "$required" = "true" ]; then
                log_error "$cmd version $version is less than required version $min_version"
                return 1
            else
                log_warning "$cmd version $version is less than recommended version $min_version"
                return 0
            fi
        fi
    fi
    
    log_success "$cmd is installed${min_version:+ (version $version >= $min_version)}"
    return 0
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -i ":$port" >/dev/null 2>&1; then
        log_error "Port $port is already in use"
        return 1
    fi
    log_success "Port $port is available"
    return 0
}

# Function to validate configuration files
validate_configs() {
    local missing_files=0
    
    # Check for required configuration files
    local required_files=(
        "docker-compose.dev.yml"
        "requirements.txt"
        "app/frontend/package.json"
        "app/api/config.py"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Missing required file: $file"
            missing_files=$((missing_files + 1))
        else
            log_success "Found required file: $file"
        fi
    done
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_warning "Creating .env file from template..."
        if [ -f .env.template ]; then
            cp .env.template .env
            log_success "Created .env file"
        else
            log_error "Missing .env.template file"
            missing_files=$((missing_files + 1))
        fi
    else
        log_success "Found .env file"
    fi
    
    return $missing_files
}

# Function to check environment variables
check_env_vars() {
    local missing_vars=0
    
    # Required environment variables
    local required_vars=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "CLICKHOUSE_USER"
        "CLICKHOUSE_PASSWORD"
        "QUESTDB_USER"
        "QUESTDB_PASSWORD"
        "GRAFANA_ADMIN_PASSWORD"
    )
    
    # Source .env file if it exists
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    fi
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Missing required environment variable: $var"
            missing_vars=$((missing_vars + 1))
        else
            log_success "Found required environment variable: $var"
        fi
    done
    
    return $missing_vars
}

# Function to check network connectivity
check_network() {
    # Check internet connectivity
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        log_error "No internet connection"
        return 1
    fi
    log_success "Internet connection is available"
    
    # Check Docker Hub connectivity
    if ! curl -s https://hub.docker.com/_/hello-world >/dev/null 2>&1; then
        log_error "Cannot connect to Docker Hub"
        return 1
    fi
    log_success "Docker Hub is accessible"
    
    return 0
}

# Function to check Docker images
check_docker_images() {
    local missing_images=0
    
    # Required Docker images
    local required_images=(
        "postgres:15-alpine"
        "clickhouse/clickhouse-server:23.3"
        "questdb/questdb:7.3.1"
        "nats:2.9-alpine"
        "redis:7.0-alpine"
        "grafana/grafana:9.5.2"
        "prom/prometheus:v2.44.0"
    )
    
    for image in "${required_images[@]}"; do
        if ! docker image inspect "$image" >/dev/null 2>&1; then
            log_warning "Docker image not found locally: $image"
            log_info "Pulling $image..."
            if ! docker pull "$image" >/dev/null 2>&1; then
                log_error "Failed to pull Docker image: $image"
                missing_images=$((missing_images + 1))
            else
                log_success "Successfully pulled Docker image: $image"
            fi
        else
            log_success "Found Docker image: $image"
        fi
    done
    
    return $missing_images
}

# Main validation function
main() {
    local errors=0
    
    echo "Starting system validation..."
    echo
    
    # Check required commands
    log_info "Checking required commands..."
    check_command "docker" "20.10.0" "true" || errors=$((errors + 1))
    check_command "docker-compose" "1.29.0" "true" || errors=$((errors + 1))
    check_command "python" "3.8.0" "false" # Python is optional on host
    check_command "node" "14.0.0" "true" || errors=$((errors + 1))
    check_command "npm" "6.0.0" "true" || errors=$((errors + 1))
    echo
    
    # Check required ports
    log_info "Checking required ports..."
    check_port 8000 || errors=$((errors + 1))  # API
    check_port 3000 || errors=$((errors + 1))  # Frontend
    check_port 5432 || errors=$((errors + 1))  # PostgreSQL
    check_port 8123 || errors=$((errors + 1))  # ClickHouse
    check_port 9000 || errors=$((errors + 1))  # QuestDB
    check_port 6379 || errors=$((errors + 1))  # Redis
    check_port 4222 || errors=$((errors + 1))  # NATS
    check_port 3001 || errors=$((errors + 1))  # Grafana
    check_port 9090 || errors=$((errors + 1))  # Prometheus
    echo
    
    # Validate configuration files
    log_info "Validating configuration files..."
    validate_configs || errors=$((errors + 1))
    echo
    
    # Check environment variables
    log_info "Checking environment variables..."
    check_env_vars || errors=$((errors + 1))
    echo
    
    # Check network connectivity
    log_info "Checking network connectivity..."
    check_network || errors=$((errors + 1))
    echo
    
    # Check Docker images
    log_info "Checking Docker images..."
    check_docker_images || errors=$((errors + 1))
    echo
    
    # Final validation result
    if [ $errors -eq 0 ]; then
        log_success "All validation checks passed!"
        return 0
    else
        log_error "Validation failed with $errors error(s)"
        return 1
    fi
}

# Run main validation function
main 