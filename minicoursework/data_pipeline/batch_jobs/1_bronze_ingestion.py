import os
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

# ==============================================================================
# 1. CẤU HÌNH THƯ VIỆN KẾT NỐI (MINIO & DELTA LAKE)
# ==============================================================================
os.environ['PYSPARK_SUBMIT_ARGS'] = (
    '--packages io.delta:delta-core_2.12:2.4.0,'
    'org.apache.hadoop:hadoop-aws:3.3.4 '
    'pyspark-shell'
)

# Khởi tạo Spark Session kết nối với hạ tầng MinIO Docker
spark = SparkSession.builder \
    .appName("Ecom_Bronze_Ingestion") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.sql.parquet.outputTimestampType", "TIMESTAMP_MICROS") \
    .config("spark.sql.legacy.parquet.nanosAsLong", "true") \
    .getOrCreate()

# Giới hạn log để màn hình terminal sạch sẽ, dễ theo dõi lỗi nếu có
spark.sparkContext.setLogLevel("WARN")
print("\n🚀 [HỆ THỐNG] SPARK SESSION ĐS KHỞI TẠO THÀNH CÔNG!")


# ==============================================================================
# 2. HÀM TỰ ĐỘNG INGEST DATA SANG LỚP BRONZE (ĐÚNG SCHEMA CỦA THẦY)
# ==============================================================================
def ingest_to_bronze(source_folder, target_table_name):
    print(f"\n──────────────────────────────────────────────────")
    print(f"📦 Đang xử lý: {source_folder} ──> {target_table_name}")
    
    source_path = f"s3a://landing-zone/{source_folder}"
    target_path = f"s3a://datalake/bronze/{target_table_name}"
    
    try:
        # 2.1 Đọc dữ liệu Parquet thô ban đầu
        raw_df = spark.read.parquet(source_path)
        
        # 2.2 Đắp thêm cột metadata _ingested_at đóng dấu thời gian (Yêu cầu bắt buộc lớp Bronze)
        bronze_df = raw_df.withColumn("raw_id", F.expr("uuid()")) \
                          .withColumn("_ingested_at", F.current_timestamp())
        
        # 2.3 Ghi xuống datalake dưới định dạng Delta Lake (Lakehouse Storage)
        bronze_df.write \
            .format("delta") \
            .mode("append") \
            .save(target_path)
            
        print(f"  ✔️  THÀNH CÔNG: Đã tạo bảng Delta '{target_table_name}'")
        
    except Exception as e:
        print(f"  ❌  THẤT BẠI khi xử lý {source_folder}: {str(e)}")


# ==============================================================================
# 3. CHẠY PIPELINE ĐỒNG BỘ 5 BẢNG THEO ĐÚNG ER DIAGRAM
# ==============================================================================
# Ánh xạ: (Tên thư mục nguồn trên MinIO -> Tên bảng Bronze tương ứng của thầy)
tables_mapping = {
    "products": "raw_products",
    "customers": "raw_customers",
    "order_items": "raw_order_items",
    "orders": "raw_orders",
    "payments": "raw_payment_attempts" # Thầy đặt tên bảng là raw_payment_attempts
}

for src_folder, target_table in tables_mapping.items():
    ingest_to_bronze(src_folder, target_table)

print("\n==================================================")
print("🎉 [HOÀN THÀNH] TOÀN BỘ 5 BẢNG BRONZE ĐÃẰM GỌN TRONG DATALAKE!")
print("==================================================")