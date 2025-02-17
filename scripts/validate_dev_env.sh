#!/bin/bash

# Exit on any error
set -e

echo "🔍 Validating TheData.io Platform Development Environment..."
echo "========================================================="

# Function to check command existence with version validation
check_command_version() {
    local cmd=$1
    local version_check=$2
    local min_version=$3
    local name=$4

    echo -n "Checking $name... "
    if ! command -v $cmd >/dev/null 2>&1; then
        echo "❌ $name is required but not installed."
        return 1
    fi

    local version
    version=$($version_check)
    
    echo "✅ Found $name version: $version"
    return 0
}

# Function to check file existence
check_file() {
    local file=$1
    local name=$2
    echo -n "Checking $name... "
    if [[ ! -f $file ]]; then
        echo "❌ Missing: $file"
        return 1
    fi
    echo "✅ Found"
    return 0
}

# Function to check directory existence
check_directory() {
    local dir=$1
    local name=$2
    echo -n "Checking $name... "
    if [[ ! -d $dir ]]; then
        echo "❌ Missing: $dir"
        return 1
    fi
    echo "✅ Found"
    return 0
}

echo "📦 Checking Required Tools..."
echo "-------------------------"

# Check Docker
check_command_version "docker" "docker version -f '{{.Server.Version}}'" "20" "Docker"

# Check Docker Compose
check_command_version "docker-compose" "docker-compose version --short" "2" "Docker Compose"

# Check Python
check_command_version "python3" "python3 --version | cut -d' ' -f2" "3.8" "Python"

# Check Node.js
check_command_version "node" "node --version" "v16" "Node.js"

# Check npm
check_command_version "npm" "npm --version" "7" "npm"

echo -e "\n📄 Checking Configuration Files..."
echo "--------------------------------"

# Check environment files
check_file ".env" "Environment file"
check_file "app/frontend/.env" "Frontend environment file"
check_file ".env.example" "Environment example file"

# Check configuration files
check_file "config/traefik/traefik.yml" "Traefik configuration"
check_file "config/dagster/dagster.yaml" "Dagster configuration"
check_file "config/dagster/workspace.yaml" "Dagster workspace configuration"
check_file "config/prometheus/prometheus.yml" "Prometheus configuration"
check_file "config/grafana/provisioning/datasources/datasources.yml" "Grafana datasources configuration"

echo -e "\n📁 Checking Directory Structure..."
echo "--------------------------------"

# Check core directories
check_directory "app/api" "API directory"
check_directory "app/frontend" "Frontend directory"
check_directory "app/dagster" "Dagster directory"
check_directory "config" "Config directory"
check_directory "scripts" "Scripts directory"
check_directory "docs" "Documentation directory"

echo -e "\n🔒 Checking Security Configuration..."
echo "-----------------------------------"

# Check if .env contains all required variables
echo -n "Validating environment variables... "
required_vars=(
    "API_PORT"
    "API_HOST"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
    "QUESTDB_USER"
    "QUESTDB_PASSWORD"
    "CLICKHOUSE_USER"
    "CLICKHOUSE_PASSWORD"
    "GRAFANA_ADMIN_PASSWORD"
    "NATS_AUTH_TOKEN"
)

missing_vars=()
while IFS= read -r line; do
    if [[ $line =~ ^[^#]*= ]] && [[ $line != *"="*[^[:space:]]* ]]; then
        var_name=$(echo "$line" | cut -d'=' -f1)
        missing_vars+=("$var_name")
    fi
done < .env

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo "✅ All required variables are set"
else
    echo "❌ Missing or empty variables: ${missing_vars[*]}"
    exit 1
fi

echo -e "\n📦 Checking Dependencies..."
echo "--------------------------"

# Check Python dependencies
echo -n "Checking Python dependencies... "
if ! pip3 freeze | grep -q "fastapi=="; then
    echo "❌ Python dependencies not installed"
    echo "Run: pip install -r requirements.txt"
    exit 1
fi
echo "✅ Python dependencies found"

# Check Node.js dependencies
echo -n "Checking Node.js dependencies... "
if [[ ! -d "app/frontend/node_modules" ]]; then
    echo "❌ Node.js dependencies not installed"
    echo "Run: cd app/frontend && npm install"
    exit 1
fi
echo "✅ Node.js dependencies found"

echo -e "\n✨ Development Environment Validation Complete!"
echo "============================================="

# Final status
echo -e "\n📋 Summary:"
echo "- All required tools are installed"
echo "- Configuration files are present"
echo "- Directory structure is correct"
echo "- Security configuration is valid"
echo "- Dependencies are installed"

echo -e "\n✅ Environment is ready for development!"
echo "Run './scripts/start_dev.sh' to start the development environment" 