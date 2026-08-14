# 🤖 LLM Agent Architecture — KAgent / KMCP / llm-d / AgentRegistry

Tài liệu mô tả chi tiết kiến trúc **E-Commerce AI Agent System** được xây dựng hoàn toàn theo chuẩn **Kubernetes-native** sử dụng hệ sinh thái:

- **KAgent** (`kagent.dev`) — Kubernetes CRD để khai báo và quản lý AI Agents
- **KMCP** (`kagent.dev`) — Kubernetes CRD để deploy MCP (Model Context Protocol) Servers
- **llm-d** — LLM Inference Platform trên Kubernetes (vLLM + Gateway API + AgentGateway)
- **AgentRegistry** (`aregistry.ai`) — Agent Catalog & Governance platform

---

## 🏗️ 1. High-Level System Deployment Diagram

```
                                ┌─────────────────────────────────┐
                                │       End User / Customer       │
                                └────────────────┬────────────────┘
                                                 │ (1) Chat via kagent-ui
                                                 ▼
                                ┌─────────────────────────────────┐
                                │     kagent-ui (Port 8080)       │
                                │       KAgent Web Interface      │
                                └────────────────┬────────────────┘
                                                 │ (2) Route to Agent CRD
                                                 ▼
                       ┌─────────────────────────────────────────────────┐
                       │              KAgent Controller                  │
                       │   (Watches Agent CRDs in kagent namespace)      │
                       └───────┬──────────────────┬──────────────────────┘
                               │                  │
            ┌──────────────────┤                  ├──────────────────┐
            ▼                  ▼                  ▼                  │
   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐         │
   │  ecom-agent    │ │  drift-agent   │ │coordinator-agent│        │
   │  (Agent CRD)   │ │  (Agent CRD)   │ │  (Agent CRD)   │        │
   └───────┬────────┘ └───────┬────────┘ └───────┬─────────┘        │
           │                  │                  │                   │
           ▼                  ▼                  ▼                   │
   ┌────────────────┐ ┌────────────────┐ ┌───────────────────┐      │
   │  ecom-mcp      │ │  drift-mcp     │ │  ecom-mcp +       │      │
   │ (MCPServer CRD)│ │ (MCPServer CRD)│ │  drift-mcp        │      │
   └───────┬────────┘ └───────┬────────┘ └───────────────────┘      │
           │                  │                                      │
           ▼                  ▼                                      │
   ┌────────────────┐ ┌────────────────┐                             │
   │  Feature Store  │ │  Drift Detection│    ┌───────────────────┐  │
   │  Web API        │ │  Web API        │    │   ModelConfig CRD  │  │
   │  (FastAPI)      │ │  (FastAPI)      │    │  (llm-d / Groq)    │  │
   └────┬──────┬─────┘ └────────────────┘    └─────────┬──────────┘  │
        │      │                                       │             │
        ▼      ▼                                       ▼             │
   ┌────────┐ ┌────────────┐              ┌────────────────────────┐ │
   │ Redis  │ │ Trino/Delta│              │  llm-d Inference       │ │
   │ Online │ │ Lakehouse  │              │  Platform (vLLM +      │ │
   │ Store  │ │ Gold Layer │              │  AgentGateway)         │ │
   └────────┘ └────────────┘              └────────────────────────┘ │
                                                                     │
                                          ┌────────────────────────┐ │
                                          │  AgentRegistry         │◄┘
                                          │  (aregistry.ai Helm)   │
                                          │  Port 12121            │
                                          └────────────────────────┘
```

---

## 🔑 2. Các Thành Phần Chính (Core Components)

### 2.1. MCP Servers (FastMCP — chuẩn KMCP)

MCP Server được xây dựng bằng thư viện **FastMCP** và deploy thông qua KMCP `MCPServer` CRD:

| MCP Server | File Code | MCP Tools Cung Cấp | Backend Web API |
|:---|:---|:---|:---|
| **ecom-mcp** | `ecom-mcp/server.py` | `get_customer_shopping_context`, `get_trending_products_analytics` | `apps/feature_api.py` |
| **drift-mcp** | `drift-mcp/server.py` | `detect_feature_drift` | `apps/drift_api.py` |

