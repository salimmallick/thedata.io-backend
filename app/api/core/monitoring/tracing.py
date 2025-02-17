from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from .config import settings
import logging

logger = logging.getLogger(__name__)

class TracingManager:
    """Manager for distributed tracing"""
    
    def __init__(self):
        self._tracer_provider = None
        self._jaeger_exporter = None
    
    def init_tracing(self, app):
        """Initialize distributed tracing"""
        try:
            # Create tracer provider
            self._tracer_provider = TracerProvider(
                resource=Resource.create({
                    "service.name": settings.SERVICE_NAME,
                    "environment": settings.ENVIRONMENT
                })
            )
            
            # Create Jaeger exporter
            self._jaeger_exporter = JaegerExporter(
                agent_host_name=settings.JAEGER_HOST,
                agent_port=settings.JAEGER_PORT,
                udp_split_oversized_batches=True
            )
            
            # Add span processor
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(self._jaeger_exporter)
            )
            
            # Set tracer provider
            trace.set_tracer_provider(self._tracer_provider)
            
            # Instrument FastAPI
            FastAPIInstrumentor.instrument_app(app)
            
            logger.info("Distributed tracing initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {str(e)}")
            raise
    
    def cleanup(self):
        """Clean up tracing resources"""
        try:
            if self._tracer_provider:
                self._tracer_provider.shutdown()
                self._tracer_provider = None
            
            if self._jaeger_exporter:
                self._jaeger_exporter.shutdown()
                self._jaeger_exporter = None
            
            logger.info("Cleaned up tracing resources")
            
        except Exception as e:
            logger.error(f"Error during tracing cleanup: {str(e)}")

# Initialize tracing manager
tracing = TracingManager()

def setup_tracer() -> trace.Tracer:
    """Setup OpenTelemetry tracer with Jaeger exporter."""
    if not settings.JAEGER_ENABLED:
        logger.info("Tracing is disabled")
        return trace.get_tracer(__name__)

    try:
        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.JAEGER_HOST,
            agent_port=settings.JAEGER_PORT,
        )

        # Create TracerProvider with resource information
        resource = Resource.create({
            "service.name": settings.SERVICE_NAME,
            "environment": settings.ENVIRONMENT
        })

        # Set global TracerProvider
        trace.set_tracer_provider(
            TracerProvider(resource=resource)
        )

        # Add Jaeger exporter to TracerProvider
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )

        logger.info(
            f"Initialized tracer: Jaeger({settings.JAEGER_HOST}:{settings.JAEGER_PORT})"
        )
        return trace.get_tracer(__name__)

    except Exception as e:
        logger.error(f"Failed to initialize tracer: {str(e)}")
        return trace.get_tracer(__name__)

# Create global tracer instance
tracer = setup_tracer()

# Create propagator for distributed tracing
propagator = TraceContextTextMapPropagator()