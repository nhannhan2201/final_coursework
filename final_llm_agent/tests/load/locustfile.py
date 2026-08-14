"""
==============================================================================
LOCUST LOAD TESTING SCRIPT: Feature Store REST API SLA
------------------------------------------------------------------------------
Giả lập tải hệ thống (Throughput req/s & Latency RTT) khi LLM Agent
kéo đặc trưng và truy vấn tri thức RAG Chunks.
==============================================================================
"""

import random
from locust import HttpUser, task, between

class FeatureStoreAPIUser(HttpUser):
    """Giả lập 50-100 LLM Agents / Web Users truy vấn Feature Store Web API cùng lúc."""
    
    wait_time = between(0.1, 0.5)  # Trễ ngẫu nhiên giữa các request (100ms - 500ms)

    @task(4)
    def test_get_customer_features(self):
        """Task 1 (Trọng số 4): Kéo đặc trưng khách hàng hợp nhất (Online + Offline)."""
        cust_id = f"CUST_{random.randint(1, 1000):06d}"
        self.client.get(
            f"/api/v1/features/customer/{cust_id}",
            name="/api/v1/features/customer/[id]"
        )

    @task(2)
    def test_search_rag_chunks(self):
        """Task 2 (Trọng số 2): Tìm kiếm RAG Text Chunks theo từ khóa."""
        keywords = ["bảo hành", "đổi trả", "giao hàng", "thanh toán", "khuyến mãi"]
        kw = random.choice(keywords)
        self.client.get(
            f"/api/v1/chunks/search/query?q={kw}",
            name="/api/v1/chunks/search/query"
        )

    @task(1)
    def test_get_trending_analytics(self):
        """Task 3 (Trọng số 1): Kéo phân tích xu hướng sản phẩm bán chạy từ Delta Lake."""
        self.client.get(
            "/api/v1/features/analytics/trending",
            name="/api/v1/features/analytics/trending"
        )

    @task(1)
    def test_health_check(self):
        """Task 4 (Trọng số 1): Health check readiness probe."""
        self.client.get("/health", name="/health")
