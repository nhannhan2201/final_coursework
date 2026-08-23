"""
==============================================================================
MÔ TẢ FILE: ecom-mcp/server.py
------------------------------------------------------------------------------
FastMCP Server cho E-Commerce Feature Store.

Expose 2 MCP Tools theo chuẩn Model Context Protocol (MCP):
  1. get_customer_shopping_context  — Truy xuất hồ sơ mua sắm cá nhân hóa
  2. get_trending_products_analytics — Phân tích top sản phẩm bán chạy

Server này gọi HTTP tới Feature Store Web API backend (apps/feature_api.py)
để lấy dữ liệu thực từ Redis (Online) và Trino/Delta Lake (Offline).
==============================================================================
"""

import os
import httpx
from fastmcp import FastMCP

# Feature Store Web API backend URL
FEATURE_API_URL = os.getenv("FEATURE_API_URL", "http://feature-api-service:8000")

# Khởi tạo FastMCP Server
mcp = FastMCP("E-Commerce Feature Store MCP Server")


@mcp.tool
async def get_customer_shopping_context(customer_id: str) -> str:
    """
    Truy xuất hồ sơ mua sắm cá nhân hóa của khách hàng từ Feature Store.

    Kết hợp dữ liệu Offline (Batch 90 ngày từ Delta Lake/Trino)
    và Online (Streaming 30 phút từ Redis) để tạo ngữ cảnh RAG đầy đủ.

    Args:
        customer_id: Mã khách hàng (VD: CUST_000001)

    Returns:
        Chuỗi mô tả hồ sơ mua sắm đầy đủ của khách hàng.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{FEATURE_API_URL}/api/v1/features/customer/{customer_id}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return (
                    f"=== 🛍️ HỒ SƠ KHÁCH HÀNG: {data.get('full_name', customer_id)} ===\n"
                    f"📍 Thành phố: {data.get('city', 'N/A')}\n"
                    f"📊 Tổng đơn hàng 90 ngày: {data.get('f_customer_total_orders_90d', 0)}\n"
                    f"💰 Giá trị đơn trung bình: {data.get('f_customer_avg_order_value_90d', 0)} VNĐ\n"
                    f"🏷️ Số ngành hàng mua sắm: {data.get('f_customer_distinct_categories_90d', 0)}\n"
                    f"⚡ Lượt xem 30 phút qua: {data.get('views_last_30m', 0)}\n"
                    f"🛒 Thêm giỏ hàng 30 phút qua: {data.get('cart_add_last_30m', 0)}\n"
                    f"📂 Ngành hàng đang xem: {data.get('latest_viewed_category', 'N/A')}\n"
                    f"🔗 Nguồn dữ liệu: {data.get('data_source', 'Redis + Delta Lake')}"
                )
            return f"Lỗi: Feature API trả về status {resp.status_code}"
    except Exception as e:
        return f"Lỗi kết nối Feature Store API tại {FEATURE_API_URL}: {e}"


@mcp.tool
async def get_trending_products_analytics() -> str:
    """
    Phân tích top sản phẩm và ngành hàng bán chạy nhất trên sàn E-Commerce.

    Truy vấn dữ liệu từ Gold Layer (Delta Lake) để tổng hợp xu hướng
    doanh số theo ngành hàng và thương hiệu.

    Returns:
        Báo cáo phân tích xu hướng sản phẩm bán chạy.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{FEATURE_API_URL}/api/v1/features/analytics/trending"
            )
            if resp.status_code == 200:
                data = resp.json()
                lines = ["=== 🔥 PHÂN TÍCH XU HƯỚNG SẢN PHẨM BÁN CHẠY ==="]
                for idx, item in enumerate(data.get("top_categories", []), 1):
                    lines.append(
                        f"{idx}. {item['category']} ({item['brand']}): "
                        f"{item['total_units_sold']} sản phẩm — "
                        f"Doanh thu: {item['total_revenue']:,.0f} VNĐ"
                    )
                lines.append(f"\n📅 Kỳ phân tích: {data.get('analysis_period', 'N/A')}")
                return "\n".join(lines)
            return f"Lỗi: Feature API trả về status {resp.status_code}"
    except Exception as e:
        return f"Lỗi kết nối Feature Store API tại {FEATURE_API_URL}: {e}"


if __name__ == "__main__":
    mcp.run(transport="http")
