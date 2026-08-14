"""
==============================================================================
MÔ TẢ FILE: apps/telemetry.py
------------------------------------------------------------------------------
Module OpenTelemetry & Prometheus Telemetry Instrumentation cho Web API 
và MCP Agent Services trong hệ thống E-Commerce MLOps.

Chức năng chính:
1. Khởi tạo Prometheus Metrics (HTTP Requests, Latency, Tool Calls, LLM Tokens).
2. Tích hợp FastAPI Middleware ghi nhận thời gian thực (Real-time tracking).
3. Expose endpoint /metrics cho Prometheus Scraper.
==============================================================================
"""

import time
import os
from typing import Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ------------------------------------------------------------------------------
# Prometheus Metrics Definitions
# ------------------------------------------------------------------------------

# Web API Telemetry Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Tổng số lượt HTTP Requests nhận được",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Thời gian xử lý HTTP Request (seconds)",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Agent & MCP Tool Telemetry Metrics
MCP_TOOL_CALLS_TOTAL = Counter(
    "mcp_tool_calls_total",
    "Tổng số lượt gọi MCP Tool",
    ["tool_name", "status"]
)

MCP_TOOL_EXECUTION_DURATION_SECONDS = Histogram(
    "mcp_tool_execution_duration_seconds",
    "Thời gian thi hành MCP Tool (seconds)",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# LLM Inference Telemetry Metrics
LLM_PROMPT_TOKENS_TOTAL = Counter(
    "llm_prompt_tokens_total",
    "Tổng số Token đầu vào (Prompt Tokens) tiêu tốn cho LLM",
    ["model"]
)

LLM_COMPLETION_TOKENS_TOTAL = Counter(
    "llm_completion_tokens_total",
    "Tổng số Token đầu ra (Completion Tokens) do LLM sinh ra",
    ["model"]
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "Thời gian phản hồi tổng cộng từ LLM Inference Server (seconds)",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# ------------------------------------------------------------------------------
# FastAPI Telemetry Setup Function
# ------------------------------------------------------------------------------

def setup_telemetry(app: FastAPI, service_name: str = "web-api") -> None:
    """
    Nhúng Prometheus Telemetry Middleware và Endpoint /metrics vào ứng dụng FastAPI.
    """
    
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        path = request.url.path
        method = request.method
        
        # Bỏ qua không ghi nhận métrics cho chính endpoint /metrics và /health
        if path in ["/metrics", "/health", "/favicon.ico"]:
            return await call_next(request)
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as exc:
            status_code = "500"
            raise exc from None
        finally:
            duration = time.time() - start_time
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status=status_code).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(duration)
            
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        """
        Endpoint trả về định dạng plain-text chuẩn Prometheus cho Prometheus Scraper.
        """
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ------------------------------------------------------------------------------
# Helper Functions cho Agent & LLM Instrumentation
# ------------------------------------------------------------------------------

def record_mcp_tool_call(tool_name: str, status: str = "success", duration_seconds: float = 0.0) -> None:
    """
    Ghi nhận chỉ số gọi MCP Tool (Thành công/Thất bại & Thời gian thi hành).
    """
    MCP_TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status=status).inc()
    if duration_seconds > 0:
        MCP_TOOL_EXECUTION_DURATION_SECONDS.labels(tool_name=tool_name).observe(duration_seconds)


def record_llm_metrics(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_seconds: float = 0.0
) -> None:
    """
    Ghi nhận chỉ số LLM Inference (Prompt Tokens, Completion Tokens & Total Latency).
    """
    if prompt_tokens > 0:
        LLM_PROMPT_TOKENS_TOTAL.labels(model=model).inc(prompt_tokens)
    if completion_tokens > 0:
        LLM_COMPLETION_TOKENS_TOTAL.labels(model=model).inc(completion_tokens)
    if duration_seconds > 0:
        LLM_REQUEST_DURATION_SECONDS.labels(model=model).observe(duration_seconds)

