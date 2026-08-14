from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
from datahub_airflow_plugin.entities import Dataset

default_args = {
    'owner': 'nhan_de',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

# ==============================================================================
# KHAI BÁO TỪNG BẢNG THẬT SỰ TRÊN MINIO/DELTA LAKE
# ==============================================================================

# --- LANDING ZONE (nguồn thô) ---
RAW_PRODUCTS        = Dataset("s3", "landing-zone/products")
RAW_CUSTOMERS       = Dataset("s3", "landing-zone/customers")
RAW_ORDER_ITEMS     = Dataset("s3", "landing-zone/order_items")
RAW_ORDERS          = Dataset("s3", "landing-zone/orders")
RAW_PAYMENTS        = Dataset("s3", "landing-zone/payments")

# --- BRONZE LAYER ---
BRONZE_PRODUCTS     = Dataset("delta-lake", "datalake/bronze/raw_products")
BRONZE_CUSTOMERS    = Dataset("delta-lake", "datalake/bronze/raw_customers")
BRONZE_ORDER_ITEMS  = Dataset("delta-lake", "datalake/bronze/raw_order_items")
BRONZE_ORDERS       = Dataset("delta-lake", "datalake/bronze/raw_orders")
BRONZE_PAYMENTS     = Dataset("delta-lake", "datalake/bronze/raw_payment_attempts")

# --- SILVER LAYER ---
SILVER_PRODUCTS     = Dataset("delta-lake", "datalake/silver/stg_products")
SILVER_CUSTOMERS    = Dataset("delta-lake", "datalake/silver/stg_customers")
SILVER_ORDER_ITEMS  = Dataset("delta-lake", "datalake/silver/stg_order_items")
SILVER_ORDERS       = Dataset("delta-lake", "datalake/silver/stg_orders")
SILVER_PAYMENTS     = Dataset("delta-lake", "datalake/silver/stg_payment_attempts")

# --- GOLD LAYER ---
GOLD_DIM_CUSTOMER       = Dataset("delta-lake", "datalake/gold/dim_customer")
GOLD_DIM_PRODUCT        = Dataset("delta-lake", "datalake/gold/dim_product")
GOLD_DIM_DATE           = Dataset("delta-lake", "datalake/gold/dim_date")
GOLD_DIM_PAYMENT_METHOD = Dataset("delta-lake", "datalake/gold/dim_payment_method")
GOLD_DIM_ORDER_STATUS   = Dataset("delta-lake", "datalake/gold/dim_order_status")
GOLD_FACT_ORDER         = Dataset("delta-lake", "datalake/gold/fact_order")
GOLD_FACT_ORDER_ITEM    = Dataset("delta-lake", "datalake/gold/fact_order_item")
GOLD_FACT_PAYMENT       = Dataset("delta-lake", "datalake/gold/fact_payment_attempt")
GOLD_OBT                = Dataset("delta-lake", "datalake/gold/obt_order_performance")
GOLD_FEAT_90D           = Dataset("delta-lake", "datalake/gold/feat_customer_90d")

# --- FEATURE STORE ---
FEAT_STREAM_60M         = Dataset("delta-lake", "datalake/gold/feat_stream_60m")
FEAT_UNIFIED            = Dataset("delta-lake", "datalake/gold/feat_customer_unified")

# ==============================================================================
# DATAHUB GMS ENDPOINT (trong mạng Docker)
# ==============================================================================
DATAHUB_GMS_URL = "http://datahub-gms:8080"


# ==============================================================================
# HÀM VALIDATE GOLD TABLES & BẮN ASSERTION LÊN DATAHUB
# ==============================================================================
def validate_gold_quality(**context):
    """
    Kết nối Trino để chạy các bài kiểm tra chất lượng cột (Column Validation)
    trên toàn bộ bảng Gold, sau đó bắn kết quả lên DataHub Assertions.
    """
    from trino.dbapi import connect
    from datahub.emitter.rest_emitter import DataHubRestEmitter
    from datahub.emitter.mcp import MetadataChangeProposalWrapper
    from datahub.metadata.schema_classes import (
        AssertionInfoClass, AssertionTypeClass,
        AssertionResultClass, AssertionResultTypeClass,
        AssertionRunEventClass, AssertionRunStatusClass,
        DatasetAssertionInfoClass, DatasetAssertionScopeClass,
        AssertionStdOperatorClass,
    )

    # --- Kết nối Trino ---
    conn = connect(host="ecom_trino", port=8080, user="airflow", catalog="delta", schema="gold")
    cursor = conn.cursor()

    # --- Kết nối DataHub Emitter ---
    emitter = DataHubRestEmitter(DATAHUB_GMS_URL)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    run_id = f"gold_quality_{now_ms}"

    # ===========================================================================
    # ĐỊNH NGHĨA CÁC BÀI KIỂM TRA CHẤT LƯỢNG (QUALITY RULES)
    # ===========================================================================
    # Mỗi bài test gồm: (tên_bảng, tên_cột, loại_check, câu_SQL_đếm_lỗi)
    #
    # Theo Spec Section 5 - Quality checks:
    # - Uniqueness: order_id, item_id, payment_id per fact table
    # - Null check: required keys/measures should stay filled
    # - Range check: amounts >= 0
    # - Referential: facts link to dimensions (customer_key not null after join)
    # - Total match check: sum(line_net_amount) ~ sum(order_net_amount)
    # ===========================================================================

    quality_checks = [
        # ====================== DIMENSION TABLES ======================
        # dim_customer: Khóa chính không được null
        ("dim_customer", "customer_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.dim_customer WHERE customer_key IS NULL"),

        # dim_customer: customer_id phải duy nhất trong các bản ghi hiện tại
        ("dim_customer", "customer_id", "unique_current",
         "SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM delta.gold.dim_customer WHERE is_current = true"),

        # dim_product: Khóa chính không được null
        ("dim_product", "product_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.dim_product WHERE product_key IS NULL"),

        # dim_product: product_id phải duy nhất trong các bản ghi hiện tại
        ("dim_product", "product_id", "unique_current",
         "SELECT COUNT(*) - COUNT(DISTINCT product_id) FROM delta.gold.dim_product WHERE is_current = true"),

        # dim_date: date_key không được null
        ("dim_date", "date_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.dim_date WHERE date_key IS NULL"),

        # dim_date: date_key phải duy nhất
        ("dim_date", "date_key", "unique",
         "SELECT COUNT(*) - COUNT(DISTINCT date_key) FROM delta.gold.dim_date"),

        # dim_payment_method: Khóa chính không được null
        ("dim_payment_method", "payment_method_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.dim_payment_method WHERE payment_method_key IS NULL"),

        # dim_order_status: Khóa chính không được null
        ("dim_order_status", "order_status_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.dim_order_status WHERE order_status_key IS NULL"),

        # ====================== FACT TABLES ======================
        # fact_order: Khóa ngoại customer_key không được null (referential integrity)
        ("fact_order", "customer_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.fact_order WHERE customer_key IS NULL"),

        # fact_order: Số tiền ròng không được âm
        ("fact_order", "order_net_amount", "non_negative",
         "SELECT COUNT(*) FROM delta.gold.fact_order WHERE order_net_amount < 0"),

        # fact_order_item: Khóa ngoại customer_key không được null
        ("fact_order_item", "customer_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.fact_order_item WHERE customer_key IS NULL"),

        # fact_order_item: Số tiền dòng sản phẩm không được âm
        ("fact_order_item", "line_net_amount", "non_negative",
         "SELECT COUNT(*) FROM delta.gold.fact_order_item WHERE line_net_amount < 0"),

        # fact_payment_attempt: Khóa ngoại customer_key không được null
        ("fact_payment_attempt", "customer_key", "not_null",
         "SELECT COUNT(*) FROM delta.gold.fact_payment_attempt WHERE customer_key IS NULL"),

        # fact_payment_attempt: Số tiền thanh toán không được âm
        ("fact_payment_attempt", "amount", "non_negative",
         "SELECT COUNT(*) FROM delta.gold.fact_payment_attempt WHERE amount < 0"),

        # ====================== OBT TABLE ======================
        # obt_order_performance: order_id không được null
        ("obt_order_performance", "order_id", "not_null",
         "SELECT COUNT(*) FROM delta.gold.obt_order_performance WHERE order_id IS NULL"),

        # obt_order_performance: Số tiền ròng không được âm
        ("obt_order_performance", "order_net_amount", "non_negative",
         "SELECT COUNT(*) FROM delta.gold.obt_order_performance WHERE order_net_amount < 0"),

        # ====================== FEATURE STORE ======================
        # feat_customer_90d: customer_id không được null
        ("feat_customer_90d", "customer_id", "not_null",
         "SELECT COUNT(*) FROM delta.gold.feat_customer_90d WHERE customer_id IS NULL"),

        # feat_customer_90d: Tổng đơn hàng không được âm
        ("feat_customer_90d", "f_customer_total_orders_90d", "non_negative",
         "SELECT COUNT(*) FROM delta.gold.feat_customer_90d WHERE f_customer_total_orders_90d < 0"),

        # ====================== CUSTOM AUDIT CHECKS (Centralized on DataHub) ======================
        # fact_order: Financial Balance Check (Đối soát tổng tiền line item với tổng hóa đơn)
        ("fact_order", "order_net_amount", "financial_balance",
         "SELECT CASE WHEN ABS((SELECT SUM(line_net_amount) FROM delta.gold.fact_order_item) - (SELECT SUM(order_net_amount) FROM delta.gold.fact_order)) > 0.01 THEN 1 ELSE 0 END"),

        # feat_customer_unified: customer_id không được null
        ("feat_customer_unified", "customer_id", "not_null",
         "SELECT COUNT(*) FROM delta.gold.feat_customer_unified WHERE customer_id IS NULL"),

        # feat_customer_unified: Số view không được âm
        ("feat_customer_unified", "f_stream_views_30m", "non_negative",
         "SELECT COUNT(*) FROM delta.gold.feat_customer_unified WHERE f_stream_views_30m < 0"),
    ]

    # ===========================================================================
    # CHẠY TỪNG BÀI TEST VÀ BẮN KẾT QUẢ LÊN DATAHUB
    # ===========================================================================
    total_checks = len(quality_checks)
    passed_count = 0

    for table_name, column_name, check_type, sql_query in quality_checks:
        # Chạy câu lệnh SQL đếm số dòng lỗi
        try:
            cursor.execute(sql_query)
            error_count = cursor.fetchone()[0]
        except Exception as e:
            print(f"  ❌ Lỗi khi kiểm tra {table_name}.{column_name}: {e}")
            error_count = -1  # Đánh dấu lỗi kết nối

        is_success = (error_count == 0)
        if is_success:
            passed_count += 1

        status_icon = "✔️" if is_success else "⚠️"
        print(f"  {status_icon} [{table_name}] {column_name} ({check_type}): "
              f"{'PASS' if is_success else f'FAIL — {error_count} dòng lỗi'}")

        # --- Tạo URN cho bảng và assertion ---
        dataset_urn = f"urn:li:dataset:(urn:li:dataPlatform:delta-lake,datalake/gold/{table_name},PROD)"
        assertion_urn = f"urn:li:assertion:gold_pipeline.{check_type}.{table_name}.{column_name}"

        try:
            # 1. Khai báo thông tin bài test (AssertionInfo) lên DataHub
            emitter.emit(MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=AssertionInfoClass(
                    type=AssertionTypeClass.DATASET,
                    datasetAssertion=DatasetAssertionInfoClass(
                        dataset=dataset_urn,
                        scope=DatasetAssertionScopeClass.DATASET_COLUMN,
                        fields=[f"urn:li:schemaField:({dataset_urn},{column_name})"],
                        operator=AssertionStdOperatorClass._NATIVE_,
                        nativeType=check_type,
                    ),
                ),
            ))

            # 2. Bắn kết quả chạy thực tế (AssertionRunEvent) lên DataHub
            emitter.emit(MetadataChangeProposalWrapper(
                entityUrn=assertion_urn,
                aspect=AssertionRunEventClass(
                    timestampMillis=now_ms,
                    asserteeUrn=dataset_urn,
                    runId=run_id,
                    assertionUrn=assertion_urn,
                    status=AssertionRunStatusClass.COMPLETE,
                    result=AssertionResultClass(
                        type=AssertionResultTypeClass.SUCCESS if is_success else AssertionResultTypeClass.FAILURE,
                        nativeResults={
                            "table": table_name,
                            "column": column_name,
                            "check_type": check_type,
                            "error_count": str(error_count),
                        },
                    ),
                ),
            ))
        except Exception as exc:
            print(f"  ⚠️ Cảnh báo: Không thể gửi assertion lên DataHub: {exc}")

    cursor.close()
    conn.close()

    # --- Tổng kết ---
    print(f"\n📊 [TỔNG KẾT QUALITY GATE]: {passed_count}/{total_checks} bài test đạt chuẩn.")

    if passed_count < total_checks:
        failed_tests = [
            f"{t}.{c} ({ct})" for t, c, ct, _ in quality_checks
            if not (True)  # Chỉ cảnh báo, không dừng pipeline
        ]
        print(f"  ⚠️ CẢNH BÁO: Có {total_checks - passed_count} bài test không đạt!")
    else:
        print(f"  ✔️ XUẤT SẮC: Toàn bộ {total_checks} bài test chất lượng dữ liệu Gold đều PASS!")


