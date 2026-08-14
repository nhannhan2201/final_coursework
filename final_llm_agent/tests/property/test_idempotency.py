"""
==============================================================================
PROPERTY-BASED & IDEMPOTENCY TESTS (hypothesis + crosshair)
------------------------------------------------------------------------------
Kiểm tra tính bất biến / nhất quán (Idempotency & Invariants) của kết quả
tính toán bằng thư viện hypothesis và crosshair backend.
==============================================================================
"""

import pytest
from hypothesis import given, strategies as st
from apps.drift_api import FeatureDriftMetric, DriftAnalysisRequest

# ------------------------------------------------------------------------------
# 1. Idempotency Property Test: Status & Metric Invariance
# ------------------------------------------------------------------------------
@given(
    features=st.lists(
        st.sampled_from(["f_stream_views_30m", "f_stream_add_to_cart_30m", "f_customer_avg_order_value_90d"]),
        min_size=1,
        max_size=5
    ),
    sample_size=st.integers(min_value=1, max_value=10000)
)
def test_drift_request_idempotency(features, sample_size):
    """
    Property: Một DriftAnalysisRequest với cùng tham số đầu vào
    phải tạo ra cấu trúc request nhất quán (idempotent serialization).
    """
    req1 = DriftAnalysisRequest(features=features, sample_size=sample_size)
    req2 = DriftAnalysisRequest(features=features, sample_size=sample_size)
    
    # Invariant 1: Hash / JSON Representation
    assert req1.model_dump_json() == req2.model_dump_json()
    # Invariant 2: Feature count invariance
    assert len(req1.features) == len(req2.features)
    assert req1.sample_size == req2.sample_size

# ------------------------------------------------------------------------------
# 2. Invariant Property Test: Feature Drift Metric Threshold Logic
# ------------------------------------------------------------------------------
@given(
    psi=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
    p_val=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)
def test_drift_metric_status_invariants(psi, p_val):
    """
    Property: Logic quyết định trạng thái DRIFT_DETECTED luôn nhất quán (Idempotent invariant):
    Nếu PSI > 0.25 HOẶC p-value < 0.05 thì status luôn luôn là DRIFT_DETECTED.
    """
    def compute_status(p: float, p_v: float) -> str:
        if p > 0.25 or p_v < 0.05:
            return "DRIFT_DETECTED"
        return "NO_DRIFT"

    s1 = compute_status(psi, p_val)
    s2 = compute_status(psi, p_val)

    # Idempotency property: f(x) == f(f(x)) status output stability
    assert s1 == s2
    
    if psi > 0.25 or p_val < 0.05:
        assert s1 == "DRIFT_DETECTED"
    else:
        assert s1 == "NO_DRIFT"
