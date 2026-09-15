# 🤖 LLM Agent Architecture — KAgent / FastMCP / Supervisor Pattern

Tài liệu mô tả chi tiết kiến trúc **Hệ Thống AI Multi-Agent chuẩn Kubernetes-Native**, kết hợp giữa **KAgent Framework**, giao thức **Model Context Protocol (FastMCP)** và mô hình điều phối giám sát (**Supervisor Pattern**).

---

## 🏛️ 1. Tổng Quan Kiến Trúc Multi-Agent

Hệ thống được thiết kế theo chuẩn Kubernetes CRD (Custom Resource Definitions) nhằm quản lý vòng đời và khả năng mở rộng của Agent tương tự như các tài nguyên native K8s:

- **KAgent Operator (`kagent.dev`):** Lắng nghe và điều khiển các tài nguyên `Agent`, `MCPServer` và `ModelConfig` trong namespace `kagent`.
- **Supervisor Pattern:** `coordinator-agent` đóng vai trò Master Agent tiếp nhận yêu cầu từ người dùng, phân tích ý định và ủy quyền cho 2 Sub-Agents chuyên môn.
- **FastMCP Tool Layer:** 2 Tool Servers độc lập kết nối trực tiếp vào Data Platform (Redis & Trino) mà không cần qua tầng Web API trung gian.

```
                         ┌─────────────────────────┐
                         │   👤 User (kagent-ui)   │
                         └────────────┬────────────┘
                                      │ (1) Chat Request (:8080)
                                      ▼
                         ┌─────────────────────────┐
                         │  coordinator-agent      │
                         │   (Supervisor Agent)    │
                         └──────┬───────────┬──────┘
       (2a) Shopping Intent     │           │     (2b) Drift Intent
                 ┌──────────────┘           └──────────────┐
                 ▼                                         ▼
      ┌────────────────────┐                    ┌────────────────────┐
      │     ecom-agent     │                    │    drift-agent     │
      │  (Shopping Spec)   │                    │    (Drift Spec)    │
      └──────────┬─────────┘                    └──────────┬─────────┘
                 │ (3a) call tool                          │ (3b) call tool
                 ▼                                         ▼
      ┌────────────────────┐                    ┌────────────────────┐
      │   ecom-mcp Pod     │                    │   drift-mcp Pod    │
      │ (:8000 FastMCP)    │                    │ (:8000 FastMCP)    │
      └──────────┬─────────┘                    └──────────┬─────────┘
                 │                                         │
                 ▼                                         ▼
        [ Redis Online & Trino ]                 [ Redis Stream & Trino ]
```

---

## ⚙️ 2. Khai Báo Các Tài Nguyên KAgent (CRDs)

### 2.1. Supervisor Coordinator Agent (`agentic_ai/coordinator-agent/deployments/agent.yaml`)
```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: coordinator-agent
  namespace: kagent
spec:
  description: Master Coordinator Agent điều phối toàn bộ hệ thống E-Commerce MLOps.
  type: Declarative
  declarative:
    modelConfig: llm-d-model-config
    stream: true
    systemMessage: >-
      Bạn là Master Coordinator AI Agent điều phối toàn bộ hệ thống.
      Quy tắc: Khi người dùng hỏi, phân tích nội dung và GỌI AGENT CHUYÊN MÔN PHÙ HỢP
      (ecom-agent cho mua sắm hoặc drift-agent cho trôi lệch dữ liệu).
    tools:
      - type: Agent
        agent:
          name: ecom-agent
          namespace: kagent
      - type: Agent
        agent:
          name: drift-agent
          namespace: kagent
```

### 2.2. FastMCP Tool Server (`agentic_ai/ecom-mcp/deployments/mcp-server.yaml`)
```yaml
apiVersion: kagent.dev/v1alpha1
kind: MCPServer
metadata:
  name: ecom-mcp
  namespace: kagent
spec:
  transportType: http
  deployment:
    image: nhannguyen2201/ecom-mcp:0.0.1
    port: 8000
    env:
      REDIS_HOST: "redis-master.data-platform.svc.cluster.local"
      REDIS_PORT: "6379"
      TRINO_HOST: "trino-coordinator.data-platform.svc.cluster.local"
      TRINO_PORT: "8080"
  httpTransport:
    targetPort: 8000
    path: /mcp
```

### 2.3. Cấu Hình Suy Luận Chung ModelConfig (`agentic_ai/model-config/model-config.yaml`)
Cả 3 Agent dùng chung tài nguyên `ModelConfig` trỏ tới AI Gateway:
```yaml
apiVersion: kagent.dev/v1alpha2
kind: ModelConfig
metadata:
  name: llm-d-model-config
  namespace: kagent
spec:
  provider: OpenAI
  model: Qwen/Qwen2.5-Coder-0.5B-Instruct
  baseUrl: http://llm-d-inference-gateway.llm-d-quickstart.svc.cluster.local/v1
```

---

## 🛡️ 3. Cơ Chế Bảo Mật Sandbox (SecurityContext)

Các Pod Agent được bảo vệ bằng cơ chế Sandbox với phân quyền tối thiểu (Least Privilege):
- `runAsNonRoot: true`: Tuyệt đối không chạy container bằng quyền `root`.
- `readOnlyRootFilesystem: true`: Khóa toàn bộ hệ thống tệp gốc ở chế độ chỉ đọc để ngăn chặn mã độc ghi tệp.
- Giao tiếp giữa các Agent và MCP Server được kiểm soát chặt chẽ trong nội bộ cluster.

---

## 💬 4. Minh Chứng Giao Diện Tương Tác (UI Chat)

Người dùng tương tác trực tiếp với hệ thống Multi-Agent thông qua Web UI (`kagent-ui` cổng `:8080`):

> 📸 **GIAO DIỆN CHAT TRỰC QUAN VỚI COORDINATOR AGENT:**
>
> ![KAgent Chatbot UI](./screenshot_kagent_chat.png)
