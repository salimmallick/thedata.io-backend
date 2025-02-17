#!/bin/bash

# Exit on error
set -e

echo "🏥 Running Health Checks for TheData.io Platform..."
echo "=============================================="

# Function to check HTTP endpoint
check_http_endpoint() {
    local service=$1
    local url=$2
    local expected_status=$3
    local timeout=$4
    local critical=$5

    echo -n "Checking $service... "
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $timeout "$url" || echo "failed")
    
    if [ "$response" = "$expected_status" ]; then
        echo "✅"
        return 0
    else
        echo "❌ (Status: $response)"
        if [ "$critical" = "true" ]; then
            return 1
        fi
        return 0
    fi
}

# Function to check TCP port
check_tcp_port() {
    local service=$1
    local host=$2
    local port=$3
    local critical=$4

    echo -n "Checking $service... "
    if nc -z -w5 $host $port; then
        echo "✅"
        return 0
    else
        echo "❌"
        if [ "$critical" = "true" ]; then
            return 1
        fi
        return 0
    fi
}

# Function to check Docker container status
check_container() {
    local service=$1
    local critical=$2

    echo -n "Checking $service container... "
    if docker-compose -f docker-compose.dev.yml ps --quiet $service | xargs docker inspect -f '{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        echo "✅"
        return 0
    else
        echo "❌"
        if [ "$critical" = "true" ]; then
            return 1
        fi
        return 0
    fi
}

echo -e "\n📊 Checking Core Services..."
echo "-------------------------"

# Check API
check_http_endpoint "API" "http://localhost:8000/health" "200" "5" "true"
check_container "api" "true"

# Check Databases
check_tcp_port "PostgreSQL" "localhost" "5432" "true"
check_tcp_port "ClickHouse HTTP" "localhost" "8123" "true"
check_tcp_port "ClickHouse Native" "localhost" "9000" "true"
check_tcp_port "QuestDB" "localhost" "8812" "true"
check_container "postgres" "true"
check_container "clickhouse" "true"
check_container "questdb" "true"

# Check Message Queue
check_tcp_port "NATS" "localhost" "4222" "true"
check_http_endpoint "NATS Monitoring" "http://localhost:8222/varz" "200" "5" "true"
check_container "nats" "true"

# Check Cache
check_tcp_port "Redis" "localhost" "6379" "true"
check_container "redis" "true"

echo -e "\n📊 Checking Data Pipeline..."
echo "-------------------------"

# Check Dagster
check_http_endpoint "Dagster" "http://localhost:3002/health" "200" "5" "true"
check_container "dagster" "true"

# Check Materialize
check_tcp_port "Materialize" "localhost" "6875" "true"
check_container "materialize" "true"

echo -e "\n📊 Checking Monitoring Stack..."
echo "----------------------------"

# Check Monitoring
check_http_endpoint "Grafana" "http://localhost:3001/api/health" "200" "5" "false"
check_http_endpoint "Prometheus" "http://localhost:9090/-/healthy" "200" "5" "false"
check_container "grafana" "false"
check_container "prometheus" "false"

# Check Traefik
check_http_endpoint "Traefik" "http://localhost:8080/ping" "200" "5" "true"
check_container "traefik" "true"

echo -e "\n📊 Checking Resource Usage..."
echo "---------------------------"

# Check container resource usage
echo "Container Resource Usage:"
docker stats --no-stream $(docker-compose -f docker-compose.dev.yml ps -q)

# Check for container warnings/errors
echo -e "\n📊 Checking Container Logs for Errors..."
echo "-----------------------------------"
for service in api dagster postgres clickhouse questdb nats redis materialize grafana prometheus traefik; do
    echo "Checking $service logs..."
    docker-compose -f docker-compose.dev.yml logs --tail=50 $service | grep -i "error" || echo "No errors found in $service logs"
done

# Final Status
echo -e "\n📋 Health Check Summary:"
echo "---------------------"
total_containers=$(docker-compose -f docker-compose.dev.yml ps -q | wc -l)
running_containers=$(docker-compose -f docker-compose.dev.yml ps -q | xargs docker inspect -f '{{.State.Running}}' | grep -c "true")

echo "Total Containers: $total_containers"
echo "Running Containers: $running_containers"

if [ "$total_containers" -eq "$running_containers" ]; then
    echo "✅ All containers are running"
else
    echo "❌ Some containers are not running ($running_containers/$total_containers)"
    exit 1
fi

echo -e "\n✨ Health check complete!" 