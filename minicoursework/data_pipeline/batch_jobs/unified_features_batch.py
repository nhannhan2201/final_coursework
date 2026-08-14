import os
import redis
import pandas as pd
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from delta.tables import DeltaTable

# ==============================================================================
# 1. KHỞI TẠO SPARK KẾT NỐI MINIO (OFFLINE STORE)
# ==============================================================================
os.environ['PYSPARK_SUBMIT_ARGS'] = (
    '--packages io.delta:delta-core_2.12:2.4.0,'
    'org.apache.hadoop:hadoop-aws:3.3.4 '
    'pyspark-shell'
)

spark = SparkSession.builder \
    .appName("Ecom_Unified_Features_Batch") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("\n🚀 [HỆ THỐNG] ĐANG ĐỒNG BỘ REDIS VÀO MINIO VÀ HỢP NHẤT DỮ LIỆU...")

def merge_unified_features():
    # ==============================================================================
    # BƯỚC 1: LẤY DỮ LIỆU ONLINE TỪ REDIS (Do Flink tính toán)
    # ==============================================================================
    try:
        r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        keys = r.keys('feat_stream:*')
        
        if not keys:
            print("⚠️ Không có dữ liệu streaming mới trong Redis để hợp nhất.")
            return

        stream_data = []
        for key in keys:
            data = r.hgetall(key)
            data['customer_id'] = key.split(':')[1]
            stream_data.append(data)
            
        stream_pd = pd.DataFrame(stream_data)
        stream_df = spark.createDataFrame(stream_pd)
        
        # Ép kiểu dữ liệu chuẩn xác
        stream_df = stream_df.withColumn("f_stream_views_30m", F.col("f_stream_views_30m").cast("int")) \
                             .withColumn("f_stream_add_to_cart_30m", F.col("f_stream_add_to_cart_30m").cast("int")) \
                             .withColumn("f_stream_cart_to_purchase_ratio_60m", F.col("f_stream_cart_to_purchase_ratio_60m").cast("float")) \
                             .withColumn("event_timestamp", F.col("event_timestamp").cast("timestamp"))
                             
    except Exception as e:
        print(f"❌ Lỗi kết nối Redis: {e}")
        return

    # ==============================================================================
    # BƯỚC 1.5: DATA QUALITY CHECK CHO FEATURE (MỤC 7 CỦA SPEC)
    # ==============================================================================
    print("\n🔍 Đang kiểm tra chất lượng dữ liệu Feature (Data Quality Gate)...")
    
    # 1. Null check: Bắt buộc customer_id không được rỗng
    null_customers = stream_df.filter(F.col("customer_id").isNull()).count()
    if null_customers > 0:
        print(f"  ⚠️ CẢNH BÁO: Phát hiện {null_customers} dòng bị NULL customer_id. Đã tự động loại bỏ!")
        stream_df = stream_df.filter(F.col("customer_id").isNotNull())
        
    # 2. Logic check: Số view không được là số âm
    invalid_views = stream_df.filter(F.col("f_stream_views_30m") < 0).count()
    if invalid_views > 0:
        print(f"  ⚠️ CẢNH BÁO: Phát hiện {invalid_views} dòng có số view âm. Đã ép về 0!")
        stream_df = stream_df.withColumn("f_stream_views_30m", F.when(F.col("f_stream_views_30m") < 0, 0).otherwise(F.col("f_stream_views_30m")))
        
    print("  ✔️ Data Quality Check Pass! Dữ liệu đạt chuẩn ML.")

    # ==============================================================================
    # BƯỚC 2: GHI BẢNG STREAM 60M XUỐNG MINIO (BẮT BUỘC THEO SPEC)
    # ==============================================================================
    stream_path = "s3a://datalake/gold/feat_stream"
    if not DeltaTable.isDeltaTable(spark, stream_path):
        stream_df.write.format("delta").mode("overwrite").save(stream_path)
        print("✔️ Đã khởi tạo thành công bảng feat_stream_60m trên MinIO (Gold Layer)!")
    else:
        DeltaTable.forPath(spark, stream_path).alias("t").merge(
            stream_df.alias("s"), 
            "t.customer_id = s.customer_id AND t.event_timestamp = s.event_timestamp"
        ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
        print("✔️ Đã đồng bộ UPSERT dữ liệu feat_stream_60m xuống MinIO!")

    # ==============================================================================
    # BƯỚC 3: KẾT HỢP VỚI BẢNG LỊCH SỬ 90 NGÀY ĐỂ TẠO BẢNG UNIFIED
    # ==============================================================================
    try:
        offline_path = "s3a://datalake/gold/feat_customer_90d"
        offline_df = spark.read.format("delta").load(offline_path)
        
        unified_df = offline_df.alias("off").join(stream_df.alias("st"), "customer_id", "outer") \
            .select(
                "customer_id",
                F.coalesce(F.col("st.event_timestamp"), F.col("off.event_timestamp")).alias("event_timestamp"),
                F.coalesce(F.col("st.f_stream_views_30m"), F.lit(0)).alias("f_stream_views_30m"),
                F.coalesce(F.col("st.f_stream_add_to_cart_30m"), F.lit(0)).alias("f_stream_add_to_cart_30m"),
                F.coalesce(F.col("st.f_stream_cart_to_purchase_ratio_60m"), F.lit(0.0)).alias("f_stream_cart_to_purchase_ratio_60m"),
                F.coalesce(F.col("off.f_customer_total_orders_90d"), F.lit(0)).alias("f_customer_total_orders_90d"),
                F.coalesce(F.col("off.f_customer_avg_order_value_90d"), F.lit(0.0)).alias("f_customer_avg_order_value_90d"),
                F.coalesce(F.col("off.f_customer_distinct_categories_90d"), F.lit(0)).alias("f_customer_distinct_categories_90d"),
                F.current_timestamp().alias("created_ts")
            )
            
    except Exception as e:
        print(f"❌ Lỗi đọc bảng Offline 90 ngày: {e}")
        return

    # ==============================================================================
    # BƯỚC 4: GHI ĐÈ BẢNG UNIFIED XUỐNG MINIO
    # ==============================================================================
    unified_path = "s3a://datalake/gold/feat_customer_unified"
    if not DeltaTable.isDeltaTable(spark, unified_path):
        unified_df.write.format("delta").mode("overwrite").save(unified_path)
        print("✔️ Đã khởi tạo thành công bảng feat_customer_unified lần đầu tiên!")
    else:
        DeltaTable.forPath(spark, unified_path).alias("t").merge(
            unified_df.alias("s"), 
            "t.customer_id = s.customer_id AND t.event_timestamp = s.event_timestamp"
        ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
        print("✔️ Đã đồng bộ UPSERT dữ liệu Unified thành công xuống MinIO!")

if __name__ == "__main__":
    merge_unified_features()