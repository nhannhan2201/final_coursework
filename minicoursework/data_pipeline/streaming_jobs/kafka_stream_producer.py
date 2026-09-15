import json
import time
import random
import uuid
import yaml
import os
from datetime import datetime, timedelta
from kafka import KafkaProducer
import pandas as pd

# ==============================================================================
# CẤU HÌNH HỆ THỐNG TỪ FILE YAML (Single Source of Truth)
# ==============================================================================
config_path = "config/generator_config.yaml"
if not os.path.exists(config_path):
    config_path = "data_generation/config/generator_config.yaml"

if not os.path.exists(config_path):
    raise FileNotFoundError(f"Không tìm thấy file config tại: {config_path}")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)

if 'base_sleep_range' not in config:
    config['base_sleep_range'] = [0.5, 2.0]

import os
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9005")
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Khởi tạo kết nối đến nhà ga Kafka
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_SERVERS],
    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
)

TOPIC_NAME = 'ecommerce_clickstream'

def generate_streaming_data_to_kafka():
    print(f"\n🚀 [PRODUCER] Bắt đầu mô phỏng luồng Clickstream thời gian thực vào '{TOPIC_NAME}'...")
    print("👉 Bấm Ctrl+C trên Terminal để dừng.\n")

    # ==============================================================================
    # [QUAN TRỌNG] ĐỌC ID THẬT TỪ LANDING-ZONE ĐỂ JOIN KHÔNG BỊ TRỐNG
    # ==============================================================================
    print("⏳ Đang nạp danh sách Khách hàng và Sản phẩm từ Cloud (MinIO)...")
    try:
        # Cấu hình khóa để pandas có quyền tải data từ MinIO
        storage_options = {
            "key": "admin",
            "secret": "password123",
            "client_kwargs": {"endpoint_url": MINIO_ENDPOINT}
        }
        
        customers_df = pd.read_parquet("s3://landing-zone/customers", columns=['customer_id'], storage_options=storage_options)
        products_df = pd.read_parquet("s3://landing-zone/products", columns=['product_id'], storage_options=storage_options)
        
        customer_ids = customers_df['customer_id'].tolist()
        product_ids = products_df['product_id'].tolist()
        
        print(f"✔️ Đã nạp thành công TOÀN BỘ {len(customer_ids)} Khách hàng và {len(product_ids)} Sản phẩm thật!\n")
    except Exception as e:
        print(f"❌ Lỗi khi đọc file trên MinIO: {e}")
        
        customer_ids = [f"CUST_{i:06d}" for i in range(0, config.get('n_customers', 120000))]
        product_ids = [f"{i+1:06d}" for i in range(0, config.get('n_products', 45000))]
        
    try:
        while True: 
            current_time = datetime.now()
            
            # --- 1. Xử lý BURSTS (Tăng tốc độ gửi) ---
            is_burst = False
            for window in config['burst_windows']:
                start_w, end_w = window.split('-')
                if start_w <= current_time.strftime('%H:%M') <= end_w:
                    is_burst = True
                    break

            # Tính toán thời gian click và thời gian hệ thống ghi nhận
            event_ts = current_time
            created_ts = current_time

            # --- 2. Xử lý LATE ARRIVALS (Kéo sự kiện về quá khứ) ---
            status_tag = "Nml " # Normal
            if random.random() < config['late_arrival_rate']:
                delay_minutes = random.randint(config['late_delay_min_max'][0], config['late_delay_min_max'][1])
                # Đẩy thời gian khách hàng thao tác về quá khứ
                event_ts = current_time - timedelta(minutes=delay_minutes)
                status_tag = "Late"

            event_id = str(uuid.uuid4())
            event = {
                'event_id': event_id,
                'event_type': random.choices(
                    ['view', 'add_to_cart', 'checkout', 'purchase'], 
                    weights=[0.6, 0.25, 0.1, 0.05], k=1
                )[0],
                'event_timestamp': event_ts.isoformat(),
                'created_ts': created_ts.isoformat(),
                'customer_id': random.choice(customer_ids),
                'device_type': random.choice(['mobile', 'desktop', 'tablet']),
                'product_id': random.choice(product_ids)
            }
            
            # Gửi sự kiện gốc
            producer.send(TOPIC_NAME, value=event)
            print(f"[{current_time.strftime('%H:%M:%S')}] [{status_tag}] 📦 {event['event_type']:<12} | KH: {event['customer_id']} | SP: {event['product_id']}")

            # --- 3. Xử lý DUPLICATES (Gửi bồi thêm lần nữa) ---
            if random.random() < config['duplicate_rate_stream']:
                dup_event = event.copy()
                dup_event['created_ts'] = (current_time + timedelta(seconds=random.randint(1, 5))).isoformat()
                producer.send(TOPIC_NAME, value=dup_event)
                print(f"[{current_time.strftime('%H:%M:%S')}] [Dup ] ⚠️ TRÙNG LẶP    | KH: {event['customer_id']} | ID: {event_id.split('-')[0]}")

            # --- Tạm nghỉ chờ sự kiện tiếp theo ---
            sleep_time = random.uniform(config['base_sleep_range'][0], config['base_sleep_range'][1])
            if is_burst:
                sleep_time = sleep_time / config['burst_multiplier']
            
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n🛑 Đã nhận lệnh dừng (Ctrl+C). Đang đóng kết nối Kafka...")
        producer.close()
        print("✔️ Đóng an toàn!")

if __name__ == "__main__":
    generate_streaming_data_to_kafka()