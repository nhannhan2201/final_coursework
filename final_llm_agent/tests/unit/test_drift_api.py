"""
==============================================================================
UNIT TESTS: Drift Detection REST API (apps/drift_api.py)
------------------------------------------------------------------------------
Sử dụng pytest và httpx.AsyncClient fixtures để kiểm thử các endpoints
tính toán KS-test và PSI score.
==============================================================================
"""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.drift_api import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_drift_health_check():
    """Test /health endpoint của Drift Detection API."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Real-Time Data Drift Detection API"

@pytest.mark.anyio
async def test_analyze_data_drift_default():
    """Test POST /api/v1/drift/analyze với payload mặc định."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/drift/analyze", json={})
    
    assert response.status_code == 200
    data = response.json()
    assert "overall_status" in data
    assert "drifted_features_count" in data
    assert len(data["metrics"]) == 3
    assert data["metrics"][0]["feature_name"] == "f_stream_views_30m"

@pytest.mark.anyio
async def test_analyze_data_drift_custom_features():
    """Test POST /api/v1/drift/analyze với danh sách features tùy chỉnh."""
    payload = {
        "features": ["f_stream_views_30m", "f_stream_add_to_cart_30m"],
        "sample_size": 2000
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/drift/analyze", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["metrics"]) == 2
    assert data["metrics"][0]["feature_name"] == "f_stream_views_30m"
    assert data["metrics"][1]["feature_name"] == "f_stream_add_to_cart_30m"
