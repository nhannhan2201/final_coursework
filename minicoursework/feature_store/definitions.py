from datetime import timedelta
from feast import Entity, FeatureView, Field, PushSource
from feast.types import Int64, Float32, String, Array
from feast.infra.offline_stores.contrib.delta_offline_store.delta_source import DeltaSource

# 1. Định nghĩa Khóa chính chung
customer = Entity(name="customer", join_keys=["customer_id"])

# ==============================================================================
# KHAI BÁO NHÁNH 1: STREAM FEATURE (60 PHÚT)
# ==============================================================================
stream_offline_source = DeltaSource(
    path="s3a://datalake/gold/feat_stream",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_ts"
)
stream_push_source = PushSource(name="stream_push_source", batch_source=stream_offline_source)

feat_stream_view = FeatureView(
    name="feat_stream",
    entities=[customer],
    ttl=timedelta(hours=2), 
    schema=[
        Field(name="f_stream_views_30m", dtype=Int64),
        Field(name="f_stream_add_to_cart_30m", dtype=Int64),
        Field(name="f_stream_cart_to_purchase_ratio_60m", dtype=Float32),
    ],
    source=stream_push_source,
    online=True # THẰNG NÀY ĐỂ TRÊN REDIS
)

# ==============================================================================
# KHAI BÁO NHÁNH 2: BATCH FEATURE (90 NGÀY) - BỔ SUNG CHO BẠN RÕ ĐỂ KHÔNG BỊ CẤN
# ==============================================================================
batch_offline_source = DeltaSource(
    path="s3a://datalake/gold/feat_customer_90d",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_ts"
)

feat_customer_90d_view = FeatureView(
    name="feat_customer_90d",
    entities=[customer],
    ttl=timedelta(days=90),
    schema=[
        Field(name="f_customer_total_orders_90d", dtype=Int64),
        Field(name="f_customer_avg_order_value_90d", dtype=Float32),
        Field(name="f_customer_distinct_categories_90d", dtype=Int64),
    ],
    source=batch_offline_source,
    online=False # THẰNG NÀY CHỈ CẦN NẰM Ở MINIO ĐỂ TRAIN, KHÔNG CẦN ĐẨY LÊN RAM REDIS
)

# ==============================================================================
# KHAI BÁO NHÁNH 3: RAG VECTOR CHUNKS FEATURE (ONLINE + OFFLINE)
# ==============================================================================
chunk = Entity(name="chunk", join_keys=["chunk_id"])

rag_offline_source = DeltaSource(
    path="s3a://datalake/gold/rag_chunks",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_ts"
)
rag_push_source = PushSource(name="rag_push_source", batch_source=rag_offline_source)

feat_rag_chunks_view = FeatureView(
    name="feat_rag_chunks",
    entities=[chunk],
    ttl=timedelta(days=365),
    schema=[
        Field(name="doc_id", dtype=String),
        Field(name="title", dtype=String),
        Field(name="category", dtype=String),
        Field(name="chunk_text", dtype=String),
        Field(name="vector_dim", dtype=Int64),
        Field(name="vector_embedding", dtype=Array(Float32)), # 384D Vector Embeddings
    ],
    source=rag_push_source,
    online=True
)