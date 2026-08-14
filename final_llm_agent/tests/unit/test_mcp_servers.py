"""
==============================================================================
UNIT TESTS: MCP Servers (ecom-mcp & drift-mcp)
------------------------------------------------------------------------------
Sử dụng pytest và unittest.mock httpx để test các MCP tool handlers.
==============================================================================
"""

import os
import sys
import importlib.util
import pytest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Dynamic import for ecom-mcp/server.py
ecom_spec = importlib.util.spec_from_file_location("ecom_server", os.path.join(PROJECT_ROOT, "ecom-mcp", "server.py"))
ecom_server = importlib.util.module_from_spec(ecom_spec)
ecom_spec.loader.exec_module(ecom_server)

# Dynamic import for drift-mcp/server.py
drift_spec = importlib.util.spec_from_file_location("drift_server", os.path.join(PROJECT_ROOT, "drift-mcp", "server.py"))
drift_server = importlib.util.module_from_spec(drift_spec)
drift_spec.loader.exec_module(drift_server)

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
@patch("httpx.AsyncClient.get")
async def test_get_customer_shopping_context_success(mock_get):
    """Test get_customer_shopping_context tool trả về formatted profile."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "full_name": "Nguyễn Văn B",
        "city": "Đà Nẵng",
        "f_customer_total_orders_90d": 8,
        "f_customer_avg_order_value_90d": 200.0,
        "f_customer_distinct_categories_90d": 3,
        "views_last_30m": 15,
        "cart_add_last_30m": 3,
        "latest_viewed_category": "Thời trang",
        "data_source": "Redis + Delta Lake"
    }
    mock_get.return_value = mock_resp

    result = await ecom_server.get_customer_shopping_context("CUST_000002")
    assert "HỒ SƠ KHÁCH HÀNG: Nguyễn Văn B" in result
    assert "Đà Nẵng" in result
    assert "15" in result

@pytest.mark.anyio
@patch("httpx.AsyncClient.get")
async def test_get_trending_products_analytics_success(mock_get):
    """Test get_trending_products_analytics tool trả về top analytics report."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "top_categories": [
            {"category": "Đồ điện tử", "brand": "Samsung", "total_units_sold": 100, "total_revenue": 50000.0}
        ],
        "analysis_period": "Historical Gold Layer"
    }
    mock_get.return_value = mock_resp

    result = await ecom_server.get_trending_products_analytics()
    assert "PHÂN TÍCH XU HƯỚNG SẢN PHẨM BÁN CHẠY" in result
    assert "Đồ điện tử (Samsung)" in result

@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
async def test_detect_feature_drift_success(mock_post):
    """Test detect_feature_drift tool trả về drift analysis report."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "overall_status": "STABLE",
        "drifted_features_count": 0,
        "metrics": [
            {
                "feature_name": "f_stream_views_30m",
                "ks_statistic": 0.02,
                "p_value": 0.5,
                "psi_score": 0.01,
                "drift_status": "NO_DRIFT"
            }
        ],
        "baseline_dataset": "Gold Layer",
        "current_stream": "Redis Stream",
        "analyzed_at": "2026-08-11T12:00:00Z"
    }
    mock_post.return_value = mock_resp

    result = await drift_server.detect_feature_drift(["f_stream_views_30m"], 1000)
    assert "BÁO CÁO GIÁM SÁT DRIFT DỮ LIỆU THỜI GIAN THỰC" in result
    assert "STABLE" in result
    assert "Feature 'f_stream_views_30m'" in result
