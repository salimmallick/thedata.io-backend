import pytest
import asyncio
import time
from datetime import datetime, timedelta
from app.api.core.database import (
    postgres,
    clickhouse,
    questdb,
    materialize
)

@pytest.mark.asyncio
async def test_metrics_flow():
    """Test data flow from metrics ingestion to real-time analytics"""
    # Insert test metric into ClickHouse
    timestamp = datetime.utcnow()
    test_metric = {
        'timestamp': timestamp,
        'name': 'test_metric',
        'value': 100.0,
        'labels': {'env': 'test'},
        'organization_id': 'test_org',
        'source': 'integration_test'
    }
    
    await clickhouse.execute(
        """
        INSERT INTO metrics (timestamp, name, value, labels, organization_id, source)
        VALUES
        """,
        [test_metric]
    )
    
    # Wait for materialization
    await asyncio.sleep(2)
    
    # Verify metric appears in Materialize view
    result = await materialize.execute(
        """
        SELECT * FROM rt_metrics 
        WHERE name = 'test_metric' 
        AND organization_id = 'test_org'
        """
    )
    assert len(result) > 0
    assert result[0]['value'] == 100.0

@pytest.mark.asyncio
async def test_event_flow():
    """Test data flow from events to analytics"""
    # Insert test event into ClickHouse
    timestamp = datetime.utcnow()
    test_event = {
        'timestamp': timestamp,
        'event_type': 'test_event',
        'source': 'integration_test',
        'organization_id': 'test_org',
        'user_id': 'test_user'
    }
    
    await clickhouse.execute(
        """
        INSERT INTO events (timestamp, event_type, source, organization_id, user_id)
        VALUES
        """,
        [test_event]
    )
    
    # Wait for materialization
    await asyncio.sleep(2)
    
    # Verify event appears in Materialize view
    result = await materialize.execute(
        """
        SELECT * FROM rt_events 
        WHERE event_type = 'test_event' 
        AND organization_id = 'test_org'
        """
    )
    assert len(result) > 0
    assert result[0]['event_count'] > 0

@pytest.mark.asyncio
async def test_error_alert_flow():
    """Test error alert flow from API metrics to alert sink"""
    # Insert test API metrics with high error rate
    timestamp = datetime.utcnow()
    test_metrics = []
    for _ in range(10):
        test_metrics.append({
            'timestamp': timestamp,
            'endpoint': '/test',
            'method': 'GET',
            'organization_id': 'test_org',
            'duration_ms': 100,
            'status_code': 500,
            'client_ip': '127.0.0.1'
        })
    
    await clickhouse.execute(
        """
        INSERT INTO api_metrics (
            timestamp, endpoint, method, organization_id,
            duration_ms, status_code, client_ip
        ) VALUES
        """,
        test_metrics
    )
    
    # Wait for alert processing
    await asyncio.sleep(5)
    
    # Verify alert was generated
    result = await materialize.execute(
        """
        SELECT * FROM error_rate_alerts 
        WHERE organization_id = 'test_org'
        AND error_rate > 0.1
        """
    )
    assert len(result) > 0

@pytest.mark.asyncio
async def test_performance_metrics_flow():
    """Test system performance metrics flow to QuestDB"""
    # Insert test performance metric
    timestamp = datetime.utcnow()
    test_metric = {
        'timestamp': timestamp,
        'host': 'test_host',
        'cpu_usage': 50.0,
        'memory_used': 4096,
        'memory_total': 8192,
        'disk_used': 100000,
        'disk_total': 500000
    }
    
    await questdb.execute(
        """
        INSERT INTO performance_metrics (
            timestamp, host, cpu_usage, memory_used,
            memory_total, disk_used, disk_total
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp, test_metric['host'], test_metric['cpu_usage'],
            test_metric['memory_used'], test_metric['memory_total'],
            test_metric['disk_used'], test_metric['disk_total']
        )
    )
    
    # Query back the metric
    result = await questdb.execute(
        """
        SELECT * FROM performance_metrics
        WHERE host = 'test_host'
        AND timestamp = ?
        """,
        (timestamp,)
    )
    assert len(result) > 0
    assert result[0]['cpu_usage'] == 50.0 