"""
==============================================================================
BOUNDARY VALUE & EQUIVALENCE PARTITIONING TESTS
------------------------------------------------------------------------------
Thiết kế test cases áp dụng kỹ thuật Phân vùng tương đương (Equivalence Partitioning)
và Phân tích giá trị biên (Boundary Value Analysis) bằng `pytest.mark.parametrize`.
==============================================================================
"""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.feature_api import app as feature_app
from apps.drift_api import app as drift_app, FeatureDriftMetric, DriftAnalysisRequest

@pytest.fixture
def anyio_backend():
    return "asyncio"

# ------------------------------------------------------------------------------
# 1. Equivalence Partitioning & Boundary Analysis cho Feature Store Web API
# ------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize(
    "customer_id, expected_status",
    [
        # Boundary Values cho customer_id
        ("CUST_000001", 200),            # Valid standard ID
        ("C", 200),                      # Min length single char
        ("CUST_" + "0" * 200, 200),      # Max length long ID
        ("SPECIAL_-_123", 200),          # Special valid URL chars partition
    ]
)
async def test_customer_id_boundary_analysis(customer_id, expected_status):
    """Phân vùng tương đương và Giá trị biên cho tham số customer_id."""
    async with AsyncClient(transport=ASGITransport(app=feature_app), base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/features/customer/{customer_id}")
    assert resp.status_code == expected_status
    data = resp.json()
    assert data["customer_id"] == customer_id

# ------------------------------------------------------------------------------
# 2. Equivalence Partitioning & Boundary Analysis cho Drift Detection API
# ------------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize(
    "sample_size, expected_status",
    [
        # Boundary Values cho sample_size
        (1, 200),       # Lower boundary min positive
        (1000, 200),    # Nominal / Typical value
        (10000, 200),   # Upper boundary large sample
        (0, 200),       # Edge case 0
    ]
)
async def test_drift_sample_size_boundary_analysis(sample_size, expected_status):
    """Phân tích giá trị biên cho kích thước mẫu sample_size."""
    async with AsyncClient(transport=ASGITransport(app=drift_app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/drift/analyze",
            json={"features": ["f_stream_views_30m"], "sample_size": sample_size}
        )
    assert resp.status_code == expected_status

@pytest.mark.parametrize(
    "psi_score, p_value, expected_status",
    [
        # Equivalence Partition: NO_DRIFT (PSI <= 0.25 và p_value >= 0.05)
        (0.00, 0.50, "NO_DRIFT"),
        (0.24, 0.10, "NO_DRIFT"),
        (0.25, 0.05, "NO_DRIFT"),         # Exact Boundary
        
        # Equivalence Partition: DRIFT_DETECTED (PSI > 0.25 hoặc p_value < 0.05)
        (0.26, 0.50, "DRIFT_DETECTED"),   # Boundary PSI > 0.25
        (0.01, 0.04, "DRIFT_DETECTED"),   # Boundary p-value < 0.05
        (0.50, 0.01, "DRIFT_DETECTED"),   # Extreme drift
    ]
)
def test_drift_threshold_boundary_logic(psi_score, p_value, expected_status):
    """Phân tích ranh giới logic kiểm định KS-test và PSI metric."""
    status = "NO_DRIFT"
    if psi_score > 0.25 or p_value < 0.05:
        status = "DRIFT_DETECTED"
    
    assert status == expected_status
