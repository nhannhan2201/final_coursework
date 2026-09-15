"""
OpenTelemetry Python SDK Instrumentation Module cho Agentic AI & FastMCP
Khởi tạo và cấu hình TracerProvider, MeterProvider, LoggerProvider
đẩy toàn bộ Telemetry (Traces, Metrics, Logs) sang OpenTelemetry Collector qua gRPC (:4317).
"""
import logging
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable

tracer = None
meter = None

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    svc_name = os.getenv("OTEL_SERVICE_NAME", "mcp-service")
    resource = Resource.create({"service.name": svc_name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(__name__)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(logging.StreamHandler())
    root.addHandler(LoggingHandler(logger_provider=logger_provider))

except Exception as e:
    logging.getLogger("telemetry").info(f"OpenTelemetry SDK optional fallback mode: {e}")


@contextmanager
def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager bọc trace span chuẩn OpenTelemetry SDK."""
    if tracer is not None:
        with tracer.start_as_current_span(span_name) as span:
            if attributes and span.is_recording():
                for key, val in attributes.items():
                    span.set_attribute(key, str(val))
            yield span
    else:
        yield None
