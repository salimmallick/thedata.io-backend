#!/bin/bash

# Exit on error
set -e

# Get environment from command line argument
ENV=$1

# Set base URL based on environment
case $ENV in
    "staging")
        BASE_URL="https://staging.thedata.io"
        ;;
    "production")
        BASE_URL="https://admin.thedata.io"
        ;;
    *)
        echo "Invalid environment specified"
        exit 1
        ;;
esac

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local expected_status=$2
    
    echo "Testing $BASE_URL$endpoint..."
    
    status_code=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL$endpoint)
    
    if [ $status_code -eq $expected_status ]; then
        echo "✅ $endpoint returned $status_code as expected"
        return 0
    else
        echo "❌ $endpoint returned $status_code, expected $expected_status"
        return 1
    fi
}

# Function to test static assets
test_static_asset() {
    local path=$1
    echo "Testing static asset $BASE_URL$path..."
    
    status_code=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL$path)
    
    if [ $status_code -eq 200 ]; then
        echo "✅ Static asset $path is accessible"
        return 0
    else
        echo "❌ Static asset $path returned $status_code"
        return 1
    fi
}

echo "Running smoke tests against $BASE_URL..."

# Test main page
test_endpoint "/" 200

# Test static assets
test_static_asset "/static/js/main.js"
test_static_asset "/static/css/main.css"
test_static_asset "/favicon.ico"

# Test authentication endpoints
test_endpoint "/login" 200
test_endpoint "/signup" 200

# Test API health check
test_endpoint "/api/health" 200

# Count failures
failures=0
for result in ${PIPESTATUS[@]}; do
    failures=$((failures + result))
done

if [ $failures -eq 0 ]; then
    echo "🎉 All smoke tests passed!"
    exit 0
else
    echo "💥 $failures smoke tests failed!"
    exit 1
fi 