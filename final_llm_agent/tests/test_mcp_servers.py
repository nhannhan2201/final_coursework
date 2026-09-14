"""
==============================================================================
KIỂM THỬ TỰ ĐỘNG FASTMCP SERVERS (E-COMMERCE & DRIFT DETECTION)
------------------------------------------------------------------------------
Kiểm thử trực tiếp 2 MCP Tools tinh gọn:
1. search_ecommerce_data: Tra cứu khách hàng, sản phẩm bán chạy, chính sách.
2. check_data_drift: Kiểm tra trôi lệch dữ liệu (KS-test và PSI).
==============================================================================
"""

import os
import json
import importlib.util
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Nạp trực tiếp từ agentic_ai/ecom-mcp/server.py
ecom_path = os.path.join(PROJECT_ROOT, "agentic_ai", "ecom-mcp", "server.py")
ecom_spec = importlib.util.spec_from_file_location("ecom_server", ecom_path)
ecom_server = importlib.util.module_from_spec(ecom_spec)
ecom_spec.loader.exec_module(ecom_server)

search_ecommerce_data = ecom_server.search_ecommerce_data
ecom_health_check = ecom_server.health_check

# Nạp trực tiếp từ agentic_ai/drift-mcp/server.py
drift_path = os.path.join(PROJECT_ROOT, "agentic_ai", "drift-mcp", "server.py")
drift_spec = importlib.util.spec_from_file_location("drift_server", drift_path)
drift_server = importlib.util.module_from_spec(drift_spec)
drift_spec.loader.exec_module(drift_server)

check_data_drift = drift_server.check_data_drift
drift_health_check = drift_server.health_check


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ------------------------------------------------------------------------------
# 1. Kiểm thử E-Commerce FastMCP Server (ecom-mcp)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_ecom_mcp_search_customer():
    """Kiểm tra tìm kiếm hồ sơ khách hàng qua mã CUST_..."""
    result = await search_ecommerce_data("CUST_000001")
    assert isinstance(result, str)
    assert "HỒ SƠ KHÁCH HÀNG" in result
    assert "CUST_000001" in result
    assert "lượt xem" in result


@pytest.mark.anyio
async def test_ecom_mcp_search_trending():
    """Kiểm tra tìm kiếm sản phẩm bán chạy."""
    result = await search_ecommerce_data("Cho tôi xem sản phẩm bán chạy nhất")
    assert isinstance(result, str)
    assert "Top ngành hàng bán chạy" in result


@pytest.mark.anyio
async def test_ecom_mcp_search_policy():
    """Kiểm tra tìm kiếm chính sách đổi trả/bảo hành."""
    result = await search_ecommerce_data("Chính sách đổi trả hàng như thế nào?")
    assert isinstance(result, str)
    assert "Chính sách đổi trả" in result
    assert "30 ngày" in result


def test_ecom_mcp_health_check():
    """Kiểm tra Healthcheck Probe cho ecom-mcp."""
    raw = ecom_health_check()
    data = json.loads(raw) if isinstance(raw, str) else raw
    assert data["status"] == "healthy"
    assert data["service"] == "ecom-mcp"


# ------------------------------------------------------------------------------
# 2. Kiểm thử Drift Detection FastMCP Server (drift-mcp)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_drift_mcp_check_drift():
    """Kiểm tra tính toán KS-test & PSI cho drift detection."""
    result = await check_data_drift("f_stream_views_30m")
    assert isinstance(result, str)
    assert "BÁO CÁO KIỂM TRA DRIFT" in result
    assert "f_stream_views_30m" in result
    assert "KS-statistic:" in result
    assert "PSI:" in result


def test_drift_mcp_health_check():
    """Kiểm tra Healthcheck Probe cho drift-mcp."""
    data = drift_health_check()
    assert isinstance(data, dict)
    assert data["status"] == "healthy"
    assert data["service"] == "drift-mcp"
