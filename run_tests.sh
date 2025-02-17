#!/bin/bash

# Function to show usage
show_usage() {
    echo "Usage: ./run_tests.sh [options] [test_path]"
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -r, --rebuild  Rebuild the test container"
    echo "Examples:"
    echo "  ./run_tests.sh                               # Run all tests"
    echo "  ./run_tests.sh app/tests/test_nats.py       # Run specific test file"
    echo "  ./run_tests.sh -r app/tests/test_nats.py    # Rebuild and run specific test"
}

# Default values
REBUILD=false
TEST_PATH="app/tests"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        *)
            TEST_PATH=$1
            shift
            ;;
    esac
done

# Stop and remove all containers
docker compose -f docker-compose.test.yml down -v

# Start only the NATS service
docker compose -f docker-compose.test.yml up -d nats-test

# Wait for NATS to be healthy
echo "Waiting for NATS to be healthy..."
until curl -s http://localhost:8223/healthz > /dev/null; do
    sleep 1
done
echo "NATS is healthy"

# Run the specific test
docker compose -f docker-compose.test.yml run --rm nats-test-runner pytest app/tests/test_nats.py::test_basic_pub_sub -vv -s --log-cli-level=INFO --tb=short 