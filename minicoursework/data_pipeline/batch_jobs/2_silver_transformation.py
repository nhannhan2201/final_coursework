import os
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from delta.tables import DeltaTable

# ==============================================================================
# 1. KHỞI TẠO SPARK SESSION
# ==============================================================================
os.environ['PYSPARK_SUBMIT_ARGS'] = (
    '--packages io.delta:delta-core_2.12:2.4.0,'
    'org.apache.hadoop:hadoop-aws:3.3.4 '
    'pyspark-shell'
)

spark = SparkSession.builder \
    .appName("Ecom_Silver_Transformation_V2") \
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

spark.sparkContext.setLogLevel("WARN")
print("\n🚀 [HỆ THỐNG] SPARK LỚP SILVER ĐÃ TÁI CẤU TRÚC ĐỂ HỖ TRỢ UPSERT/MERGE!")

# ==============================================================================
# HÀM UPSERT ĐA NĂNG (GHI ĐÈ NẾU TRÙNG, THÊM MỚI NẾU CHƯA CÓ)
# ==============================================================================
def upsert_to_silver(source_df, target_path, join_condition):
    if not DeltaTable.isDeltaTable(spark, target_path):
        source_df.write.format("delta").mode("overwrite").save(target_path)
    else:
        target_table = DeltaTable.forPath(spark, target_path)
        target_table.alias("target") \
            .merge(source_df.alias("source"), join_condition) \
            .whenMatchedUpdateAll() \
            .whenNotMatchedInsertAll() \
            .execute()


# ==============================================================================
# 2. PIPELINE XỬ LÝ CHI TIẾT CHO TỪNG THỰC THỂ (GIỮ NGUYÊN LOGIC CỦA BẠN)
# ==============================================================================

def process_stg_products():
    print("\n✨ Xử lý: raw_products ──> stg_products")
    df = spark.read.format("delta").load("s3a://datalake/bronze/raw_products")
    
    # Giữ nguyên cấu trúc: product_id, category, brand, base_price, is_active, created_ts
    stg_df = df.select("product_id", "category", "brand", "base_price", "is_active", "created_ts", "raw_id", "_ingested_at") \
               .dropDuplicates(["product_id"])
    
    upsert_to_silver(stg_df, "s3a://datalake/silver/stg_products", "target.product_id = source.product_id")
    print("  ✔️ Hoàn thành bảng stg_products!")


def process_stg_customers():
    print("\n✨ Xử lý: raw_customers ──> stg_customers")
    df = spark.read.format("delta").load("s3a://datalake/bronze/raw_customers")
    
    # Khớp chuẩn 100% thuộc tính sinh ra từ file generate của bạn
    stg_df = df.select("customer_id", "signup_ts", "country", "city", "segment", "marketing_opt_in", "raw_id", "_ingested_at") \
               .dropDuplicates(["customer_id"])
    
    upsert_to_silver(stg_df, "s3a://datalake/silver/stg_customers", "target.customer_id = source.customer_id")
    print("  ✔️ Hoàn thành bảng stg_customers!")


def process_stg_order_items():
    print("\n✨ Xử lý: raw_order_items ──> stg_order_items")
    df = spark.read.format("delta").load("s3a://datalake/bronze/raw_order_items")
    
    # Đổi tên order_item_id -> item_id cho tinh gọn, giữ nguyên quantity, unit_price, discount_amount
    stg_df = df.withColumnRenamed("order_item_id", "item_id") \
               .select("item_id", "order_id", "product_id", "quantity", "unit_price", "discount_amount", "raw_id", "_ingested_at") \
               .dropDuplicates(["item_id"]) # Khử trùng triệt để nhiễu lặp 2% của hệ thống nguồn
    
    upsert_to_silver(stg_df, "s3a://datalake/silver/stg_order_items", "target.item_id = source.item_id")
    print("  ✔️ Hoàn thành bảng stg_order_items!")


def process_stg_orders():
    print("\n✨ Xử lý: raw_orders ──> stg_orders")
    df = spark.read.format("delta").load("s3a://datalake/bronze/raw_orders")
    
    # Kế thừa xử lý tránh lỗi khi đọc data cũ chưa có cột mới (Schema Evolution)
    # Giữ nguyên toàn bộ logic lấy cột của bạn
    has_new_cols = "shipping_method" in df.columns and "coupon_code" in df.columns
    
    if has_new_cols:
        stg_df = df.withColumn("order_status", F.col("status")) \
                   .select("order_id", "customer_id", "order_ts", "order_status", "city", "shipping_method", "coupon_code", "raw_id", "_ingested_at")
    else:
        stg_df = df.withColumn("order_status", F.col("status")) \
                   .select("order_id", "customer_id", "order_ts", "order_status", "city", "raw_id", "_ingested_at") \
                   .withColumn("shipping_method", F.lit(None).cast("string")) \
                   .withColumn("coupon_code", F.lit(None).cast("string"))
                   
    stg_df = stg_df.dropDuplicates(["order_id"])
    
    upsert_to_silver(stg_df, "s3a://datalake/silver/stg_orders", "target.order_id = source.order_id")
    print("  ✔️ Hoàn thành bảng stg_orders!")


def process_stg_payment_attempts():
    print("\n✨ Xử lý: raw_payment_attempts ──> stg_payment_attempts")
    df = spark.read.format("delta").load("s3a://datalake/bronze/raw_payment_attempts")
    
    # Giữ nguyên vẹn dữ liệu tài chính thô, không join chéo, không tạo trường giả
    stg_df = df.select("payment_id", "order_id", "payment_timestamp", "payment_method", "amount", "payment_status", "raw_id", "_ingested_at") \
               .dropDuplicates(["payment_id"])
               
    upsert_to_silver(stg_df, "s3a://datalake/silver/stg_payment_attempts", "target.payment_id = source.payment_id")
    print("  ✔️ Hoàn thành bảng stg_payment_attempts!")


# ==============================================================================
# 3. KÍCH HOẠT CHẠY PIPELINE
# ==============================================================================
process_stg_products()
process_stg_customers()
process_stg_order_items()
process_stg_orders()
process_stg_payment_attempts()

print("\n==================================================")
print("🎉 [XỬ LÝ XONG] LỚP SILVER MỚI ĐÃ SẴN SÀNG ĐỂ PHỤC VỤ TẦNG GOLD!")
print("==================================================")