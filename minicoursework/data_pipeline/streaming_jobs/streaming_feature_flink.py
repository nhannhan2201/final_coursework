import json
import redis
from datetime import datetime
from pyflink.common import Types, WatermarkStrategy, Time
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.datastream.formats.json import JsonRowDeserializationSchema
from pyflink.datastream.window import SlidingEventTimeWindows
from pyflink.datastream.functions import ProcessWindowFunction
from pyflink.common import Duration

# ==============================================================================
# 1. KHỞI TẠO MÔI TRƯỜNG FLINK
# ==============================================================================
env = StreamExecutionEnvironment.get_execution_environment()

# Thêm gói JAR kết nối Kafka (Hãy đảm bảo bạn đã tải file này về hoặc cấu hình đúng)
env.add_jars("file:////home/nhan/Projects/minicoursework/jars/flink-sql-connector-kafka-1.17.1.jar")


# ==============================================================================
# 2. CẮM VÒI VÀO KAFKA HỨNG CLICKSTREAM VÀ GẮN WATERMARK 45 PHÚT
# ==============================================================================
schema = Types.ROW_NAMED(
    ["event_id", "event_type", "event_timestamp", "created_ts", "customer_id", "device_type", "product_id"],
    [Types.STRING(), Types.STRING(), Types.STRING(), Types.STRING(), Types.STRING(), Types.STRING(), Types.STRING()]
)

import os
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

kafka_source = KafkaSource.builder() \
    .set_bootstrap_servers(KAFKA_SERVERS)\
    .set_topics("ecommerce_clickstream") \
    .set_group_id("flink_feature_group") \
    .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
    .set_value_only_deserializer(JsonRowDeserializationSchema.builder().type_info(schema).build()) \
    .build()

# --- NÂNG CẤP PHẦN 2: Watermark Strategy 45 phút cho Late Arrivals (5-45m) ---
stream = env.from_source(
    kafka_source, 
    WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_minutes(45)) \
        .with_idleness(Duration.of_minutes(1)) \
        .with_timestamp_assigner(lambda event, _: int(datetime.fromisoformat(event.event_timestamp).timestamp() * 1000)), 
    "Kafka_Clickstream_Source"
)


# ==============================================================================
# 3. HÀM CỬA SỔ TRƯỢT 60 PHÚT VÀ UPSERT LÊN REDIS (ONLINE STORE)
# ==============================================================================
class FeatureAggregator(ProcessWindowFunction):
    def process(self, key, context, elements):
        customer_id = key
        views_30m = carts_30m = carts_60m = purchases_60m = 0
        
        window_end_ms = context.window().end
        threshold_30m_ms = window_end_ms - (30 * 60 * 1000)

        # --- NÂNG CẤP PHẦN 2: Khử trùng lặp sự kiện (1.5% Duplicates) bằng Set theo event_id trong Window ---
        seen_events = set()

        for event in elements:
            # Nếu event_id đã xử lý trong window này -> Bỏ qua (Drop duplicate)
            if event.event_id in seen_events:
                continue
            seen_events.add(event.event_id)

            event_ts = int(datetime.fromisoformat(event.event_timestamp).timestamp() * 1000)
            
            # Tính cho khung 30 phút
            if event_ts >= threshold_30m_ms:
                if event.event_type == 'view': views_30m += 1
                elif event.event_type == 'add_to_cart': carts_30m += 1
            
            # Tính cho khung 60 phút
            if event.event_type == 'add_to_cart': carts_60m += 1
            elif event.event_type == 'purchase': purchases_60m += 1

        # Tránh lỗi chia cho 0
        ratio_60m = round(float(purchases_60m) / (purchases_60m + carts_60m), 4) if (carts_60m > 0 or purchases_60m > 0) else 0.0

        # Ghi trực tiếp lên Redis
        try:
            r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)
            feature_dict = {
                "f_stream_views_30m": views_30m,
                "f_stream_add_to_cart_30m": carts_30m,
                "f_stream_cart_to_purchase_ratio_60m": ratio_60m,
                "event_timestamp": datetime.fromtimestamp(window_end_ms/1000).isoformat(),
                "created_ts": datetime.now().isoformat()
            }
            redis_key = f"feat_stream:{customer_id}"
            r.hset(redis_key, mapping=feature_dict)
            r.expire(redis_key, 2 * 60 * 60) # Cài đặt TTL 2 tiếng để dọn rác tự động
            
            print(f"⚡ [FLINK -> REDIS] Khách: {customer_id} | Views: {views_30m} | Ratio: {ratio_60m}")
        except Exception as e:
            print(f"❌ Lỗi kết nối Redis: {e}")
            
        return [(customer_id, views_30m, carts_30m, ratio_60m)]

# ==============================================================================
# 4. CHẠY PIPELINE THỜI GIAN THỰC
# ==============================================================================
# --- NÂNG CẤP PHẦN 2: Thêm allowed_lateness(45m) để cứu dữ liệu đến muộn sau khi cửa sổ đóng ---
stream.key_by(lambda x: x.customer_id, key_type=Types.STRING()) \
    .window(SlidingEventTimeWindows.of(Time.minutes(60), Time.minutes(5))) \
    .allowed_lateness(Time.minutes(45)) \
    .process(FeatureAggregator(), Types.TUPLE([Types.STRING(), Types.INT(), Types.INT(), Types.FLOAT()]))

print("🌪️ [HỆ THỐNG] FLINK ĐANG LẮNG NGHE KAFKA VÀ BẮN DỮ LIỆU LÊN REDIS (ĐÃ TỐI ƯU WATERMARK 45M & DEDUPLICATION)...")
env.execute("Flink_Realtime_Features")