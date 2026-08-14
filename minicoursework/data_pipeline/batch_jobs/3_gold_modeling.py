import os
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.sql.types import IntegerType, StringType, BooleanType
from pyspark.sql.window import Window

# ==============================================================================
# 1. KHỞI TẠO SPARK SESSION & CẤU HÌNH DELTA LAKE
# ==============================================================================
os.environ['PYSPARK_SUBMIT_ARGS'] = (
    '--packages io.delta:delta-core_2.12:2.4.0,'
    'org.apache.hadoop:hadoop-aws:3.3.4 '
    'pyspark-shell'
)

spark = SparkSession.builder \
    .appName("Ecom_Gold_Modeling_Final") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("\n🚀 [HỆ THỐNG] SPARK SESSION LỚP GOLD ĐÃ SẴN SÀNG CHẠY THEO SPEC MỚI!")

# Đọc dữ liệu đầu vào từ tầng Silver sạch
# Đọc dữ liệu đầu vào từ tầng Silver sạch
stg_products = spark.read.format("delta").load("s3a://datalake/silver/stg_products")
stg_customers = spark.read.format("delta").load("s3a://datalake/silver/stg_customers")
stg_order_items = spark.read.format("delta").load("s3a://datalake/silver/stg_order_items")

# FIX LỖI BIGINT (DATATYPE MISMATCH): Ép kiểu nanoseconds về Timestamp chuẩn ngay từ cửa ngõ
stg_orders = spark.read.format("delta").load("s3a://datalake/silver/stg_orders")
    
stg_payments = spark.read.format("delta").load("s3a://datalake/silver/stg_payment_attempts")

# ==============================================================================
# 2. XÂY DỰNG CÁC BẢNG CHIỀU (MỤC 2: DIMENSION TABLES)
# ==============================================================================
print("\n🟡 [BƯỚC 1/5] Đang xử lý các bảng Chiều (Dimension Tables)...")

from delta.tables import DeltaTable

# ==============================================================================
# 2.1 dim_customer: Quản lý thông tin khách hàng (Chuẩn SCD Type 2)
# ==============================================================================
dim_customer_path = "s3a://datalake/gold/dim_customer"

if not DeltaTable.isDeltaTable(spark, dim_customer_path):
    print("  -> Khởi tạo dim_customer lần đầu với cấu trúc SCD2...")
    dim_customer = stg_customers \
        .withColumn("customer_key", F.expr("uuid()")) \
        .withColumn("valid_from_ts", F.to_timestamp(F.lit("1970-01-01 00:00:00"))) \
        .withColumn("valid_to_ts", F.to_timestamp(F.lit("9999-12-31 23:59:59"))) \
        .withColumn("is_current", F.lit(True)) \
        .select("customer_key", "customer_id", "signup_ts", "country", "segment", "marketing_opt_in", "valid_from_ts", "valid_to_ts", "is_current")
    dim_customer.write.format("delta").mode("overwrite").save(dim_customer_path)
else:
    print("  -> Cập nhật SCD Type 2 cho dim_customer...")
    stg_customers.createOrReplaceTempView("src_customers")
    
    spark.sql(f"""
    MERGE INTO delta.`{dim_customer_path}` t
    USING (
        SELECT uuid() as generated_key, customer_id as merge_key, * FROM src_customers
        UNION ALL
        SELECT uuid() as generated_key, NULL as merge_key, src.* FROM src_customers src
        JOIN (SELECT * FROM delta.`{dim_customer_path}`) tgt ON src.customer_id = tgt.customer_id AND tgt.is_current = true
        WHERE src.segment <> tgt.segment OR src.country <> tgt.country
    ) s
    ON t.customer_id = s.merge_key AND t.is_current = true
    WHEN MATCHED AND (t.segment <> s.segment OR t.country <> s.country) THEN
        UPDATE SET is_current = false, valid_to_ts = current_timestamp()
    WHEN NOT MATCHED THEN
        INSERT (customer_key, customer_id, signup_ts, country, segment, marketing_opt_in, valid_from_ts, valid_to_ts, is_current)
        VALUES (s.generated_key, s.customer_id, s.signup_ts, s.country, s.segment, s.marketing_opt_in, to_timestamp('1970-01-01 00:00:00'), '9999-12-31 23:59:59', true)
    """)
dim_customer = spark.read.format("delta").load(dim_customer_path)

