# 📋 Centralized Logging & Distributed Tracing Report

Báo cáo triển khai hệ thống thu thập log tập trung (Centralized Logging) bằng **EFK Stack** (Elasticsearch + Fluent Bit + Kibana) và hệ thống theo dõi luồng yêu cầu phân tán (Distributed Tracing) bằng **Jaeger + OpenTelemetry**.

---

## 📝 1. Centralized Logging — EFK Stack (Kibana)

### Kiến Trúc
- **Fluent Bit (DaemonSet):** Chạy trên mọi node trong cluster, tự động thu thập logs từ tất cả containers (stdout/stderr) thông qua đường dẫn `/var/log/containers/*.log`.
- **Elasticsearch (StatefulSet):** Lưu trữ và đánh chỉ mục (index) logs dạng Logstash format (`k8s-logs-YYYY.MM.DD`).
- **Kibana (Deployment):** Giao diện trực quan để tìm kiếm, lọc và phân tích logs theo thời gian thực.

### Triển Khai
```bash
kubectl apply -f deployments/efk_logging.yaml

# Port-forward để truy cập Kibana UI
kubectl port-forward -n logging svc/kibana 5601:5601
# Truy cập: http://localhost:5601
```

> 📸 **MINH CHỨNG KIBANA LOGGING:**
> *Hãy chụp màn hình giao diện Kibana Discover hiển thị logs từ các pods feature-api, drift-api, ecom-mcp, drift-mcp.*
>
> **🖼️ Ảnh minh chứng:**
> *(Dán ảnh vào dòng này)*

---

## 🔍 2. Distributed Tracing — Jaeger + OpenTelemetry

### Kiến Trúc
- **OpenTelemetry Collector (Deployment):** Nhận traces từ các ứng dụng (FastAPI, MCP Servers) qua giao thức OTLP (gRPC/HTTP) và chuyển tiếp tới Jaeger.
- **Jaeger All-in-One (Deployment):** Lưu trữ và trực quan hóa toàn bộ distributed traces, hiển thị latency breakdown cho từng span trong chuỗi xử lý request.

### Chuỗi Trace Điển Hình
```
User Request → Ingress Gateway → Feature API → Redis/Trino
                                              → MCP Server → Agent → LLM Inference
```

### Triển Khai
```bash
kubectl apply -f deployments/jaeger_tracing.yaml

# Port-forward để truy cập Jaeger UI
kubectl port-forward -n tracing svc/jaeger 16686:16686
# Truy cập: http://localhost:16686
```

### Cấu Hình Ứng Dụng Gửi Traces
Các ứng dụng FastAPI (`feature_api.py`, `drift_api.py`) sử dụng module `apps/telemetry.py` đã tích hợp sẵn OpenTelemetry Instrumentation. Chỉ cần thiết lập biến môi trường trỏ tới OTel Collector:

```yaml
env:
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "http://otel-collector.tracing.svc.cluster.local:4317"
- name: OTEL_SERVICE_NAME
  value: "feature-api"  # hoặc "drift-api"
```

> 📸 **MINH CHỨNG JAEGER TRACING:**
> *Hãy chụp màn hình giao diện Jaeger UI hiển thị distributed trace của một request đi qua Feature API → Redis → Trino, thể hiện latency breakdown cho từng span.*
>
> **🖼️ Ảnh minh chứng:**
> *(Dán ảnh vào dòng này)*