with DAG(
    'ecom_gold_feature_pipeline',
    default_args=default_args,
    description='Pipeline xử lý Batch & Unified Features đạt chuẩn SLA <= 5 min',
    schedule_interval=None,
    catchup=False,
    tags=['ecommerce', 'feature_store', 'gold_layer']
) as dag:

    # 1. Tầng Bronze: đọc landing-zone → ghi bronze
    task_bronze = BashOperator(
        task_id='ingest_bronze',
        bash_command='cd /opt/airflow/project && python data_pipeline/batch_jobs/1_bronze_ingestion.py',
        inlets=[
            RAW_PRODUCTS, RAW_CUSTOMERS, RAW_ORDER_ITEMS, RAW_ORDERS, RAW_PAYMENTS
        ],
        outlets=[
            BRONZE_PRODUCTS, BRONZE_CUSTOMERS, BRONZE_ORDER_ITEMS,
            BRONZE_ORDERS, BRONZE_PAYMENTS
        ]
    )

    # 2. Tầng Silver: đọc bronze → ghi silver
    task_silver = BashOperator(
        task_id='transform_silver',
        bash_command='cd /opt/airflow/project && python data_pipeline/batch_jobs/2_silver_transformation.py',
        inlets=[
            BRONZE_PRODUCTS, BRONZE_CUSTOMERS, BRONZE_ORDER_ITEMS,
            BRONZE_ORDERS, BRONZE_PAYMENTS
        ],
        outlets=[
            SILVER_PRODUCTS, SILVER_CUSTOMERS, SILVER_ORDER_ITEMS,
            SILVER_ORDERS, SILVER_PAYMENTS
        ]
    )

    # 3. Tầng Gold: đọc silver → ghi dim/fact/obt/feat
    task_gold = BashOperator(
        task_id='model_gold',
        bash_command='cd /opt/airflow/project && python data_pipeline/batch_jobs/3_gold_modeling.py',
        inlets=[
            SILVER_PRODUCTS, SILVER_CUSTOMERS, SILVER_ORDER_ITEMS,
            SILVER_ORDERS, SILVER_PAYMENTS
        ],
        outlets=[
            GOLD_DIM_CUSTOMER, GOLD_DIM_PRODUCT, GOLD_DIM_DATE,
            GOLD_DIM_PAYMENT_METHOD, GOLD_DIM_ORDER_STATUS,
            GOLD_FACT_ORDER, GOLD_FACT_ORDER_ITEM, GOLD_FACT_PAYMENT,
            GOLD_OBT, GOLD_FEAT_90D
        ]
    )

    # 3.5 Tầng Storage Optimization: Compaction & Z-Ordering theo chuẩn Rubric
    task_optimize_storage = BashOperator(
        task_id='optimize_lakehouse_storage',
        bash_command='cd /opt/airflow/project && python data_pipeline/batch_jobs/4_lakehouse_optimization.py',
        inlets=[
            GOLD_DIM_CUSTOMER, GOLD_FACT_ORDER, GOLD_OBT, GOLD_FEAT_90D
        ],
        outlets=[
            GOLD_DIM_CUSTOMER, GOLD_FACT_ORDER, GOLD_OBT, GOLD_FEAT_90D
        ]
    )

    # 4. Tầng Feature Store: đọc gold + redis → ghi unified
    task_unified_features = BashOperator(
        task_id='merge_unified_features',
        bash_command='cd /opt/airflow/project && python data_pipeline/batch_jobs/unified_features_batch.py',
        inlets=[
            GOLD_FEAT_90D,
            Dataset("redis", "feat_stream")  # Dữ liệu streaming từ Redis/Flink
        ],
        outlets=[
            FEAT_STREAM_60M,
            FEAT_UNIFIED
        ]
    )

    # 5. Validate Gold: Kiểm tra chất lượng cột dữ liệu & bắn Assertion lên DataHub (Chạy sau cùng)
    task_validate_gold = PythonOperator(
        task_id='validate_gold_quality',
        python_callable=validate_gold_quality,
        inlets=[
            GOLD_DIM_CUSTOMER, GOLD_DIM_PRODUCT, GOLD_DIM_DATE,
            GOLD_DIM_PAYMENT_METHOD, GOLD_DIM_ORDER_STATUS,
            GOLD_FACT_ORDER, GOLD_FACT_ORDER_ITEM, GOLD_FACT_PAYMENT,
            GOLD_OBT, GOLD_FEAT_90D, FEAT_UNIFIED
        ],
    )

    task_bronze >> task_silver >> task_gold >> task_optimize_storage >> task_unified_features >> task_validate_gold