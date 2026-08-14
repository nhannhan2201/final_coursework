import yaml
import pandas as pd
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Chỉ Import các hàm sinh dữ liệu tĩnh lịch sử
from src.generate_base_info import generate_customers, generate_products, generate_customer_labels
from src.generate_sale_history import generate_sales_data

# ==============================================================================
# CẤU HÌNH KẾT NỐI MINIO (S3 COMPATIBLE)
# ==============================================================================
import os
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9005")
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password123"
LANDING_ZONE_BUCKET = "landing-zone"

def setup_minio_buckets():
    """Tự động tạo bucket landing-zone và datalake nếu chưa có trên MinIO"""
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY
    )
    
    for bucket in [LANDING_ZONE_BUCKET, 'datalake']:
        try:
            s3_client.head_bucket(Bucket=bucket)
        except ClientError:
            s3_client.create_bucket(Bucket=bucket)
            print(f"🪣 [HỆ THỐNG] Đã khởi tạo bucket mới trên MinIO: {bucket}")

def save_to_minio_parquet(df, table_name, partition_cols=None):
    """Hàm lưu DataFrame thành Parquet bắn thẳng lên S3 (MinIO)"""
    s3_path = f"s3://{LANDING_ZONE_BUCKET}/{table_name}"
    
    # Cấu hình khóa để Pandas/PyArrow mở cửa được MinIO
    storage_options = {
        "key": MINIO_ACCESS_KEY,
        "secret": MINIO_SECRET_KEY,
        "client_kwargs": {"endpoint_url": MINIO_ENDPOINT}
    }
    
    if partition_cols:
        df.to_parquet(s3_path, index=False, engine='pyarrow', partition_cols=partition_cols, storage_options=storage_options)
    else:
        # Lưu thành 1 file data.parquet duy nhất bên trong folder s3_path
        file_path = f"{s3_path}/data.parquet"
        df.to_parquet(file_path, index=False, engine='pyarrow', storage_options=storage_options)
    
    print(f"☁️ [LANDING ZONE] Đã bay lên Cloud thành công: {table_name} tại {s3_path}")

def main():
    print("==================================================")
    print("⚡ KHỞI ĐỘNG LUỒNG SINH DỮ LIỆU BATCH LÊN CLOUD")
    print("==================================================")
    
    print("\n⚙️ Bước 0: Chuẩn bị không gian hạ tầng trên MinIO...")
    setup_minio_buckets()

    # 1. Đọc cấu hình từ file YAML
    with open('config/generator_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        if isinstance(config['schema_change_date'], str):
           config['schema_change_date'] = datetime.strptime(config['schema_change_date'], "%Y-%m-%d")

    print("\n⚙️ Bước 1: Khởi tạo thông tin cơ sở Customers & Products...")
    customers_df = generate_customers(config['n_customers'], config['skew_ratio_city'], config['random_seed'])
    products_df = generate_products(config['n_products'], config['skew_ratio_category'], config['random_seed'])
    
    print("\n⚙️ Bước 1b: Sinh bảng nhãn Churn (Label Table) 2 cột cho ML...")
    churn_rate = config.get('churn_rate', 0.18)
    labels_df = generate_customer_labels(customers_df, churn_rate, config['random_seed'])

    print("\n⚙️ Bước 2: Tạo lịch sử mua bán 90 ngày tích lũy (Có Data Drift)...")
    df_orders, df_items, df_payments = generate_sales_data(customers_df, products_df, config)

    print("\n⚙️ Bước 3: Đẩy dữ liệu thẳng lên Landing Zone (MinIO)...")
    save_to_minio_parquet(customers_df, 'customers')
    save_to_minio_parquet(products_df, 'products')
    save_to_minio_parquet(labels_df, 'customer_labels')  # 🏷️ Đẩy bảng nhãn ML lên MinIO
    
    # Chia phân vùng theo ngày cho Orders và Payments
    df_orders['order_date'] = df_orders['order_ts'].dt.date
    save_to_minio_parquet(df_orders, 'orders', partition_cols=['order_date'])
    
    save_to_minio_parquet(df_items, 'order_items')
    
    df_payments['payment_date'] = df_payments['payment_timestamp'].dt.date
    save_to_minio_parquet(df_payments, 'payments', partition_cols=['payment_date'])

    print("\n==================================================")
    print("🎉 [HOÀN TẤT] DỮ LIỆU CÓ DRIFT & LABEL ĐÃ NẰM TRÊN CLOUD SẴN SÀNG CHO SPARK!")
    print("==================================================")

if __name__ == "__main__":
    main()