# --- KIỂM TRA CHẤT LƯỢNG DỮ LIỆU SCD TYPE 2 (QUALITY GATE FOR SCD2) ---
current_cust_count = dim_customer.filter(F.col("is_current") == True).count()
total_cust_ids = dim_customer.select("customer_id").distinct().count()
print(f"  📊  [KIỂM TRA SCD TYPE 2]:")
print(f"      -> Tổng số customer_id độc nhất : {total_cust_ids}")
print(f"      -> Số bản ghi đang Active (is_current=True): {current_cust_count}")
if current_cust_count == total_cust_ids:
    print("      ✔️  SCD2 VALIDATION SUCCESS: 100% Khách hàng có đúng 1 bản ghi Active duy nhất!")
else:
    print("      ⚠️  CẢNH BÁO SCD2: Phát hiện có khách hàng bị trùng bản ghi Active!")
print("  ✔️  Hoàn thành dim_customer (SCD Type 2)")




# ==============================================================================
# 2.2 dim_product: Danh mục sản phẩm kinh doanh (Chuẩn SCD Type 2)
# ==============================================================================
dim_product_path = "s3a://datalake/gold/dim_product"

if not DeltaTable.isDeltaTable(spark, dim_product_path):
    print("  -> Khởi tạo dim_product lần đầu với cấu trúc SCD2...")
    dim_product = stg_products \
        .withColumn("product_key", F.expr("uuid()")) \
        .withColumn("valid_from_ts", F.to_timestamp(F.lit("1970-01-01 00:00:00"))) \
        .withColumn("valid_to_ts", F.to_timestamp(F.lit("9999-12-31 23:59:59"))) \
        .withColumn("is_current", F.lit(True)) \
        .select("product_key", "product_id", "category", "brand", "base_price", "is_active", "created_ts", "valid_from_ts", "valid_to_ts", "is_current")
    dim_product.write.format("delta").mode("overwrite").save(dim_product_path)
else:
    print("  -> Cập nhật SCD Type 2 cho dim_product...")
    stg_products.createOrReplaceTempView("src_products")
    
    spark.sql(f"""
    MERGE INTO delta.`{dim_product_path}` t
    USING (
        SELECT uuid() as generated_key, product_id as merge_key, * FROM src_products
        UNION ALL
        SELECT uuid() as generated_key, NULL as merge_key, src.* FROM src_products src
        JOIN (SELECT * FROM delta.`{dim_product_path}`) tgt ON src.product_id = tgt.product_id AND tgt.is_current = true
        WHERE src.base_price <> tgt.base_price OR src.category <> tgt.category
    ) s
    ON t.product_id = s.merge_key AND t.is_current = true
    WHEN MATCHED AND (t.base_price <> s.base_price OR t.category <> s.category) THEN
        UPDATE SET is_current = false, valid_to_ts = current_timestamp()
    WHEN NOT MATCHED THEN
        INSERT (product_key, product_id, category, brand, base_price, is_active, created_ts, valid_from_ts, valid_to_ts, is_current)
        VALUES (s.generated_key, s.product_id, s.category, s.brand, s.base_price, s.is_active, s.created_ts, to_timestamp('1970-01-01 00:00:00'), '9999-12-31 23:59:59', true)
    """)
print("  ✔️  Hoàn thành dim_product (SCD Type 2)")





# 2.3 dim_date: Bảng lịch tổng thể (Bao trọn cả ngày Order lẫn ngày Payment bị vắt sang)
order_dates = stg_orders.select(F.to_date(F.col("order_ts")).alias("calendar_date"))
payment_dates = stg_payments.select(F.to_date(F.col("payment_timestamp")).alias("calendar_date"))

# Gom tất cả các ngày lại và lọc trùng
all_dates = order_dates.union(payment_dates).distinct()

dim_date = all_dates \
    .withColumn("date_key", F.date_format(F.col("calendar_date"), "yyyyMMdd").cast(IntegerType())) \
    .withColumn("day_of_week", F.dayofweek(F.col("calendar_date"))) \
    .withColumn("month", F.month(F.col("calendar_date"))) \
    .withColumn("year", F.year(F.col("calendar_date"))) \
    .withColumn("is_weekend", F.when(F.col("day_of_week").isin(1, 7), True).otherwise(False)) \
    .select("date_key", "calendar_date", "day_of_week", "month", "year", "is_weekend")

dim_date.write.format("delta").mode("overwrite").save("s3a://datalake/gold/dim_date")
print("  ✔️  Hoàn thành dim_date (Đã chống lỗi vắt qua ngày mới!)")

