# 📊 Data Generation & Drift Simulation Report

Báo cáo chi tiết quá trình sinh dữ liệu giả lập, cấu hình mô phỏng hiện tượng trôi lệch phân phối dữ liệu (Data Drift) và cấu trúc bảng nhãn (label table) phục vụ huấn luyện mô hình.

---

## ⚙️ 1. Cấu Hình Sinh Dữ Liệu (Generator Configuration)
Mã nguồn sinh dữ liệu sử dụng tệp cấu hình yaml để định nghĩa phân phối xác suất của hành vi mua sắm, tần suất giao dịch và tỷ lệ lỗi thanh toán.

> 📸 **[CAPTURE MINH CHỨNG - DỮ LIỆU CẤU HÌNH GENERATOR]**
> *Hãy chụp màn hình tệp yaml cấu hình generator (ví dụ: `generator_config.yaml`) định nghĩa các tham số phân phối xác suất.*

---

## 📈 2. Giả Lập Trôi Lệch Dữ Liệu (Simulate Data Drift)
Mô phỏng sự thay đổi hành vi người dùng bằng cách áp dụng các hàm thay đổi phân phối (nhân hệ số drift) đối với các đặc trưng như `purchase_frequency` hay `average_order_value`.

> 📸 **MINH CHỨNG GIẢ LẬP VÀ PHÂN TÍCH DATA DRIFT (KS-TEST & PSI SCORE):**
```json
{
  "overall_status": "STABLE",
  "drifted_features_count": 0,
  "metrics": [
    {
      "feature_name": "f_stream_views_30m",
      "p_value": 0.7293,
      "ks_statistic": 0.0519,
      "psi_score": 0.0394,
      "drift_status": "NO_DRIFT"
    },
    {
      "feature_name": "f_customer_avg_order_value_90d",
      "p_value": 0.3359,
      "ks_statistic": 0.0366,
      "psi_score": 0.0077,
      "drift_status": "NO_DRIFT"
    }
  ],
  "baseline_dataset": "Delta Lake Gold Layer (feat_customer_90d)",
  "current_stream": "Redis Real-Time Stream (feat_stream_60m)"
}
```

---

## 🔗 3. Bảng Nhãn & Ghép Nhãn (Label Table & Merge ID & Label)
Để phục vụ bài toán học máy, một bảng nhãn gồm ít nhất 2 cột: `id` (hoặc `customer_id`) và `label` (nhãn phân lớp mua sắm/rời bỏ) được khởi tạo và ghép nối (merge/join) với các đặc trưng từ Feature Store.

> 📸 **[CAPTURE MINH CHỨNG - BẢNG SAU KHI MERGE ID VÀ LABEL]**
> *Hãy chụp màn hình kết quả truy vấn SQL hiển thị bảng đặc trưng hợp nhất sau khi thực hiện JOIN bảng nhãn với các đặc trưng của khách hàng.*
