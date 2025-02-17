#!/bin/bash

# Exit on any error
set -e

echo "🔍 Validating Message Queue Configuration..."
echo "========================================"

# Function to check NATS connection
check_nats_connection() {
    echo -n "Checking NATS connection... "
    if curl -s http://localhost:8222/varz > /dev/null; then
        echo "✅"
        return 0
    else
        echo "❌"
        return 1
    fi
}

# Function to check JetStream
check_jetstream() {
    echo -n "Checking JetStream... "
    if curl -s http://localhost:8222/jsz > /dev/null; then
        echo "✅"
        return 0
    else
        echo "❌"
        return 1
    fi
}

# Function to check stream existence
check_stream() {
    local stream=$1
    echo -n "Checking stream $stream... "
    if curl -s http://localhost:8222/streamz | grep -q "\"name\":\"$stream\""; then
        echo "✅"
        return 0
    else
        echo "❌"
        return 1
    fi
}

# Function to check consumer existence
check_consumer() {
    local stream=$1
    local consumer=$2
    echo -n "Checking consumer $consumer on stream $stream... "
    if curl -s "http://localhost:8222/consumerz/$stream/$consumer" | grep -q "\"name\":\"$consumer\""; then
        echo "✅"
        return 0
    else
        echo "❌"
        return 1
    fi
}

# Check NATS Server Status
echo -e "\n📊 Checking NATS Server Status..."
echo "------------------------------"
check_nats_connection

# Check JetStream Status
echo -e "\n📊 Checking JetStream Status..."
echo "----------------------------"
check_jetstream

# Check Core Streams
echo -e "\n📊 Checking Core Streams..."
echo "------------------------"
check_stream "EVENTS"
check_stream "METRICS"
check_stream "LOGS"

# Check Core Consumers
echo -e "\n📊 Checking Core Consumers..."
echo "--------------------------"
check_consumer "EVENTS" "event_processor"
check_consumer "METRICS" "metrics_processor"
check_consumer "LOGS" "log_processor"

# Check Stream Configuration
echo -e "\n📊 Checking Stream Configuration..."
echo "--------------------------------"

# Get and validate EVENTS stream config
echo "Validating EVENTS stream configuration..."
curl -s http://localhost:8222/streamz/EVENTS | jq -r '.config | {
    retention: .retention,
    max_msgs_per_subject: .max_msgs_per_subject,
    max_bytes: .max_bytes,
    max_age: .max_age
}'

# Get and validate METRICS stream config
echo -e "\nValidating METRICS stream configuration..."
curl -s http://localhost:8222/streamz/METRICS | jq -r '.config | {
    retention: .retention,
    max_msgs_per_subject: .max_msgs_per_subject,
    max_bytes: .max_bytes,
    max_age: .max_age
}'

# Check Stream Health
echo -e "\n🏥 Checking Stream Health..."
echo "-------------------------"

# Check message counts
echo "Message counts:"
curl -s http://localhost:8222/streamz | jq -r '.streams[] | "\(.name): \(.messages) messages"'

# Check consumer lag
echo -e "\nConsumer lag:"
for stream in EVENTS METRICS LOGS; do
    echo "$stream stream:"
    curl -s "http://localhost:8222/consumerz/$stream" | jq -r '.consumers[] | "\(.name): \(.num_pending) pending messages"'
done

# Summary
echo -e "\n📋 Validation Summary:"
echo "--------------------"
echo "✅ NATS server is running"
echo "✅ JetStream is enabled"
echo "✅ Core streams are configured"
echo "✅ Core consumers are configured"

# Check for any warnings
warnings=0
echo -e "\n⚠️  Warnings:"
echo "-----------"

# Check for high message counts
high_message_count=$(curl -s http://localhost:8222/streamz | jq -r '.streams[] | select(.messages > 1000000) | .name')
if [ ! -z "$high_message_count" ]; then
    echo "- High message count in streams: $high_message_count"
    warnings=$((warnings + 1))
fi

# Check for high consumer lag
high_lag=$(curl -s http://localhost:8222/consumerz | jq -r '.[] | select(.num_pending > 10000) | .name')
if [ ! -z "$high_lag" ]; then
    echo "- High consumer lag in: $high_lag"
    warnings=$((warnings + 1))
fi

if [ $warnings -eq 0 ]; then
    echo "No warnings found"
fi

echo -e "\n✨ Message queue validation complete!" 