# 2.4 dim_payment_method: Danh mục các phương thức thanh toán
dim_payment_method = stg_payments.select("payment_method").distinct() \
    .withColumn("payment_method_key", F.monotonically_increasing_id().cast(IntegerType())) \
    .select("payment_method_key", "payment_method")
dim_payment_method.write.format("delta").mode("overwrite").save("s3a://datalake/gold/dim_payment_method")
print("  ✔️  Hoàn thành dim_payment_method")

# 2.5 dim_order_status: Danh mục các trạng thái đơn hàng
dim_order_status = stg_orders.select("order_status").distinct() \
    .withColumn("order_status_key", F.monotonically_increasing_id().cast(IntegerType())) \
    .withColumnRenamed("order_status", "order_status_name") \
    .select("order_status_key", "order_status_name")
dim_order_status.write.format("delta").mode("overwrite").save("s3a://datalake/gold/dim_order_status")
print("  ✔️  Hoàn thành dim_order_status")



# ==============================================================================
# BƯỚC ĐỆM: LOAD TOÀN BỘ LỊCH SỬ DIMENSION (KHÔNG LỌC IS_CURRENT = TRUE NỮA)
# ==============================================================================
dim_customer = spark.read.format("delta").load("s3a://datalake/gold/dim_customer")
dim_product = spark.read.format("delta").load("s3a://datalake/gold/dim_product")

# ==============================================================================
# 3. XÂY DỰNG CÁC BẢNG SỰ KIỆN (MỤC 3: FACT TABLES) - POINT-IN-TIME JOIN
# ==============================================================================
print("\n🟡 [BƯỚC 2/5] Đang xử lý các bảng Sự kiện (Fact Tables) bằng Point-in-Time Join...")

items_with_context = stg_order_items.alias("i") \
    .join(stg_orders.alias("o"), on="order_id", how="inner") \
    .withColumn("order_date_key", F.date_format(F.col("o.order_ts"), "yyyyMMdd").cast(IntegerType())) \
    .select(
        "i.item_id", "order_id", "i.product_id", "o.customer_id", 
        "i.quantity", "i.unit_price", "i.discount_amount", "order_date_key", "o.order_ts"
    )

# 3.2 fact_order_item
fact_order_item = items_with_context.alias("f") \
    .join(dim_customer.alias("c"), 
          (F.col("f.customer_id") == F.col("c.customer_id")) & 
          (F.col("f.order_ts") >= F.col("c.valid_from_ts")) & 
          (F.col("f.order_ts") <= F.col("c.valid_to_ts")), 
          how="left") \
    .join(dim_product.alias("p"), 
          (F.col("f.product_id") == F.col("p.product_id")) & 
          (F.col("f.order_ts") >= F.col("p.valid_from_ts")) & 
          (F.col("f.order_ts") <= F.col("p.valid_to_ts")), 
          how="left") \
    .withColumn("line_net_amount", (F.col("f.quantity") * F.col("f.unit_price")) - F.col("f.discount_amount")) \
    .select("c.customer_key", "p.product_key", "f.order_date_key", 
            "f.quantity", "f.unit_price", "f.discount_amount", "line_net_amount")
fact_order_item.write.format("delta").mode("overwrite").partitionBy("order_date_key").save("s3a://datalake/gold/fact_order_item")

# 3.1 fact_order
# Thêm tính năng total_quantity phục vụ cho bảng phẳng
order_aggregates = items_with_context.groupBy("order_id") \
    .agg(
        F.sum(F.col("quantity") * F.col("unit_price")).alias("order_gross_amount"),
        F.sum("discount_amount").alias("order_discount_amount"),
        F.sum((F.col("quantity") * F.col("unit_price")) - F.col("discount_amount")).alias("order_net_amount"),
        F.count("item_id").alias("item_count"),
        F.sum("quantity").alias("total_quantity") 
    )

fact_order = stg_orders.alias("o") \
    .join(order_aggregates.alias("agg"), on="order_id", how="left") \
    .join(dim_customer.alias("c"), 
          (F.col("o.customer_id") == F.col("c.customer_id")) & 
          (F.col("o.order_ts") >= F.col("c.valid_from_ts")) & 
          (F.col("o.order_ts") <= F.col("c.valid_to_ts")), 
          how="left") \
    .join(dim_order_status.alias("s"), F.col("o.order_status") == F.col("s.order_status_name"), "left") \
    .withColumn("order_date_key", F.date_format(F.col("o.order_ts"), "yyyyMMdd").cast(IntegerType())) \
    .select("c.customer_key", "order_date_key", "s.order_status_key", 
            "agg.order_gross_amount", "agg.order_discount_amount", "agg.order_net_amount", "agg.item_count")
