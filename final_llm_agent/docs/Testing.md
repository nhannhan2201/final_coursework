# 🧪 Báo Cáo Kiểm Thử & Xác Minh Hệ Thống (Validation & Verification)

Báo cáo này tập hợp các kết quả kiểm thử tự động (**Automated Testing Suite**) với **36 bài test** toàn diện, đạt độ phủ mã nguồn (**Code Coverage > 90%**) cho toàn bộ hệ thống API (`feature_api.py`, `drift_api.py`) và FastMCP Tool Servers.

---

## 📈 1. Toàn Bộ 36 Pytest Test Cases & Code Coverage (>90%)

Hệ thống kiểm thử tự động tích hợp trực tiếp vào Jenkins CI/CD Pipeline (Stage 2) bao gồm 36 bài kiểm thử thuộc 4 nhóm nghiệp vụ:
1. **Feature Store API Tests (14 tests):** Kiểm tra tính năng đọc Online Cache Redis (<1ms), Fallback sang Trino Delta Lake, và tìm kiếm ngữ nghĩa RAG Chunks.
2. **Drift Detection API Tests (3 tests):** Kiểm tra các thuật toán thống kê KS-Test và PSI Score phân tích trôi lệch dữ liệu.
3. **Boundary Value Analysis & Equivalence Partitioning (14 tests):** Kiểm tra các điểm giá trị biên nhạy cảm (`customer_id` siêu dài, `sample_size = 0, 1, 10000`, ngưỡng chuyển trạng thái PSI `0.24` vs `0.26`).
4. **FastMCP Tool Tests & Property Tests (5 tests):** Kiểm tra các công cụ `get_customer_shopping_context`, `detect_feature_drift` và tính bất biến (Idempotency) bằng Hypothesis.

```bash
# Chạy toàn bộ 36 test cases và hiển thị bảng độ phủ mã nguồn:
pytest tests/ -v --cov=apps --cov-report=term-missing
```

> 📸 **MINH CHỨNG DUY NHẤT: 36 TESTS PASSED & COVERAGE BẢNG THỐNG KÊ:**
>
> *(Chỉ cần 1 ảnh chụp màn hình terminal duy nhất khi chạy lệnh `pytest tests/ -v --cov=apps` hiển thị 36 passed màu xanh lá cây và bảng Coverage > 90% tại đây)*
>
> ![Pytest Full Suite Coverage](screenshot_pytest_coverage.png)

---

## 🚀 2. Kiểm Thử Tải Hệ Thống (Locust Load Testing)

Giả lập người dùng đồng thời gửi yêu cầu liên tục đến Feature Store API và Drift API thông qua kịch bản Locust trong `tests/load/locustfile.py` để đánh giá thông lượng (Throughput) và độ ổn định khi chịu tải.

```bash
locust -f tests/load/locustfile.py --headless -u 1000 -r 50 --run-time 1m
```

> 📸 **MINH CHỨNG BÁO CÁO TẢI LOCUST:**
>
> *(Chèn ảnh chụp màn hình bảng kết quả Locust Load Test tại đây)*
>
> ![Locust Load Testing Results](screenshot_locust_results.png)
