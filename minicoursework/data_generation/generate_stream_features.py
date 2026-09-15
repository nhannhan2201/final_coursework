#!/usr/bin/env python3
"""
Script nạp dữ liệu Streaming Features thời gian thực vào Redis Feature Store (Port 6379).
Phục vụ trực tiếp cho FastMCP Tool (ecom-mcp) khi truy vấn hồ sơ khách hàng (VD: CUST_000001).
"""
import random
import sys
from datetime import datetime

try:
    import redis
except ImportError:
    print("❌ Lỗi: Thiếu thư viện redis. Cài đặt bằng: pip install redis")
    sys.exit(1)

REDIS_HOST = "localhost"
REDIS_PORT = 6379

def main():
    print(f"⚡ Đang kết nối tới Redis Feature Store tại {REDIS_HOST}:{REDIS_PORT}...")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
    except Exception as e:
        print(f"❌ Không thể kết nối tới Redis: {e}")
        print("💡 Hãy đảm bảo bạn đã chạy: docker compose up -d tại thư mục minicoursework")
        sys.exit(1)

    print("🚀 Đang sinh và nạp dữ liệu Streaming Feature cho 100 khách hàng mẫu (CUST_000001 -> CUST_000100)...")
    pipeline = r.pipeline()
    for i in range(1, 101):
        cust_id = f"CUST_{i:06d}"
        key = f"feat_stream:{cust_id}"
        
        # CUST_000001 được gán giá trị đẹp để demo test
        if i == 1:
            views_30m = 15
            cart_30m = 4
            ratio_60m = 0.45
        else:
            views_30m = random.randint(2, 30)
            cart_30m = random.randint(0, 8)
            ratio_60m = round(random.uniform(0.05, 0.90), 4)

        pipeline.hset(key, mapping={
            "f_stream_views_30m": str(views_30m),
            "f_stream_add_to_cart_30m": str(cart_30m),
            "f_stream_cart_to_purchase_ratio_60m": str(ratio_60m),
            "event_timestamp": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        pipeline.expire(key, 86400) # TTL 24h

    pipeline.execute()
    print("✅ Đã nạp thành công 100 hồ sơ Streaming Feature vào Redis!")
    print(f"🔍 Kiểm tra thử khách hàng CUST_000001: {r.hgetall('feat_stream:CUST_000001')}")

if __name__ == "__main__":
    main()
