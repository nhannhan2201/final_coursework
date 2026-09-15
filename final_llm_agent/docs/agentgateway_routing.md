# 🌐 AI Gateway Routing & Policy — Envoy AgentGateway Report

Tài liệu báo cáo chi tiết cấu hình cổng **AI Gateway** sử dụng **Envoy AgentGateway** theo chuẩn **Kubernetes Gateway API v1**, quản lý định tuyến lưu lượng suy luận LLM, tích hợp **Gateway API Inference Extension (GAIE)** và chính sách xuất telemetry phân tán.

---

## 🏛️ 1. Kiến Trúc AI Gateway Trên Kubernetes

Thay vì sử dụng Ingress Controller truyền thống (chỉ định tuyến HTTP/Layer 7 đơn giản), dự án triển khai giải pháp **Envoy AgentGateway** chuyên biệt cho các khối lượng công việc AI/LLM:

- **Gateway Controller (`agentgateway-system`):** Quản lý trạng thái và sinh cấu hình xDS động đẩy tới proxy.
- **Inference Gateway Proxy (`llm-d-quickstart`):** Pod Envoy Proxy tiếp nhận toàn bộ yêu cầu từ các Agent, mở cổng `:80` (ClusterIP) và NodePort `:32257`.
- **HTTPRoute (`optimized-baseline`):** Khai báo quy tắc định tuyến các yêu cầu `/v1/chat/completions` tới `InferencePool`.

```
[ Multi-Agents in ns: kagent ] 
             │
             ▼ (HTTP POST /v1/chat/completions :80)
┌─────────────────────────────────────────────────────────────┐
│  Gateway: llm-d-inference-gateway (agentgateway Proxy)      │
│  Namespace: llm-d-quickstart (Port :80 / NodePort :32257)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼ (gRPC ext-proc)               ▼ (HTTP Forward)
      [ llm-d Router EPP ]            [ vLLM decode Pod ]
    (KV-cache Affinity Probe)       (Qwen2.5-Coder-0.5B :8000)
```

---

## ⚙️ 2. Khai Báo Gateway & HTTPRoute

### 2.1. Cấu Hình Gateway Resource
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: llm-d-inference-gateway
  namespace: llm-d-quickstart
spec:
  gatewayClassName: agentgateway
  listeners:
  - name: http
    port: 80
    protocol: HTTP
    allowedRoutes:
      namespaces:
        from: All
```

### 2.2. Khai Báo HTTPRoute Tới InferencePool
Tệp định tuyến chuyển tiếp các yêu cầu suy luận mô hình tới `InferencePool: optimized-baseline`:
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: optimized-baseline
  namespace: llm-d-quickstart
spec:
  parentRefs:
  - name: llm-d-inference-gateway
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - group: inference.networking.k8s.io
      kind: InferencePool
      name: optimized-baseline
      port: 8000
```

---

## 🛡️ 3. Chính Sách AgentgatewayPolicy (Telemetry & Tracing)

Chính sách `AgentgatewayPolicy` ([agentic_ai/agentgateway_policy.yaml](file:///home/nhan/Projects/final_coursework/final_llm_agent/agentic_ai/agentgateway_policy.yaml)) được áp dụng trực tiếp lên Gateway để thu thập toàn bộ spans suy luận LLM:

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayPolicy
metadata:
  name: llm-d-inference-policy
  namespace: llm-d-quickstart
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: llm-d-inference-gateway
  tracing:
    openTelemetry:
      endpoint: opentelemetry-collector.monitoring.svc.cluster.local:4317
      serviceName: llm-d-inference-gateway
      samplingRate: 100
      capturePrompt: true
      captureCompletion: true
```

* **Lợi ích:**
  1. Tự động trích xuất số lượng `prompt_tokens`, `completion_tokens`, độ trễ TTFT (Time to First Token) và round-trip latency.
  2. Xuất dữ liệu qua OTLP gRPC `:4317` về `opentelemetry-collector` để chuyển tiếp lên Jaeger và Langfuse Cloud.

---

## 💻 4. Lệnh Kiểm Tra Hoạt Động Của Gateway

```bash
# 1. Kiểm tra trạng thái Gateway (PROGRAMMED: True)
kubectl get gateway -n llm-d-quickstart

# 2. Kiểm tra HTTPRoute đã bind vào Gateway
kubectl get httproute -n llm-d-quickstart

# 3. Test gửi prompt suy luận qua Gateway NodePort (:32257) hoặc Port-Forward (:8880)
curl -s -X POST http://localhost:8880/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
    "messages": [{"role": "user", "content": "Hello! Say test OK"}],
    "max_tokens": 10
  }' | jq .
```
Kết quả trả về JSON phản hồi trực tiếp từ Pod `vLLM decode` qua sự điều phối của `llm-d Router EPP`.
