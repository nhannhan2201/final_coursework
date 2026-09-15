# 🧩 Software Design Patterns & Architectural Decisions

Báo cáo chi tiết về việc ứng dụng các mẫu thiết kế phần mềm (**Design Patterns**) trong mã nguồn của hệ thống Multi-Agent AI & FastMCP Tool Servers.

---

## 🎨 1. Strategy Pattern (Mẫu Chiến Lược)

- **Vị trí áp dụng:** Bộ phân tích kiểm định độ lệch dữ liệu trong [agentic_ai/drift-mcp/server.py](file:///home/nhan/Projects/final_coursework/final_llm_agent/agentic_ai/drift-mcp/server.py).
- **Mục đích:** Cho phép hoán đổi linh hoạt giữa các thuật toán thống kê kiểm định mà không làm thay đổi luồng điều khiển của MCP Tool:
  - **`KSTestStrategy`:** Kiểm định phi tham số Kolmogorov-Smirnov 2 mẫu trên dữ liệu liên tục (`p-value < 0.05` biểu thị trôi lệch).
  - **`PSIStrategy`:** Chỉ số ổn định quần thể (Population Stability Index) chia bin tần suất (`PSI > 0.2` biểu thị phân phối có biến động đáng kể).

```python
from abc import ABC, abstractmethod
import numpy as np
from scipy import stats

class DriftDetectionStrategy(ABC):
    @abstractmethod
    def evaluate(self, baseline: np.ndarray, current: np.ndarray) -> dict:
        pass

class KSTestStrategy(DriftDetectionStrategy):
    def evaluate(self, baseline: np.ndarray, current: np.ndarray) -> dict:
        stat, p_val = stats.ks_2samp(baseline, current)
        return {"metric": "KS-Test", "statistic": float(stat), "p_value": float(p_val), "is_drift": p_val < 0.05}

class PSIStrategy(DriftDetectionStrategy):
    def evaluate(self, baseline: np.ndarray, current: np.ndarray) -> dict:
        psi_score = self._compute_psi(baseline, current)
        return {"metric": "PSI", "score": float(psi_score), "is_drift": psi_score > 0.2}
```

---

## 🔌 2. Adapter Pattern (Mẫu Thích Ứng)

- **Vị trí áp dụng:** Module tích hợp nguồn dữ liệu đa tầng trong [agentic_ai/ecom-mcp/server.py](file:///home/nhan/Projects/final_coursework/final_llm_agent/agentic_ai/ecom-mcp/server.py).
- **Mục đích:** Đóng vai trò adapter chuẩn hóa hai nguồn dữ liệu không đồng nhất:
  - Dữ liệu luồng trực tuyến từ **Redis Online Store** (Key-Value In-Memory, hash map `< 1ms`).
  - Dữ liệu lịch sử 90 ngày từ **Trino SQL Engine** (Relational SQL trên bảng Delta Lake Parquet).
  - Hợp nhất thành cấu trúc `CustomerShoppingProfile` thống nhất cho LLM tiêu thụ.

```python
class UnifiedFeatureStoreAdapter:
    def __init__(self, redis_client, trino_client):
        self.redis = redis_client
        self.trino = trino_client

    async def get_unified_profile(self, customer_id: str) -> dict:
        # Lấy đặc trưng trực tuyến thời gian thực
        stream_data = await self.redis.hgetall(f"feat_stream:{customer_id}")
        # Truy vấn lịch sử 90 ngày trên Delta Lake
        order_history = await self.trino.query_orders(customer_id)
        
        # Thích ứng và hợp nhất thành một hồ sơ thống nhất
        return {
            "customer_id": customer_id,
            "views_last_30m": int(stream_data.get("views_30m", 0)),
            "cart_additions_30m": int(stream_data.get("cart_additions_30m", 0)),
            "total_spent_90d": float(order_history.get("total_spent", 0.0)),
            "order_count_90d": int(order_history.get("order_count", 0))
        }
```

---

## 👑 3. Supervisor Pattern (Mẫu Điều Phối Giám Sát)

- **Vị trí áp dụng:** Bộ điều phối `coordinator-agent` kết nối với 2 Sub-Agents `ecom-agent` và `drift-agent`.
- **Mục đích:** Phân tách trách nhiệm chuyên biệt hóa (Separation of Concerns). `coordinator-agent` chỉ tập trung phân tích ý định và ủy quyền cho chuyên gia cấp dưới giải quyết, loại bỏ sự phức tạp khi nhồi nhét quá nhiều Tool vào một Agent duy nhất.
