"""
==============================================================================
MÔ TẢ FILE: drift-mcp/server.py
------------------------------------------------------------------------------
FastMCP Server cho Real-time Data Drift Detection.

Expose MCP Tool theo chuẩn Model Context Protocol (MCP):
  1. detect_feature_drift — Phân tích trôi lệch dữ liệu thời gian thực
     giữa Redis Stream và Baseline Delta Lake (KS-test & PSI score).

Server này gọi HTTP tới Drift Detection Web API backend (apps/drift_api.py)
để thực hiện tính toán Kolmogorov-Smirnov Test và Population Stability Index.
==============================================================================
"""

import os
from typing import Optional
import httpx
from fastmcp import FastMCP

# Drift Detection Web API backend URL
DRIFT_API_URL = os.getenv("DRIFT_API_URL", "http://drift-api-service:8003")

# Khởi tạo FastMCP Server
mcp = FastMCP("Drift Detection MCP Server")


@mcp.tool
async def detect_feature_drift(
    features: Optional[list[str]] = None,
    sample_size: int = 1000
) -> str:
    """
    Phân tích trôi lệch dữ liệu thời gian thực (Data Drift Detection).

    So sánh phân phối dữ liệu hiện tại từ Redis Streaming với Baseline
    từ Delta Lake Gold Layer bằng thuật toán Kolmogorov-Smirnov Test
    và Population Stability Index (PSI).

    Args:
        features: Danh sách tên đặc trưng cần kiểm tra. Mặc định kiểm tra
                  3 features chính: f_stream_views_30m, f_stream_add_to_cart_30m,
                  f_customer_avg_order_value_90d.
        sample_size: Kích thước mẫu dữ liệu để phân tích (mặc định 1000).

    Returns:
        Báo cáo chi tiết trạng thái drift của từng đặc trưng.
    """
    if features is None:
        features = [
            "f_stream_views_30m",
            "f_stream_add_to_cart_30m",
            "f_customer_avg_order_value_90d"
        ]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{DRIFT_API_URL}/api/v1/drift/analyze",
                json={"features": features, "sample_size": sample_size}
            )
            if resp.status_code == 200:
                data = resp.json()
                overall = data.get("overall_status", "UNKNOWN")
                drift_count = data.get("drifted_features_count", 0)
                metrics = data.get("metrics", [])

                lines = [
                    "=== 📉 BÁO CÁO GIÁM SÁT DRIFT DỮ LIỆU THỜI GIAN THỰC ===",
                    f"🔍 Trạng thái tổng thể: {overall}",
                    f"📊 Số lượng đặc trưng trôi lệch: {drift_count}/{len(features)}",
                    f"📏 Kích thước mẫu: {sample_size}",
                    f"📁 Baseline: {data.get('baseline_dataset', 'Delta Lake Gold Layer')}",
                    f"📡 Current: {data.get('current_stream', 'Redis Real-Time Stream')}",
                    ""
                ]
                for m in metrics:
                    status_icon = "🔴" if m["drift_status"] == "DRIFT_DETECTED" else "🟢"
                    lines.append(
                        f"  {status_icon} Feature '{m['feature_name']}':\n"
                        f"     KS-statistic: {m['ks_statistic']} | "
                        f"p-value: {m['p_value']} | "
                        f"PSI: {m['psi_score']} → {m['drift_status']}"
                    )

                lines.append(f"\n⏰ Analyzed at: {data.get('analyzed_at', 'N/A')}")
                return "\n".join(lines)
            return f"Lỗi: Drift API trả về status {resp.status_code}"
    except Exception as e:
        return f"Lỗi kết nối Drift Detection API tại {DRIFT_API_URL}: {e}"


if __name__ == "__main__":
    mcp.run(transport="http")
