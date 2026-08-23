# 🤖 Phân Hệ Agentic AI — KAgent, FastMCP & llm-d Inference Platform

Phân hệ toàn diện về **Agentic AI** trên Kubernetes theo đúng chuẩn kiến trúc `llm-d`, `agentgateway`, `kagent`, `FastMCP` và `agentregistry` như bài lab tham khảo.

---

## 🏛️ Kiến Trúc Tổng Quan Phân Hệ

```
[ User Query ] ──> [ Ingress Gateway ] ──> [ kagent-ui ]
                                                 │
                                                 ▼
                                     [ coordinator-agent ]
                                        (Declarative Agent)
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   │ (MCP Tool Calls)                                          │ (Inference /v1/chat/completions)
                   ▼                                                           ▼
         [ MCP Tool Servers ]                                           [ AgentGateway ]
         • ecom-mcp (Shopping context, Analytics)                              │ (HTTPRoute)
         • drift-mcp (Data drift detection)                                    ▼
                   │                                                   [ llm-d / vLLM Engine ]
                   ▼ (REST APIs)                                         (Qwen3-0.6B Model)
         [ Redis + Trino Lakehouse ]
```

---

## 📂 Cấu Trúc Thư Mục Phân Hệ

```text
agentic_ai/
├── model-config/                  # Cấu hình ModelConfig CRD & LLM Secret dùng chung
│   ├── model-config.yaml
│   └── llm-secret.yaml
├── ecom-mcp/                      # FastMCP Server cho E-Commerce Features (server.py, Dockerfile, deployments/)
├── drift-mcp/                     # FastMCP Server cho Drift Detection (server.py, Dockerfile, deployments/)
├── coordinator-agent/             # Coordinator Multi-Agent Orchestration (CRD Declarative Agent)
├── agentgateway-routing.yaml      # Định tuyến AgentGateway & HTTPRoute tới InferencePool
├── notebooks/                     # Jupyter Notebooks demo luồng tương tác Agent
│   └── agent_demo.ipynb
└── README.md                      # Hướng dẫn chi tiết phân hệ
```

---

## 🚀 Hướng Dẫn Cài Đặt Nền Tảng K8s Operators & llm-d (Chạy 1 Lần)

### 1. Cài Đặt KAgent Platform Qua Helm OCI
```bash
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
    --namespace kagent \
    --create-namespace

helm upgrade kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
    --namespace kagent \
    --set global.agents.enabled=false \
    --reuse-values
```

### 2. Cài Đặt Kubernetes Gateway API & AgentGateway
```bash
# Cài đặt Gateway API & GAIE CRDs
export GATEWAY_API_VERSION=v1.5.1
export GAIE_VERSION=v1.5.0
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/${GAIE_VERSION}/manifests.yaml

# Cài đặt AgentGateway Operator
export AGENTGATEWAY_VERSION=v1.3.1
helm upgrade --install agentgateway-crds \
    oci://cr.agentgateway.dev/charts/agentgateway-crds \
    --namespace agentgateway-system \
    --create-namespace \
    --version ${AGENTGATEWAY_VERSION}

helm upgrade --install agentgateway \
    oci://cr.agentgateway.dev/charts/agentgateway \
    --namespace agentgateway-system \
    --create-namespace \
    --version ${AGENTGATEWAY_VERSION} \
    --set inferenceExtension.enabled=true
```

### 3. Cài Đặt AgentRegistry (Catalog UI)
```bash
helm upgrade -i agentregistry oci://ghcr.io/agentregistry-dev/agentregistry/charts/agentregistry \
    --namespace agentregistry \
    --create-namespace \
    --set config.jwtPrivateKey=$(openssl rand -hex 32) \
    --set image.tag=v0.3.3 \
    --set database.host=postgres-pgvector.agentregistry.svc.cluster.local \
    --set database.password=agentregistry \
    --set database.sslMode=disable
```

### 4. Triển Khai llm-d ModelServer (Chuẩn theo bài lab)
```bash
export NAMESPACE=llm-d-quickstart
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Clone llm-d repo
git clone https://github.com/llm-d/llm-d.git -b release-0.8 /tmp/llm-d
export REPO_ROOT=/tmp/llm-d
source ${REPO_ROOT}/guides/env.sh
export GUIDE_NAME="quickstart"

# Deploy ModelServer (vLLM Qwen3-0.6B)
export ACCELERATOR_TYPE=cpu
export MODEL_SERVER=vllm
export INFRA_PROVIDER=base
kubectl apply -n ${NAMESPACE} -k ${REPO_ROOT}/guides/${GUIDE_NAME}/modelserver/${ACCELERATOR_TYPE}/${MODEL_SERVER}/
```

---

## 🎯 Triển Khai Declarative Agents & FastMCP Servers (Jenkins Tự Động Deploy)

```bash
# 1. Triển khai ModelConfig & Secret kết nối llm-d
kubectl apply -f model-config/

# 2. Triển khai AgentGateway Routing & Telemetry Policy
kubectl apply -f agentgateway-routing.yaml
kubectl apply -f agentgateway_policy.yaml

# 3. Triển khai 2 FastMCP Tool Servers
kubectl apply -f ecom-mcp/deployments/
kubectl apply -f drift-mcp/deployments/

# 4. Triển khai Coordinator Agent
kubectl apply -f coordinator-agent/deployments/
```

### 💬 Trò Chuyện Với Agent Qua UI:
```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```
Truy cập: **`http://localhost:8080`**
