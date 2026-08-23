"""
OpenTelemetry Python SDK Instrumentation Module
Chuẩn hóa theo mã nguồn Downloads/observability/observability/src/telemetry.py
Khởi tạo và cấu hình TracerProvider, MeterProvider, LoggerProvider
đẩy toàn bộ Telemetry (Traces, Metrics, Logs) sang OpenTelemetry Collector qua gRPC (:4317).
"""
import logging
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable
from fastapi import FastAPI, Request, Response

# Khởi tạo mặc định tracer và meter
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

    # 1. Khởi tạo Resource định danh Service Name
    svc_name = os.getenv("OTEL_SERVICE_NAME", "ecom-agent-service")
    resource = Resource.create({"service.name": svc_name})

    # 2. Khởi tạo Tracer Provider (Distributed Tracing -> Jaeger/Langfuse)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(__name__)

    # 3. Khởi tạo Meter Provider (Metrics -> Prometheus/OTel)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
    )
    metrics.set_meter_provider(meter_provider)

    # 4. Khởi tạo Logger Provider (Centralized Logging -> Elasticsearch/Kibana)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(logging.StreamHandler())
    root.addHandler(LoggingHandler(logger_provider=logger_provider))

except Exception as e:
    logging.getLogger("telemetry").info(f"OpenTelemetry SDK optional fallback mode: {e}")


# 5. Helpers & FastAPI Telemetry Middleware
@contextmanager
def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager bọc trace span chuẩn OpenTelemetry SDK.
    """
    if tracer is not None:
        with tracer.start_as_current_span(span_name) as span:
            if attributes and span.is_recording():
                for key, val in attributes.items():
                    span.set_attribute(key, str(val))
            yield span
    else:
        yield None


def setup_telemetry(app: FastAPI, service_name: str = "web-api") -> None:
    """
    Đăng ký Telemetry middleware cho FastAPI Application.
    Tự động ghi nhận Traces, Latency và HTTP Status Code.
    """
    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method
        if tracer is not None:
            with tracer.start_as_current_span(f"{method} {path}") as span:
                span.set_attribute("http.method", method)
                span.set_attribute("http.url", str(request.url))
                span.set_attribute("http.route", path)
                try:
                    response = await call_next(request)
                    span.set_attribute("http.status_code", response.status_code)
                    return response
                except Exception as exc:
                    span.set_attribute("http.status_code", 500)
                    span.record_exception(exc)
                    raise exc from None
        else:
            return await call_next(request)
