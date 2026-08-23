# ⚡ AgentRegistry Deployment & Security Sandboxing Report (aregistry.ai Standard)

Tài liệu này hướng dẫn và minh chứng quy trình cài đặt **AgentRegistry**, cấu hình phân quyền thông qua cơ chế **Sandbox**, triển khai Agent dưới dạng **Multi-Replica (HA)** và kiểm tra giao diện tương tác UI Chat với Agent.

---

## 📌 1. Triển Khai AgentRegistry (aregistry.ai)

Hệ thống **AgentRegistry** được cài đặt thông qua Helm chart chính thức từ `aregistry.ai`. Registry này quản lý vòng đời và làm catalog dịch vụ cho toàn bộ AI Agents và FastMCP Tools trong tổ chức.

```bash
# 1. Cài đặt AgentRegistry Helm Chart
helm upgrade -i agentregistry oci://ghcr.io/agentregistry-dev/agentregistry/charts/agentregistry \
    --namespace agentregistry --create-namespace \
    --set config.jwtPrivateKey=$(openssl rand -hex 32) \
    --set image.tag=v0.3.3 \
    --set database.host=postgres-pgvector.agentregistry.svc.cluster.local \
    --set database.password=agentregistry \
    --set database.sslMode=disable

# 2. Port-forward giao diện AgentRegistry UI
kubectl port-forward -n agentregistry svc/agentregistry 12121:80
# Mở trình duyệt: http://localhost:12121
```

> 📸 **MINH CHỨNG AGENTREGISTRY CATALOG UI:**
>
> *(Chèn ảnh chụp màn hình giao diện AgentRegistry UI hiển thị danh mục các Tools ecom-mcp và drift-mcp tại đây)*
>
> ![AgentRegistry Catalog UI](screenshot_agent_registry.png)

---

## 🛡️ 2. Bảo Mật Sandbox Cho Agent Execution

Mỗi Agent khi được kích hoạt các công cụ (Tools) từ MCP Servers đều chạy trong môi trường **Sandbox** được cô lập nghiêm ngặt ở tầng Kubernetes để tránh việc Agent thực thi các mã độc hại hoặc truy cập tài nguyên trái phép:

1. **Security Context (Phân quyền tối thiểu):**
   - Không chạy dưới quyền root (`runAsNonRoot: true`).
   - Cấm ghi file lên hệ thống gốc (`readOnlyRootFilesystem: true`).
   - Loại bỏ toàn bộ Linux Capabilities không cần thiết (`capabilities.drop: ["ALL"]`).
2. **Network Policies (Cô lập mạng):**
   - Chỉ cho phép Agent gọi các API Backend được chỉ định (như `feature-api` và `drift-api`).
   - Chặn toàn bộ luồng mạng đi ra ngoài Internet công cộng hoặc các Namespaces nhạy cảm khác.

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
  containers:
  - name: agent-runtime
    securityContext:
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

---

## 👥 3. Triển Khai Multi-Replica & KEDA Autoscaling (High Availability)

Để bảo đảm hệ thống có thể đáp ứng hàng ngàn yêu cầu tư vấn đồng thời từ khách hàng, cấu hình **Multi-Replica** và KEDA Autoscaling được áp dụng trực tiếp qua file [apps/deployments/keda_autoscaling.yaml](file:///home/nhan/Projects/final_coursework/final_llm_agent/apps/deployments/keda_autoscaling.yaml):

- Số lượng Pods chạy `feature-api` được cấu hình tối thiểu `minReplicaCount: 1` và tự động giãn nở lên tối đa `maxReplicaCount: 5` khi CPU vượt 70%.

```bash
# Kiểm tra số lượng Pods đang hoạt động đa bản sao:
kubectl get pods -n default
```

> 📸 **MINH CHỨNG MULTI-REPLICA & KEDA AUTOSCALING PODS:**
>
> *(Chèn ảnh chụp màn hình terminal `kubectl get pods -n default` hoặc `kubectl get scaledobject` tại đây)*
>
> ![Multi Replica Pods](screenshot_multi_replica_pods.png)

---

## 💬 4. Trò Chuyện & Tương Tác Với Agent Trên KAgent Chat UI

Người dùng có thể trực tiếp tương tác và đặt câu hỏi cho Agent thông qua giao diện **KAgent Web UI**:

```bash
# Port-forward giao diện KAgent Web UI
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
# Mở trình duyệt: http://localhost:8080
```

> 📸 **MINH CHỨNG KAGENT CHAT UI:**
>
> *(Chèn ảnh chụp màn hình giao diện kagent-ui trò chuyện với Coordinator Agent tại đây)*
>
> ![KAgent Chat UI](screenshot_kagent_ui_chat.png)