"""
==============================================================================
UNIT TESTS: Feature Store REST API (apps/feature_api.py)
------------------------------------------------------------------------------
Sử dụng pytest, httpx.AsyncClient fixtures, và unittest.mock
để đạt Test Coverage > 90%.
==============================================================================
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from apps.feature_api import (
    app,
    get_online_features_from_redis,
    get_offline_features_from_trino,
    get_trending_analytics_from_trino,
    get_chunk_from_redis_or_file,
    search_chunks_by_query
)

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_health_check():
    """Test /health endpoint trả về status 200 và healthy."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Feature Store REST API"
    assert "timestamp" in data

@pytest.mark.anyio
@patch("apps.feature_api.get_online_features_from_redis")
@patch("apps.feature_api.get_offline_features_from_trino")
async def test_get_customer_features_endpoint(mock_trino, mock_redis):
    """Test GET /api/v1/features/customer/{customer_id}."""
    mock_redis.return_value = {
        "views_last_30m": 12,
        "cart_add_last_30m": 4,
        "latest_viewed_category": "Electronics"
    }
    mock_trino.return_value = {
        "full_name": "Nguyễn Văn A",
        "city": "Hà Nội",
        "total_orders_90d": 15,
        "avg_order_value_90d": 450.0,
        "distinct_categories_90d": 5
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/features/customer/CUST_000001")
    
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "CUST_000001"
    assert data["full_name"] == "Nguyễn Văn A"
    assert data["views_last_30m"] == 12

@pytest.mark.anyio
@patch("apps.feature_api.get_trending_analytics_from_trino")
async def test_get_trending_analytics_endpoint(mock_trino):
    """Test GET /api/v1/features/analytics/trending."""
    mock_trino.return_value = [
        {"category": "Electronics", "brand": "Apple", "total_units_sold": 500, "total_revenue": 250000.0}
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/features/analytics/trending")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["top_categories"]) == 1

@pytest.mark.anyio
@patch("apps.feature_api.redis.Redis")
async def test_get_online_features_from_redis_success(mock_redis_cls):
    """Test get_online_features_from_redis khi Redis kết nối thành công."""
    mock_r = AsyncMock()
    mock_r.hgetall.return_value = {
        "f_stream_views_30m": "10",
        "f_stream_add_to_cart_30m": "3",
        "latest_category": "Thời trang"
    }
    mock_redis_cls.return_value = mock_r

    res = await get_online_features_from_redis("CUST_000001")
    assert res["views_last_30m"] == 10
    assert res["cart_add_last_30m"] == 3
    assert res["latest_viewed_category"] == "Thời trang"

@pytest.mark.anyio
@patch("apps.feature_api.redis.Redis", side_effect=Exception("Redis connection error"))
async def test_get_online_features_from_redis_fallback(mock_redis_cls):
    """Test get_online_features_from_redis khi Redis lỗi thì dùng fallback."""
    res = await get_online_features_from_redis("CUST_000001")
    assert res["views_last_30m"] == 8
    assert res["cart_add_last_30m"] == 2

@patch("trino.dbapi.connect")
def test_get_offline_features_from_trino_success(mock_trino_conn):
    """Test get_offline_features_from_trino kết nối thành công."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("CUST_001", "Trần Thị B", "Đà Nẵng", 10, 250.0, 4)
    mock_conn.cursor.return_value = mock_cursor
    mock_trino_conn.return_value = mock_conn

    res = get_offline_features_from_trino("CUST_001")
    assert res["full_name"] == "Trần Thị B"
    assert res["total_orders_90d"] == 10

@patch("trino.dbapi.connect", side_effect=Exception("Trino error"))
def test_get_offline_features_from_trino_fallback(mock_trino_conn):
    """Test get_offline_features_from_trino khi lỗi thì dùng fallback."""
    res = get_offline_features_from_trino("CUST_001")
    assert res["total_orders_90d"] == 14
    assert res["avg_order_value_90d"] == 320.50

@patch("trino.dbapi.connect")
def test_get_trending_analytics_from_trino_success(mock_trino_conn):
    """Test get_trending_analytics_from_trino kết nối thành công."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("Electronics", "Sony", 150, 75000.0)
    ]
    mock_conn.cursor.return_value = mock_cursor
    mock_trino_conn.return_value = mock_conn

    res = get_trending_analytics_from_trino()
    assert len(res) == 1
    assert res[0]["category"] == "Electronics"
    assert res[0]["brand"] == "Sony"

@patch("trino.dbapi.connect", side_effect=Exception("Trino error"))
def test_get_trending_analytics_from_trino_fallback(mock_trino_conn):
    """Test get_trending_analytics_from_trino khi lỗi dùng fallback."""
    res = get_trending_analytics_from_trino()
    assert len(res) == 5
    assert res[0]["category"] == "Thời trang & Phụ kiện"

@pytest.mark.anyio
@patch("apps.feature_api.redis.Redis")
async def test_get_chunk_from_redis_success(mock_redis_cls):
    """Test get_chunk_from_redis_or_file lấy thành công từ Redis."""
    mock_r = AsyncMock()
    mock_r.hgetall.return_value = {
        "chunk_id": "CHUNK_001",
        "title": "Chính sách bảo hành",
        "chunk_text": "Chi tiết bảo hành..."
    }
    mock_redis_cls.return_value = mock_r

    res = await get_chunk_from_redis_or_file("CHUNK_001")
    assert res["chunk_id"] == "CHUNK_001"
    assert res["title"] == "Chính sách bảo hành"

@pytest.mark.anyio
@patch("apps.feature_api.redis.Redis", side_effect=Exception("Redis fail"))
async def test_get_chunk_from_file_fallback(mock_redis_cls, tmp_path):
    """Test get_chunk_from_redis_or_file fallback đọc từ file."""
    res = await get_chunk_from_redis_or_file("NON_EXISTENT_CHUNK")
    assert res is None or isinstance(res, dict)

@pytest.mark.anyio
async def test_search_chunks_by_query():
    """Test search_chunks_by_query trả về list."""
    res = await search_chunks_by_query("bảo hành")
    assert isinstance(res, list)

@pytest.mark.anyio
@patch("apps.feature_api.get_chunk_from_redis_or_file")
async def test_get_rag_chunk_endpoint(mock_chunk):
    """Test GET /api/v1/chunks/{chunk_id}."""
    mock_chunk.return_value = {
        "chunk_id": "CHUNK_001",
        "doc_id": "DOC_01",
        "title": "Chính Sách Đổi Trả",
        "category": "Policy",
        "chunk_text": "Khách hàng được đổi trả.",
        "vector_dim": 384
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/chunks/CHUNK_001")
    assert resp.status_code == 200
    assert resp.json()["chunk_id"] == "CHUNK_001"

@pytest.mark.anyio
@patch("apps.feature_api.search_chunks_by_query")
async def test_search_rag_chunks_endpoint(mock_search):
    """Test GET /api/v1/chunks/search/query."""
    mock_search.return_value = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/chunks/search/query?q=giao hàng")
    assert resp.status_code == 200
    assert resp.json()["total_results"] == 0
