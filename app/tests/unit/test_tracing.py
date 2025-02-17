import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from app.api.core.tracing import TracingManager, tracing
from app.api.core.config import settings

@pytest.fixture
def mock_app():
    """Create a mock FastAPI application"""
    return FastAPI()

@pytest.fixture
def tracing_manager():
    """Create a test tracing manager instance"""
    return TracingManager()

@pytest.mark.asyncio
async def test_tracing_initialization(tracing_manager, mock_app):
    """Test tracing system initialization"""
    # Initialize tracing
    tracing_manager.init_tracing(mock_app)
    
    # Verify tracer provider is set up
    assert tracing_manager._tracer_provider is not None
    assert isinstance(tracing_manager._tracer_provider, TracerProvider)
    
    # Verify Jaeger exporter is set up
    assert tracing_manager._jaeger_exporter is not None
    
    # Clean up
    tracing_manager.cleanup()

@pytest.mark.asyncio
async def test_tracing_cleanup(tracing_manager, mock_app):
    """Test tracing system cleanup"""
    # Initialize first
    tracing_manager.init_tracing(mock_app)
    
    # Clean up
    tracing_manager.cleanup()
    
    # Verify cleanup
    assert tracing_manager._tracer_provider is None
    assert tracing_manager._jaeger_exporter is None

@pytest.mark.asyncio
async def test_tracing_configuration(tracing_manager, mock_app):
    """Test tracing configuration"""
    with patch('opentelemetry.sdk.trace.TracerProvider') as mock_provider:
        tracing_manager.init_tracing(mock_app)
        
        # Verify service name and environment are set
        resource_args = mock_provider.call_args[1]['resource'].attributes
        assert resource_args['service.name'] == "thedata-api"
        assert resource_args['environment'] == settings.ENVIRONMENT

@pytest.mark.asyncio
async def test_span_processor_setup(tracing_manager, mock_app):
    """Test span processor configuration"""
    tracing_manager.init_tracing(mock_app)
    
    # Verify BatchSpanProcessor is set up
    processors = tracing_manager._tracer_provider._active_span_processor._span_processors
    assert any(isinstance(p, BatchSpanProcessor) for p in processors)
    
    # Clean up
    tracing_manager.cleanup()

@pytest.mark.asyncio
async def test_jaeger_exporter_configuration(tracing_manager, mock_app):
    """Test Jaeger exporter configuration"""
    with patch('opentelemetry.exporter.jaeger.thrift.JaegerExporter') as mock_exporter:
        tracing_manager.init_tracing(mock_app)
        
        # Verify Jaeger configuration
        mock_exporter.assert_called_once_with(
            agent_host_name=settings.JAEGER_AGENT_HOST,
            agent_port=settings.JAEGER_AGENT_PORT,
            udp_split_oversized_batches=True
        )

@pytest.mark.asyncio
async def test_fastapi_instrumentation(tracing_manager, mock_app):
    """Test FastAPI instrumentation"""
    with patch('opentelemetry.instrumentation.fastapi.FastAPIInstrumentor') as mock_instrumentor:
        tracing_manager.init_tracing(mock_app)
        
        # Verify FastAPI instrumentation
        mock_instrumentor.instrument_app.assert_called_once_with(mock_app)

@pytest.mark.asyncio
async def test_tracing_error_handling(tracing_manager, mock_app):
    """Test error handling during tracing initialization"""
    with patch('opentelemetry.sdk.trace.TracerProvider', side_effect=Exception("Tracing error")):
        with pytest.raises(Exception) as exc_info:
            tracing_manager.init_tracing(mock_app)
        assert "Tracing error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_cleanup_error_handling(tracing_manager, mock_app):
    """Test error handling during cleanup"""
    # Initialize tracing
    tracing_manager.init_tracing(mock_app)
    
    # Mock cleanup error
    with patch.object(
        tracing_manager._tracer_provider,
        'shutdown',
        side_effect=Exception("Cleanup error")
    ):
        # Should not raise exception
        tracing_manager.cleanup()
        assert tracing_manager._tracer_provider is None

@pytest.mark.asyncio
async def test_tracing_singleton(mock_app):
    """Test tracing manager singleton instance"""
    # Get global instance
    global_instance = tracing
    
    # Initialize tracing
    global_instance.init_tracing(mock_app)
    
    # Verify it's properly initialized
    assert global_instance._tracer_provider is not None
    assert global_instance._jaeger_exporter is not None
    
    # Clean up
    global_instance.cleanup()

@pytest.mark.asyncio
async def test_multiple_initialization(tracing_manager, mock_app):
    """Test multiple initialization handling"""
    # First initialization
    tracing_manager.init_tracing(mock_app)
    first_provider = tracing_manager._tracer_provider
    
    # Second initialization
    tracing_manager.init_tracing(mock_app)
    second_provider = tracing_manager._tracer_provider
    
    # Should create new provider
    assert first_provider is not second_provider
    
    # Clean up
    tracing_manager.cleanup() 