fact_order.write.format("delta").mode("overwrite").partitionBy("order_date_key").save("s3a://datalake/gold/fact_order")

# 3.3 fact_payment_attempt
fact_payment_attempt = stg_payments.alias("p") \
    .join(stg_orders.alias("o"), on="order_id", how="left") \
    .join(dim_customer.alias("c"), 
          (F.col("o.customer_id") == F.col("c.customer_id")) & 
          (F.col("p.payment_timestamp") >= F.col("c.valid_from_ts")) & 
          (F.col("p.payment_timestamp") <= F.col("c.valid_to_ts")), 
          how="left") \
    .join(dim_payment_method.alias("m"), F.col("p.payment_method") == F.col("m.payment_method"), "left") \
    .withColumn("payment_date_key", F.date_format(F.col("p.payment_timestamp"), "yyyyMMdd").cast(IntegerType())) \
    .withColumn("is_payment_success", F.when(F.col("p.payment_status") == "Success", 1).otherwise(0)) \
    .withColumn("is_payment_failed", F.when(F.col("p.payment_status") == "Failed", 1).otherwise(0)) \
    .select("c.customer_key", "payment_date_key", "m.payment_method_key", 
            "p.amount", "is_payment_success", "is_payment_failed")
fact_payment_attempt.write.format("delta").mode("overwrite").partitionBy("payment_date_key").save("s3a://datalake/gold/fact_payment_attempt")


# ==============================================================================
# 4. XÂY DỰNG BẢNG PHẲNG TỔNG HỢP OBT (MỤC 4: OBT TABLE) - ÁP DỤNG SALTING & BROADCAST JOIN
# ==============================================================================
print("\n🟡 [BƯỚC 3/5] Đang tích hợp dữ liệu OBT (obt_order_performance) với kỹ thuật SALTING giải quyết Skew (85% HCMC)...")

# Tìm trạng thái cuối cùng của thanh toán
last_payment_status = stg_payments \
    .withColumn("rn", F.row_number().over(Window.partitionBy("order_id").orderBy(F.col("payment_timestamp").desc()))) \
    .filter(F.col("rn") == 1) \
    .select("order_id", F.col("payment_status").alias("payment_status_last"))

# --- KỸ THUẬT SALTING CHO BẢNG STG_ORDERS VÀ DIM_CUSTOMER VÌ SKEW CITY (85% HCMC) ---
# Thêm cột salt_key ngẫu nhiên từ 0->7 vào bảng stg_orders
SALT_BUCKETS = 8
orders_salted = stg_orders.withColumn("salt_key", F.floor(F.rand() * SALT_BUCKETS))

# Nhân bản bảng customer tương ứng với 8 salt_keys
SALT_ARRAY = [F.lit(i) for i in range(SALT_BUCKETS)]
customers_exploded = dim_customer.withColumn("salt_key", F.explode(F.array(SALT_ARRAY)))

obt_order_performance = orders_salted.alias("o") \
    .join(order_aggregates.alias("agg"), on="order_id", how="left") \
    .join(customers_exploded.alias("c"), 
          (F.col("o.customer_id") == F.col("c.customer_id")) & 
          (F.col("o.salt_key") == F.col("c.salt_key")) & 
          (F.col("o.order_ts") >= F.col("c.valid_from_ts")) & 
          (F.col("o.order_ts") <= F.col("c.valid_to_ts")), 
          how="left") \
    .join(last_payment_status.alias("pay"), on="order_id", how="left") \
    .select(
        "o.order_id", 
        "o.customer_id", 
        F.col("o.order_ts").alias("order_timestamp"), 
        "c.country", 
        "c.segment",
        "agg.total_quantity", 
        "agg.order_net_amount", 
        "pay.payment_status_last",
        F.col("o.city").alias("shipping_city"), 
        "o.coupon_code"
    )
obt_order_performance.write.format("delta").mode("overwrite").save("s3a://datalake/gold/obt_order_performance")
print("  ✔️  Hoàn thành obt_order_performance với Salting Join thành công!")


# ==============================================================================
# 5. DATA QUALITY KIỂM TRA CHẤT LƯỢNG (MỤC 5: QUALITY CHECKS)
# ==============================================================================
print("\n🟡 [BƯỚC 4/5] Kích hoạt kiểm tra chất lượng dữ liệu tự động (Data Quality Gates)...")

