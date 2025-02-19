"""
Distributed tracing module using OpenTelemetry.
"""
from typing import Optional, Dict, Any
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from fastapi import FastAPI
from app.api.core.config.settings import settings
from ..logging.logger import logger

class TracingManager:
    """Manages distributed tracing configuration and lifecycle."""
    
    def __init__(self):
        """Initialize tracing manager."""
        self._tracer_provider: Optional[TracerProvider] = None
        self._initialized = False
    
    def init_tracing(self, app: FastAPI) -> None:
        """Initialize tracing for the application."""
        if self._initialized:
            return
            
        try:
            # Create tracer provider
            self._tracer_provider = TracerProvider()
            trace.set_tracer_provider(self._tracer_provider)
            
            # Configure OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.OTLP_ENDPOINT,
                insecure=not settings.OTLP_SECURE
            )
            
            # Add span processor
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            
            # Instrument FastAPI
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self._tracer_provider,
                excluded_urls=settings.TRACE_EXCLUDED_URLS
            )
            
            self._initialized = True
            logger.info("Tracing initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize tracing", error=e)
            # Don't raise - tracing should not break the application
    
    def get_tracer(self, name: str = "thedata.io"):
        """Get a tracer instance."""
        return trace.get_tracer(name)
    
    def start_span(
        self,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None
    ) -> trace.Span:
        """Start a new span."""
        tracer = self.get_tracer()
        
        # Create span with context if provided
        if context:
            carrier = {}
            TraceContextTextMapPropagator().inject(carrier, context)
            ctx = TraceContextTextMapPropagator().extract(carrier=carrier)
            span = tracer.start_span(name, context=ctx, kind=kind)
        else:
            span = tracer.start_span(name, kind=kind)
        
        return span
    
    def inject_context(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Inject trace context into carrier headers."""
        carrier = {}
        TraceContextTextMapPropagator().inject(carrier, context)
        return carrier
    
    def extract_context(self, carrier: Dict[str, str]) -> trace.SpanContext:
        """Extract trace context from carrier headers."""
        return TraceContextTextMapPropagator().extract(carrier=carrier)
    
    def add_span_attributes(self, span: trace.Span, attributes: Dict[str, Any]) -> None:
        """Add attributes to a span."""
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
    
    def record_exception(
        self,
        span: trace.Span,
        exception: Exception,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an exception in a span."""
        span.record_exception(exception)
        if attributes:
            self.add_span_attributes(span, attributes)
    
    def cleanup(self) -> None:
        """Clean up tracing resources."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()
            self._initialized = False
            logger.info("Tracing cleaned up successfully")

# Create global tracing instance
tracer = TracingManager()

__all__ = ['tracer', 'TracingManager'] 