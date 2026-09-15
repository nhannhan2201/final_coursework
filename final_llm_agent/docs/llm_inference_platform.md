# 🚀 LLM Inference Platform — llm-d + AgentGateway Deployment & Optimization

Tài liệu hướng dẫn chi tiết về nền tảng phục vụ mô hình ngôn ngữ lớn (**llm-d Model Serving Platform**) trên Kubernetes, tích hợp **vLLM Engine**, **Endpoint Picker (EPP)** và **Envoy AgentGateway**.

---

## 🏛️ 1. Kiến Trúc Model Serving Trên Kubernetes

Hệ thống serving sử dụng giải pháp **llm-d** kết hợp với **Gateway API Inference Extension (GAIE)**:

```
                  [ Agent / KAgent ModelConfig ]
                                │
                                ▼ (HTTP /v1/chat/completions :80)
                [ Gateway: llm-d-inference-gateway ]
                                │
                                ▼ (HTTPRoute)
                   [ InferencePool: optimized-baseline ]
                                │
                ┌───────────────┴───────────────┐
                ▼ (gRPC ext-proc)               ▼ (HTTP Forward)
       [ llm-d Router EPP ]            [ vLLM decode Pod ]
     (KV-Cache Affinity Router)       (Qwen2.5-Coder-0.5B :8000)
```

1. **AI Gateway Proxy (`llm-d-inference-gateway`):** Tiếp nhận toàn bộ lưu lượng suy luận từ các Agent qua cổng `:80` hoặc NodePort `:32257`.
2. **llm-d Router EPP (`optimized-baseline-epp`):** Pod Router tham vấn định tuyến thông minh dựa trên tỷ lệ trùng lặp bộ nhớ đệm KV-cache (Prefix Caching) và độ dài hàng đợi xử lý của từng Pod vLLM.
3. **vLLM Decode (`optimized-baseline-cpu-vllm-decode`):** Pod Model Server chạy mô hình Qwen2.5-Coder-0.5B với bộ nhớ đệm PagedAttention v2.

---

## ⚙️ 2. Tối Ưu Hóa Bộ Nhớ Đệm Với PagedAttention v2

- **PagedAttention v2:** Quản lý bộ nhớ đệm Key-Value (KV-cache) theo cơ chế phân trang (paging) tương tự như bộ nhớ ảo của hệ điều hành, loại bỏ 100% hiện tượng phân mảnh bộ nhớ ngoài (External Fragmentation).
- **Prefix Caching:** Tự động nhận diện và tái sử dụng KV-cache của các System Prompt dùng chung giữa các lượt gọi của Multi-Agent, giảm đáng kể độ trễ sinh từ đầu tiên (TTFT).

---

## 💻 3. Kiểm Tra Sức Khỏe & Thử Nghiệm Suy Luận

```bash
# 1. Kiểm tra trạng thái Pods trong namespace llm-d-quickstart
kubectl get pods -n llm-d-quickstart

# 2. Gửi request suy luận thử nghiệm qua Gateway:
curl -s -X POST http://localhost:8880/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
    "messages": [
      {"role": "system", "content": "You are an AI assistant."},
      {"role": "user", "content": "Ping test!"}
    ],
    "max_tokens": 16
  }' | jq .
```
Phản hồi trả về đạt tốc độ sinh token cao và độ trễ ổn định.