### 2.2. KAgent Agents (Kubernetes CRD)

| Agent | YAML CRD | MCP Servers | Vai Trò |
|:---|:---|:---|:---|
| **ecom-agent** | `ecom-mcp/deployments/agent.yaml` | ecom-mcp | Tư vấn mua sắm cá nhân hóa |
| **drift-agent** | `drift-mcp/deployments/agent.yaml` | drift-mcp | Giám sát Data Drift |
| **coordinator-agent** | `coordinator-agent/deployments/agent.yaml` | ecom-mcp + drift-mcp | Điều phối 2 agent |

### 2.3. ModelConfig (kết nối LLM)

| Config | Model | Provider | Endpoint |
|:---|:---|:---|:---|
| `groq-model-config` | `llama-3.1-8b-instant` | Groq Cloud | `https://api.groq.com/openai/v1` |
| `llm-d-model-config` | `Qwen/Qwen3-0.6B` | llm-d Self-Hosted | `http://llm-d-inference-gateway.llm-d-quickstart.svc.cluster.local/v1` |

---

## 🧪 3. Low-Level ML & System Design (5 Key Classes)

### 1. `FastMCP("E-Commerce Feature Store MCP Server")` — MCP Tool Server
- **Vị trí:** [`ecom-mcp/server.py`](file:///home/nhan/Projects/final_coursework/final_llm_agent/ecom-mcp/server.py)
- **Mục đích:** Đóng gói 2 MCP Tools (`get_customer_shopping_context`, `get_trending_products_analytics`) theo chuẩn Model Context Protocol cho KAgent Agents sử dụng.

### 2. `FastMCP("Drift Detection MCP Server")` — MCP Tool Server
- **Vị trí:** [`drift-mcp/server.py`](file:///home/nhan/Projects/final_coursework/final_llm_agent/drift-mcp/server.py)
- **Mục đích:** Đóng gói MCP Tool `detect_feature_drift` phân tích trôi lệch dữ liệu bằng KS-test & PSI score.

### 3. `CustomerFeatureResponse` — Pydantic Schema
- **Vị trí:** [`apps/feature_api.py`](file:///home/nhan/Projects/final_coursework/final_llm_agent/apps/feature_api.py)
- **Mục đích:** Kiểm định kiểu dữ liệu đầu ra cho đặc trưng hợp nhất (Online Redis + Offline Delta Lake).

### 4. `FeatureStoreAPIService` — FastAPI Engine
- **Vị trí:** [`apps/feature_api.py`](file:///home/nhan/Projects/final_coursework/final_llm_agent/apps/feature_api.py)
- **Mục đích:** Kéo song song (Async/Threadpool) dữ liệu từ Redis Online Store và Trino Lakehouse.

### 5. `DriftAnalysisResponse` — Pydantic Schema
- **Vị trí:** [`apps/drift_api.py`](file:///home/nhan/Projects/final_coursework/final_llm_agent/apps/drift_api.py)
- **Mục đích:** Kiểm định cấu trúc dữ liệu báo cáo drift (KS-statistic, p-value, PSI score).

---

## 🚀 4. Quy Trình Deploy Agent Lên Kubernetes

### Bước 1: Deploy Secret & ModelConfig
```bash
cd ecom-mcp/deployments
kubectl apply -f groq-secret.yaml
kubectl apply -f model-config.yaml
```

### Bước 2: Deploy MCP Servers
```bash
kubectl apply -f ecom-mcp/deployments/mcp-server.yaml
kubectl apply -f drift-mcp/deployments/mcp-server.yaml
```

### Bước 3: Deploy Agents
```bash
kubectl apply -f ecom-mcp/deployments/agent.yaml
kubectl apply -f drift-mcp/deployments/agent.yaml
kubectl apply -f coordinator-agent/deployments/agent.yaml
```

### Bước 4: Truy cập kagent-ui
```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
# Mở trình duyệt: http://localhost:8080
```
