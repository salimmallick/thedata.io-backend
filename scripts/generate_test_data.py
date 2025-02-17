#!/usr/bin/env python3
import asyncio
import random
import uuid
from datetime import datetime, timedelta
import httpx
import json
from typing import List, Dict, Any
import faker

fake = faker.Faker()

# Configuration
BASE_URL = "http://localhost:8000"
NUM_EVENTS = 1000
NUM_METRICS = 500
NUM_LOGS = 200

async def generate_user_events() -> List[Dict[str, Any]]:
    """Generate realistic user interaction events"""
    events = []
    platforms = ["web", "ios", "android"]
    event_types = ["page_view", "button_click", "form_submit", "scroll", "video_play"]
    
    for _ in range(NUM_EVENTS):
        timestamp = datetime.utcnow() - timedelta(
            minutes=random.randint(0, 60 * 24)  # Last 24 hours
        )
        
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "platform": random.choice(platforms),
            "event_type": "user_interaction",
            "event_name": random.choice(event_types),
            "properties": {
                "page": fake.uri_path(),
                "user_agent": fake.user_agent(),
                "screen_size": f"{random.randint(1024, 2560)}x{random.randint(768, 1600)}",
                "locale": fake.locale(),
            },
            "context": {
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "ip": fake.ipv4(),
                "country": fake.country_code(),
                "city": fake.city(),
            }
        }
        events.append(event)
    
    return events

async def generate_metrics() -> List[Dict[str, Any]]:
    """Generate system and application metrics"""
    metrics = []
    metric_names = [
        "api_latency", "cpu_usage", "memory_usage", "disk_io",
        "network_throughput", "error_rate", "request_count"
    ]
    
    for _ in range(NUM_METRICS):
        timestamp = datetime.utcnow() - timedelta(
            minutes=random.randint(0, 60 * 24)
        )
        
        metric = {
            "metric_id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "name": random.choice(metric_names),
            "value": random.uniform(0, 100),
            "tags": {
                "service": random.choice(["api", "worker", "database"]),
                "environment": "development",
                "host": f"host-{random.randint(1, 5)}"
            }
        }
        metrics.append(metric)
    
    return metrics

async def generate_logs() -> List[Dict[str, Any]]:
    """Generate application logs"""
    logs = []
    log_levels = ["info", "warn", "error", "debug"]
    services = ["api", "worker", "database", "cache"]
    
    for _ in range(NUM_LOGS):
        timestamp = datetime.utcnow() - timedelta(
            minutes=random.randint(0, 60 * 24)
        )
        
        log = {
            "log_id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "level": random.choice(log_levels),
            "service": random.choice(services),
            "message": fake.sentence(),
            "context": {
                "request_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()) if random.random() > 0.5 else None,
                "trace_id": str(uuid.uuid4())
            }
        }
        logs.append(log)
    
    return logs

async def ingest_data():
    """Ingest generated data into the platform"""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Ingest events
        events = await generate_user_events()
        for batch in [events[i:i+100] for i in range(0, len(events), 100)]:
            response = await client.post("/ingest/events", json=batch)
            print(f"Ingested {len(batch)} events: {response.status_code}")
        
        # Ingest metrics
        metrics = await generate_metrics()
        for batch in [metrics[i:i+100] for i in range(0, len(metrics), 100)]:
            response = await client.post("/ingest/metrics", json=batch)
            print(f"Ingested {len(batch)} metrics: {response.status_code}")
        
        # Ingest logs
        logs = await generate_logs()
        for batch in [logs[i:i+100] for i in range(0, len(logs), 100)]:
            response = await client.post("/ingest/logs", json=batch)
            print(f"Ingested {len(batch)} logs: {response.status_code}")

if __name__ == "__main__":
    print("Generating and ingesting test data...")
    asyncio.run(ingest_data())
    print("Done!") 