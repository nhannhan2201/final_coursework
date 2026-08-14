# 📐 Schema Design & Data Modeling Documentation

## 1. Naming Conventions (Quy Ước Đặt Tên Bảng)
Hệ thống tuân thủ chặt chẽ quy ước đặt tên bảng theo từng tầng kiến trúc Medallion:

- **Bronze & Silver Layer:** 
  - Bronze (Raw Ingestion): Tiền tố `raw_` (ví dụ: `raw_products`, `raw_customers`, `raw_orders`, `raw_order_items`, `raw_payment_attempts`).
  - Silver (Clean & Staging): Tiền tố `stg_` (ví dụ: `stg_products`, `stg_customers`, `stg_orders`, `stg_order_items`, `stg_payment_attempts`).

- **Gold Layer:**
  - Bảng Chiều (Dimension Tables): Tiền tố `dim_` (ví dụ: `dim_customer`, `dim_product`, `dim_date`, `dim_payment_method`, `dim_order_status`).
  - Bảng Sự Kiện (Fact Tables): Tiền tố `fact_` (ví dụ: `fact_order`, `fact_order_item`, `fact_payment_attempt`).
  - Bảng Phẳng Rộng (One Big Table): Tiền tố `obt_` (ví dụ: `obt_order_performance`).
  - Bảng Kho Đặc Trưng (Feature Store): Tiền tố `feat_` (ví dụ: `feat_customer_90d`, `feat_stream_60m`, `feat_customer_unified`).

---

## 2. Chuẩn SCD Type 2 Cho Bảng Dimension (`dim_customer` & `dim_product`)

### 2.1. Cấu Trúc Cột SCD Type 2:
Mỗi bản ghi chiều biến đổi theo thời gian được quản lý bằng 3 cột chuẩn:
- `valid_from_ts` (Timestamp): Mốc thời gian bắt đầu có hiệu lực (Mặc định `1970-01-01 00:00:00` cho phiên bản đầu tiên để đảm bảo tính khớp điểm lịch sử).
- `valid_to_ts` (Timestamp): Mốc thời gian hết hiệu lực (`9999-12-31 23:59:59` nếu đang active).
- `is_current` (Boolean): Cờ đánh dấu bản ghi đang có hiệu lực hiện tại (`True`/`False`).

### 2.2. Cơ Chế Cập Nhật MERGE INTO (PySpark Delta Lake):
Khi thông tin phân khúc `segment` hoặc `country` của khách hàng thay đổi, Spark thực hiện lệnh `MERGE INTO`:
1. Bản ghi hiện tại bị đóng hiệu lực: `UPDATE SET is_current = false, valid_to_ts = current_timestamp()`.
2. Bản ghi mới được chèn vào: `INSERT VALUES (uuid(), customer_id, ..., valid_from_ts = current_timestamp(), valid_to_ts = '9999-12-31 23:59:59', is_current = true)`.

---

## 3. Point-in-Time Join (Ghép Nối Chuẩn Điểm Thời Gian Lịch Sử)

Khi tạo các bảng Fact (`fact_order_item`, `obt_order_performance`), đơn hàng trong quá khứ được ghép với bản ghi Dimension tương ứng theo điều kiện thời gian:

```sql
SELECT 
    orders.order_id,
    orders.order_ts,
    cust.customer_key,
    cust.segment
FROM stg_orders orders
JOIN dim_customer cust 
  ON orders.customer_id = cust.customer_id
 AND orders.order_ts >= cust.valid_from_ts
 AND orders.order_ts <= cust.valid_to_ts
```
Điều này đảm bảo báo cáo lịch sử tài chính không bị sai lệch khi thông tin khách hàng hoặc giá sản phẩm bị thay đổi theo thời gian.
