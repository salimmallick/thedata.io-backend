#!/bin/bash

# Exit on error
set -e

echo "🧪 Running Tests for TheData.io Platform..."
echo "======================================"

# Function to print section header
print_header() {
    echo -e "\n📌 $1"
    echo "$(printf '=%.0s' {1..${#1}})"
}

# Function to run tests with coverage
run_tests_with_coverage() {
    local test_path=$1
    local module=$2
    
    echo "Running tests for $module..."
    pytest \
        --cov=$test_path \
        --cov-report=term-missing \
        --cov-report=html:coverage_reports/$module \
        -v \
        $test_path
}

# Create coverage reports directory
mkdir -p coverage_reports

# Ensure we're in development environment
if [ "$ENVIRONMENT" != "development" ]; then
    export ENVIRONMENT=development
fi

# Install test dependencies if needed
print_header "Checking Test Dependencies"
pip install -r requirements-test.txt

# Run API tests
print_header "Running API Tests"
run_tests_with_coverage "app/api" "api"

# Run Pipeline tests
print_header "Running Pipeline Tests"
run_tests_with_coverage "app/dagster" "pipeline"

# Run Integration tests
print_header "Running Integration Tests"
pytest -v app/tests/integration/

# Run Frontend tests
print_header "Running Frontend Tests"
(
    cd app/frontend
    npm test -- --coverage
)

# Run E2E tests if specified
if [ "$1" = "--e2e" ]; then
    print_header "Running E2E Tests"
    (
        cd app/frontend
        npm run test:e2e
    )
fi

# Generate combined coverage report
print_header "Generating Coverage Report"
coverage combine coverage_reports/*/
coverage report
coverage html -d coverage_reports/combined

# Run linting
print_header "Running Linters"

echo "Running Python linters..."
flake8 app/
pylint app/
mypy app/

echo "Running Frontend linters..."
(
    cd app/frontend
    npm run lint
    npm run type-check
)

# Print summary
print_header "Test Summary"
echo "
Test Results:
------------
✓ API Tests
✓ Pipeline Tests
✓ Integration Tests
✓ Frontend Tests
✓ Linting Checks

Coverage reports are available in:
--------------------------------
• API Coverage:      coverage_reports/api/index.html
• Pipeline Coverage: coverage_reports/pipeline/index.html
• Frontend Coverage: app/frontend/coverage/lcov-report/index.html
• Combined Coverage: coverage_reports/combined/index.html
"

echo "✨ All tests completed successfully!" 