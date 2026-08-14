# 🧩 Software Design Patterns in Agentic Infrastructure

Báo cáo chi tiết về việc ứng dụng các mẫu thiết kế phần mềm (Design Patterns) tiêu biểu trong kiến trúc Agentic AI và MLOps nhằm tăng tính module hóa, dễ dàng mở rộng và bảo trì mã nguồn.

---

## 🎨 1. Strategy Pattern (Mẫu Chiến Lược)
- **Vị trí áp dụng:** Bộ mã nguồn phân tích Data Drift (`drift_api.py` hoặc `drift-mcp/server.py`).
- **Chi tiết:** Cho phép hoán đổi linh hoạt các thuật toán tính toán độ lệch phân phối dữ liệu (như *Kolmogorov-Smirnov test - KS-test*, hoặc *Population Stability Index - PSI*) tùy theo kiểu dữ liệu (Categorical vs Numerical).

> 📸 **[CAPTURE MINH CHỨNG - CODE STRATEGY PATTERN]**
> *Hãy chụp màn hình đoạn code định nghĩa Interface/Abstract Class chiến lược phân tích drift và các lớp triển khai cụ thể.*

---

## 🔌 2. Adapter Pattern (Mẫu Thích Ứng)
- **Vị trí áp dụng:** Bộ kết nối dữ liệu Feature Store (`feature_api.py`).
- **Chi tiết:** Đóng vai trò làm cổng chuyển tiếp tương thích giữa các nguồn lưu trữ đặc trưng khác nhau (Redis Online Store cho thời gian thực và Trino/Delta Lakehouse cho ngoại tuyến offline) sang định dạng dữ liệu chuẩn Pydantic mà các Agents có thể tiêu thụ trực tiếp.

> 📸 **[CAPTURE MINH CHỨNG - CODE ADAPTER PATTERN]**
> *Hãy chụp màn hình đoạn code của lớp Adapter/Wrapper thực hiện việc chuyển đổi cấu trúc dữ liệu thô từ database thành schema chuẩn.*
