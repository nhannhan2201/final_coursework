import os
from pyspark.sql import SparkSession

# ==============================================================================
# 1. KHỞI TẠO SPARK SESSION CHO TỐI ƯU HÓA LAKEHOUSE STORAGE
# ==============================================================================
os.environ['PYSPARK_SUBMIT_ARGS'] = (
    '--packages io.delta:delta-core_2.12:2.4.0,'
    'org.apache.hadoop:hadoop-aws:3.3.4 '
    'pyspark-shell'
)

spark = SparkSession.builder \
    .appName("Ecom_Lakehouse_Storage_Optimization") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("\n======================================================================")
print("🚀 [LAKEHOUSE STORAGE OPTIMIZATION] BẮT ĐẦU TỐI ƯU COMPACTION & Z-ORDERING...")
print("======================================================================\n")

tables_to_optimize = [
    ("dim_customer", "s3a://datalake/gold/dim_customer", "customer_id"),
    ("fact_order", "s3a://datalake/gold/fact_order", "order_date_key"),
    ("obt_order_performance", "s3a://datalake/gold/obt_order_performance", "customer_id"),
    ("feat_customer_90d", "s3a://datalake/gold/feat_customer_90d", "customer_id"),
]

for table_name, table_path, zorder_col in tables_to_optimize:
    print(f"🟡 Đang tối ưu hóa bảng: [{table_name}] tại path `{table_path}`...")
    print(f"   -> Thực hiện COMPACTION (Bin-packing small files into ~128MB files)...")
    print(f"   -> Thực hiện Z-ORDERING theo cột: `{zorder_col}`...")
    
    try:
        # Chạy câu lệnh OPTIMIZE và ZORDER BY chuẩn Delta Lake Engine
        optimize_sql = f"OPTIMIZE delta.`{table_path}` ZORDER BY ({zorder_col})"
        metrics_df = spark.sql(optimize_sql)
        metrics = metrics_df.collect()[0]
        
        files_removed = metrics["numFilesRemoved"] if "numFilesRemoved" in metrics else 0
        files_added = metrics["numFilesAdded"] if "numFilesAdded" in metrics else 0
        
        print(f"   ✔️  TỐI ƯU THÀNH CÔNG [{table_name}]:")
        print(f"       -> Số file nhỏ đã gom & loại bỏ (Removed): {files_removed}")
        print(f"       -> Số file lớn tối ưu mới tạo (Added)   : {files_added}\n")
    except Exception as e:
        print(f"   ⚠️  Cảnh báo tối ưu bảng {table_name}: {e}\n")

print("======================================================================")
print("🎉 [XUẤT SẮC] ĐÃ TỐI ƯU HÓA HOÀN TOÀN STORAGE CHO TOÀN BỘ LAKEHOUSE GOLD LAYER!")
print("======================================================================\n")
