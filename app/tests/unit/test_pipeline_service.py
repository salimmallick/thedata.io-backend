import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime
from app.api.services.pipeline import (
    PipelineService,
    EventProcessor,
    MetricsProcessor,
    VideoProcessor,
    LogProcessor
)

@pytest.mark.asyncio
async def test_pipeline_service_init():
    """Test pipeline service initialization."""
    processor = EventProcessor("test_events", ["user_events"])
    assert processor.name == "test_events"
    assert processor.topics == ["user_events"]
    assert processor._stop is False
    assert len(processor._tasks) == 0

@pytest.mark.asyncio
async def test_pipeline_service_start():
    """Test pipeline service start."""
    processor = EventProcessor("test_events", ["user_events"])
    await processor.start()
    assert len(processor._tasks) == 1
    assert not processor._stop
    await processor.stop()  # Cleanup

@pytest.mark.asyncio
async def test_pipeline_service_stop():
    """Test pipeline service stop."""
    processor = EventProcessor("test_events", ["user_events"])
    await processor.start()
    await processor.stop()
    assert processor._stop is True
    assert len(processor._tasks) == 0

@pytest.mark.asyncio
async def test_event_processor():
    """Test EventProcessor functionality."""
    with patch('app.api.services.pipeline.get_clickhouse_client') as mock_ch_client:
        # Setup mocks
        mock_client = AsyncMock()
        mock_ch_client.return_value.__aenter__.return_value = mock_client

        # Create processor
        processor = EventProcessor("test_events", ["user_events"])

        # Test message processing
        test_data = {
            "event_id": "test-123",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "click",
            "event_name": "button_click",
            "properties": {"button_id": "submit"}
        }

        await processor.process_message("user_events", test_data)

        # Verify ClickHouse insert was called
        mock_client.execute.assert_called_once()
        # Verify the query contains the event data
        call_args = mock_client.execute.call_args[0]
        assert "INSERT INTO events" in call_args[0]
        assert test_data["event_id"] in str(call_args[1][0])

@pytest.mark.asyncio
async def test_metrics_processor():
    """Test MetricsProcessor functionality."""
    with patch('app.api.services.pipeline.get_questdb_sender') as mock_questdb:
        # Setup mocks
        mock_sender = AsyncMock()
        mock_questdb.return_value.__aenter__.return_value = mock_sender

        # Create processor
        processor = MetricsProcessor("test_metrics", ["performance_metrics"])

        # Test message processing
        test_data = {
            "name": "response_time",
            "value": 100,
            "source": "api_server",
            "timestamp": datetime.utcnow().isoformat()
        }

        await processor.process_message("performance_metrics", test_data)

        # Verify QuestDB writes
        mock_sender.table.assert_called_once_with(test_data["name"])
        mock_sender.symbol.assert_called_once_with("source", test_data["source"])
        mock_sender.float.assert_called_once_with("value", test_data["value"])
        mock_sender.flush.assert_called_once()

@pytest.mark.asyncio
async def test_video_processor():
    """Test video analytics processing."""
    with patch('app.api.services.pipeline.get_clickhouse_client') as mock_ch_client:
        # Setup mocks
        mock_client = AsyncMock()
        mock_ch_client.return_value.__aenter__.return_value = mock_client

        # Create processor
        processor = VideoProcessor("video_events", ["video_analytics"])

        # Test message processing
        test_data = {
            "video_id": "test123",
            "timestamp": "2024-02-12T00:00:00Z",
            "metrics": {
                "views": 100,
                "likes": 50,
                "comments": 25
            }
        }

        await processor.process_message("video_analytics", test_data)

        # Verify processing was successful
        assert mock_client.execute.call_count == 0  # No database operations in current implementation

@pytest.mark.asyncio
async def test_log_processor():
    """Test log processing."""
    with patch('app.api.services.pipeline.get_clickhouse_client') as mock_ch_client:
        # Setup mocks
        mock_client = AsyncMock()
        mock_ch_client.return_value.__aenter__.return_value = mock_client

        # Create processor
        processor = LogProcessor("log_events", ["error_logs"])

        # Test message processing
        test_data = {
            "log_id": "error123",
            "timestamp": "2024-02-12T00:00:00Z",
            "level": "ERROR",
            "message": "Test error message",
            "service": "api",
            "trace_id": "trace123"
        }

        await processor.process_message("error_logs", test_data)

        # Verify processing was successful
        assert mock_client.execute.call_count == 0  # No database operations in current implementation 