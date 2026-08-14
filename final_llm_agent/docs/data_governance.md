# 🏛️ Data Governance & Pipeline Lineage (DataHub Integration)

Báo cáo chi tiết về việc xây dựng hệ thống quản trị dữ liệu (Data Governance) cho RAG data pipeline bằng cách tích hợp siêu dữ liệu (Metadata) và lược đồ quan hệ (Lineage) lên nền tảng **DataHub**.

---

## 🌪️ 1. Airflow RAG Ingestion Pipeline
Luồng công việc (DAG) tự động chạy định kỳ kéo dữ liệu từ file text thô, tiến hành cắt nhỏ (chunking), tạo vector embeddings và đẩy trực tiếp vào Feature Store thông qua Feast.

> 📸 **[CAPTURE MINH CHỨNG - AIRFLOW PIPELINE RUN SUCCESS]**
> *Hãy chụp màn hình giao diện Airflow DAG Graph View hiển thị toàn bộ các nhiệm vụ (tasks) trong luồng ingestion đều ở trạng thái thành công (màu xanh lá cây).*

---

## 🗺️ 2. DataHub Lineage Map
Cơ chế tự động thu thập metadata từ Spark/Airflow và đẩy về DataHub để vẽ sơ đồ nguồn gốc dữ liệu (Data Lineage).

> 📸 **[CAPTURE MINH CHỨNG - DATAHUB LINEAGE MAP]**
> *Hãy chụp màn hình giao diện DataHub thể hiện Lineage kết nối từ các tệp thô nguồn ➔ Gold Tables ➔ RAG Feature Store để reviewer thấy nguồn gốc dữ liệu.*

---

## 🧪 3. DataHub Assertions (Kiểm Định Chất Lượng Dữ Liệu)
Tích hợp các câu lệnh kiểm định (Assertions) tự động chạy để kiểm tra số lượng bản ghi, tính toàn vẹn và định dạng kiểu dữ liệu của các đặc trưng.

> 📸 **[CAPTURE MINH CHỨNG - DATAHUB ASSERTIONS RESULTS]**
> *Hãy chụp màn hình trang thông tin Assertions trên DataHub hiển thị trạng thái kiểm tra chất lượng dữ liệu vượt qua thành công (Passed).*