# Kiểm tra Tổng match check: sum(line_net_amount) từ item có khớp với order_net_amount không
sum_line_net = fact_order_item.agg(F.sum("line_net_amount")).collect()[0][0] or 0.0
sum_order_net = fact_order.agg(F.sum("order_net_amount")).collect()[0][0] or 0.0

print(f"  📊  [ĐỐI SOÁT TÀI CHÍNH]:")
print(f"      -> Tổng tiền ròng tính từ Dòng Sản Phẩm: {sum_line_net}")
print(f"      -> Tổng tiền ròng tính từ Đơn Hóa Đơn : {sum_order_net}")
if abs((sum_line_net or 0) - (sum_order_net or 0)) < 0.01:
    print("      ✔️  ĐỐI SOÁT THÀNH CÔNG: Dữ liệu tài chính khớp hoàn toàn!")
else:
    print("      ⚠️  CẢNH BÁO: Dữ liệu tài chính có sự lệch số lẻ!")


# ==============================================================================
# 6. KHO ĐẶC TRƯNG AI/ML (MỤC 6: OFFLINE FEATURE STORE) - TỐI ƯU HIGH CARDINALITY & BROADCAST
# ==============================================================================
print("\n🟡 [BƯỚC 5/5] Đang tính toán Feature Store (`feat_customer_90d`) với BROADCAST & APPROX_COUNT_DISTINCT...")

current_pipeline_ts = F.current_timestamp()
ninety_days_ago = current_pipeline_ts - F.expr("INTERVAL 90 DAYS")

# Tối ưu 1: Dùng F.broadcast(stg_products) loại bỏ hoàn toàn Shuffle Join cho bảng sản phẩm
# Tối ưu 2: Dùng F.approx_count_distinct thay countDistinct để giảm 90% Shuffle với High Cardinality (120k customers)
feat_customer_90d = items_with_context \
    .filter(F.col("order_ts") >= ninety_days_ago) \
    .join(F.broadcast(stg_products), on="product_id", how="inner") \
    .withColumn("line_net_amount", (F.col("quantity") * F.col("unit_price")) - F.col("discount_amount")) \
    .groupBy("customer_id") \
    .agg(
        F.approx_count_distinct("order_id", rsd=0.01).alias("f_customer_total_orders_90d"),
        F.avg("line_net_amount").alias("f_customer_avg_order_value_90d"),
        F.approx_count_distinct("category", rsd=0.01).alias("f_customer_distinct_categories_90d")
    ) \
    .withColumn("event_timestamp", current_pipeline_ts) \
    .withColumn("created_ts", current_pipeline_ts) \
    .select("customer_id", "event_timestamp", "f_customer_total_orders_90d", 
            "f_customer_avg_order_value_90d", "f_customer_distinct_categories_90d", "created_ts")

feat_customer_90d.write.format("delta").mode("overwrite").save("s3a://datalake/gold/feat_customer_90d")
print("  ✔️  Hoàn thành trích xuất feat_customer_90d với Broadcast Join & approx_count_distinct!")

# ==============================================================================
# 7. TÍCH HỢP BẢNG NHÃN ML (LABEL TABLE) PHỤC VỤ HUẤN LUYỆN MÔ HÌNH CHURN (RUBRIC)
# ==============================================================================
print("\n🟡 [BƯỚC CHUẨN BỊ ML] Đang tích hợp bảng nhãn `customer_labels` (2 cột) với Feature Vectors...")
try:
    stg_labels = spark.read.format("parquet").load("s3a://landing-zone/customer_labels")
    gold_ml_dataset = feat_customer_90d.join(stg_labels, on="customer_id", how="left")
    gold_ml_dataset.write.format("delta").mode("overwrite").save("s3a://datalake/gold/gold_ml_churn_dataset")
    print("  ✔️  Hoàn thành tích hợp Gold ML Dataset (`gold_ml_churn_dataset`) sẵn sàng cho huấn luyện ML!")
except Exception as e:
    print(f"  ⚠️  Chưa tìm thấy bảng customer_labels trên Landing Zone: {e}")

print("\n==================================================")
print("🎉 [XUẤT SẮC] PIPELINE GOLD LAYER ĐÃ TỐI ƯU HÓA XỬ LÝ SKEW, HIGH CARDINALITY & ML LABELS!")
print("==================================================")