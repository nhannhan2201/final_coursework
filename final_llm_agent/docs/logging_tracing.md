# 📋 Centralized Logging & Distributed Tracing Report

Báo cáo triển khai toàn diện hệ thống thu thập log tập trung (**Centralized Logging**) bằng **ECK Stack** (Elasticsearch + Kibana) và hệ thống theo dõi phân tán (**Distributed Tracing**) bằng **OpenTelemetry SDK + OpenTelemetry Collector + Jaeger UI + Langfuse**.

---

## 📝 1. Centralized Logging — ECK Stack (Elasticsearch & Kibana)

### 1.1. Kiến Trúc Thu Thập Logs Tập Trung
Hệ thống sử dụng mô hình Logging Kubernetes chuẩn quốc tế:
- **OpenTelemetry Python SDK (In-Process LoggingHandler):** Tích hợp trực tiếp tại Gốc Rễ (`Root Logger`) của các tiến trình microservices (`feature-api`, `drift-api`, `ecom-mcp`, `drift-mcp`).
- **OpenTelemetry Collector (`opentelemetry-collector`):** Thu thập toàn bộ logs qua chuẩn OTLP gRPC (`Port 4317`) và xuất tự động sang Elasticsearch (`https://elasticsearch-es-http.monitoring.svc.cluster.local:9200`).
- **Elasticsearch (ECK StatefulSet):** Đóng vai trò Data Store lưu trữ và đánh chỉ mục logs tập trung.
- **Kibana (ECK Deployment):** Cung cấp giao diện trực quan hóa (Kibana Discover) để truy vấn, lọc log theo thời gian thực theo namespace, service, hoặc mức độ log (`INFO`, `WARN`, `ERROR`).

```
[ Pod: feature-api ] ──┐
[ Pod: drift-api   ] ──┼──> [ OTLP gRPC :4317 ] ──> [ OTel Collector ] ──> [ Elasticsearch ] ──> [ Kibana UI :5601 ]
[ Pod: ecom-mcp    ] ──┤
[ Pod: drift-mcp   ] ──┘
```

### 1.2. Hướng Dẫn Triển Khai & Kiểm Tra
```bash
# 1. Cài đặt Elastic Operator & ECK Stack qua Helm
helm repo add elastic https://helm.elastic.co && helm repo update
helm install elastic-operator elastic/eck-operator -n elastic-system --create-namespace
helm install elastic elastic/eck-stack -n monitoring -f observability/helm_charts/kibana/values.yaml

# 2. Kiểm tra trạng thái các Pods trong namespace monitoring
kubectl get pods -n monitoring -l app.kubernetes.io/name=eck-kibana

# 3. Port-forward giao diện Kibana UI
kubectl port-forward -n monitoring svc/elastic-eck-kibana-kb-http 5601:5601
# Truy cập: https://localhost:5601
# User: elastic
# Password: lấy từ secret bằng lệnh:
kubectl get secret elasticsearch-es-elastic-user -n monitoring -o jsonpath='{.data.elastic}' | base64 -d
```

> 📸 **MINH CHỨNG KIBANA LOGGING DISCOVER:**
>
> *(Chèn ảnh chụp màn hình Kibana Discover lọc log theo `service.name: feature-api` hoặc `level: ERROR` tại đây)*
>
> ![Kibana Discover Logs](screenshot_kibana_logging.png)

---

## 🔍 2. Distributed Tracing — OpenTelemetry + Jaeger + Langfuse

### 2.1. Kiến Trúc Distributed Tracing
Để theo dõi độ trễ và luồng gọi phân tán giữa các vi dịch vụ và AI Agent, dự án tích hợp **OpenTelemetry Python SDK** trực tiếp vào mã nguồn microservices và đẩy spans về **Jaeger UI** và **Langfuse**:

```
[ User / Client ]
       │
       ▼ (HTTP Request)
[ FastAPI Web API (feature-api / drift-api) ]
       │  ├─ [ Span: HTTP GET /api/v1/features/customer/{id} ]
       │  ├─ [ Span: redis.get_online_features ] ─────────> [ Redis Online Store (<1ms) ]
       │  └─ [ Span: trino.get_offline_features ] ────────> [ Trino Engine / Delta Lake ]
       │
       ▼ (OTLP gRPC Port 4317)
[ OpenTelemetry Collector ] ──┬──> [ Jaeger Engine ] ──> [ Jaeger Web UI :16686 ]
                              └──> [ Langfuse Web ] ───> [ Langfuse Web UI :3000 ]
```

### 2.2. Khởi Tạo OpenTelemetry SDK Trong Mã Nguồn (`apps/telemetry.py`)
Mã nguồn `apps/telemetry.py` được thiết kế theo đúng chuẩn OpenTelemetry Python SDK:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# 1. Gắn nhãn service.name cho Resource
svc_name = os.getenv("OTEL_SERVICE_NAME", "feature-api")
resource = Resource.create({"service.name": svc_name})
tracer_provider = TracerProvider(resource=resource)

# 2. Xuất Traces qua OTLP gRPC tới OTel Collector
endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://opentelemetry-collector.monitoring.svc.cluster.local:4317")
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))

trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)
```

### 2.3. Tạo Trace Spans Cho Từng Thao Tác Cơ Sở Dữ Liệu
Trong `apps/feature_api.py` và `apps/drift_api.py`, các khối truy xuất Redis và Trino được bao bọc bởi context manager `trace_span`:
```python
# Đo lường thao tác Redis Online Store (<1ms)
with trace_span("redis.get_online_features", {"db.system": "redis", "customer_id": customer_id}):
    raw_data = await redis_client.get(f"customer:{customer_id}")

# Đo lường thao tác Trino Offline Lakehouse
with trace_span("trino.get_offline_features", {"db.system": "trino", "customer_id": customer_id}):
    cursor.execute(f"SELECT * FROM gold.customer_features WHERE customer_id = '{customer_id}'")
```

### 2.4. Triển Khai & Kiểm Tra Traces Trên Jaeger UI
```bash
# 1. Cài đặt Jaeger Tracing qua Helm
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm install jaeger jaegertracing/jaeger -n monitoring

# 2. Port-forward giao diện Jaeger UI
kubectl port-forward -n monitoring svc/jaeger 16686:16686
# Truy cập: http://localhost:16686
```

> 📸 **MINH CHỨNG JAEGER DISTRIBUTED TRACING:**
>
> *(Chèn ảnh chụp màn hình Jaeger UI hiển thị timeline phân tích chi tiết trace span từ API xuống Redis và Trino tại đây)*
>
> ![Jaeger Distributed Traces](screenshot_jaeger_tracing.png)
