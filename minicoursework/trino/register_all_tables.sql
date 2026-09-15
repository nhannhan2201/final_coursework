-- ==============================================================================
-- ĐĂNG KÝ TOÀN BỘ DELTA TABLES VÀO TRINO QUA HIVE METASTORE
-- Chạy trong Trino CLI hoặc DBeaver (kết nối Trino JDBC)
-- ==============================================================================

-- ========== 1. TẠO SCHEMAS (tương ứng 3 tầng Lakehouse) ==========
CREATE SCHEMA IF NOT EXISTS delta.bronze   WITH (location = 's3a://datalake/bronze/');
CREATE SCHEMA IF NOT EXISTS delta.silver   WITH (location = 's3a://datalake/silver/');
CREATE SCHEMA IF NOT EXISTS delta.gold     WITH (location = 's3a://datalake/gold/');

-- ========== 2. ĐĂNG KÝ BẢNG BRONZE (5 bảng) ==========
CALL delta.system.register_table(schema_name => 'bronze', table_name => 'raw_products',         table_location => 's3a://datalake/bronze/raw_products');
CALL delta.system.register_table(schema_name => 'bronze', table_name => 'raw_customers',        table_location => 's3a://datalake/bronze/raw_customers');
CALL delta.system.register_table(schema_name => 'bronze', table_name => 'raw_order_items',      table_location => 's3a://datalake/bronze/raw_order_items');
CALL delta.system.register_table(schema_name => 'bronze', table_name => 'raw_orders',           table_location => 's3a://datalake/bronze/raw_orders');
CALL delta.system.register_table(schema_name => 'bronze', table_name => 'raw_payment_attempts', table_location => 's3a://datalake/bronze/raw_payment_attempts');

-- ========== 3. ĐĂNG KÝ BẢNG SILVER (5 bảng) ==========
CALL delta.system.register_table(schema_name => 'silver', table_name => 'stg_products',          table_location => 's3a://datalake/silver/stg_products');
CALL delta.system.register_table(schema_name => 'silver', table_name => 'stg_customers',         table_location => 's3a://datalake/silver/stg_customers');
CALL delta.system.register_table(schema_name => 'silver', table_name => 'stg_order_items',       table_location => 's3a://datalake/silver/stg_order_items');
CALL delta.system.register_table(schema_name => 'silver', table_name => 'stg_orders',            table_location => 's3a://datalake/silver/stg_orders');
CALL delta.system.register_table(schema_name => 'silver', table_name => 'stg_payment_attempts',  table_location => 's3a://datalake/silver/stg_payment_attempts');

-- ========== 4. ĐĂNG KÝ BẢNG GOLD — DIMENSIONS (5 bảng) ==========
CALL delta.system.register_table(schema_name => 'gold', table_name => 'dim_customer',        table_location => 's3a://datalake/gold/dim_customer');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'dim_product',         table_location => 's3a://datalake/gold/dim_product');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'dim_date',            table_location => 's3a://datalake/gold/dim_date');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'dim_payment_method',  table_location => 's3a://datalake/gold/dim_payment_method');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'dim_order_status',    table_location => 's3a://datalake/gold/dim_order_status');

-- ========== 5. ĐĂNG KÝ BẢNG GOLD — FACTS (3 bảng) ==========
CALL delta.system.register_table(schema_name => 'gold', table_name => 'fact_order',             table_location => 's3a://datalake/gold/fact_order');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'fact_order_item',        table_location => 's3a://datalake/gold/fact_order_item');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'fact_payment_attempt',   table_location => 's3a://datalake/gold/fact_payment_attempt');

-- ========== 6. ĐĂNG KÝ BẢNG GOLD — OBT (1 bảng) ==========
CALL delta.system.register_table(schema_name => 'gold', table_name => 'obt_order_performance',  table_location => 's3a://datalake/gold/obt_order_performance');

-- ========== 7. ĐĂNG KÝ BẢNG GOLD — FEATURE STORE (3 bảng) ==========
CALL delta.system.register_table(schema_name => 'gold', table_name => 'feat_customer_90d',      table_location => 's3a://datalake/gold/feat_customer_90d');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'feat_stream_60m',        table_location => 's3a://datalake/gold/feat_stream_60m');
CALL delta.system.register_table(schema_name => 'gold', table_name => 'feat_customer_unified',  table_location => 's3a://datalake/gold/feat_customer_unified');
