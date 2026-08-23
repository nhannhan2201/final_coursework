# 🛍️ E-Commerce Medallion Lakehouse, AI Agent & MLOps System

Hệ thống tích hợp toàn diện quy trình kỹ thuật dữ liệu (**Data Engineering**), kho lưu trữ đặc trưng (**Feature Store**), hệ thống suy luận mô hình ngôn ngữ lớn (**llm-d / vLLM Inference Platform**), kiến trúc đa tác tử (**Multi-Agent System**), và nền tảng giám sát phân tán (**Full-Stack Observability**) trên Kubernetes.

---

## 🏛️ Kiến Trúc Tổng Quan Toàn Hệ Thống

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                           1. MEDALLION LAKEHOUSE & STREAMING DATA                         │
│                                                                                           │
│   [ Kafka Clickstream ] ──> [ PyFlink (Watermark 45m) ] ──> [ Redis Online Store (<1ms) ] │
│                                                                                           │
│   [ PostgreSQL Raw ] ──> [ PySpark Batch ] ──> [ MinIO Datalake (Bronze ➔ Silver ➔ Gold) ]│
│                                              └──> [ Trino Query Engine ]                  │
└───────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                             2. FEATURE STORE & DRIFT WEB APIS                             │
│                                                                                           │
│       [ Feature Store API (:8000) ]              [ Drift Detection API (:8003) ]          │
│       (Hợp nhất Redis Online & Trino Offline)    (Kiểm định KS-Test & PSI Score)          │
└───────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                     3. AGENTIC AI & llm-d INFERENCE INFRASTRUCTURE                        │
│                                                                                           │
│       [ ecom-mcp (:8000) ]                        [ drift-mcp (:8000) ]                   │
│       (get_customer_shopping_context,             (detect_feature_drift)                  │
│        get_trending_products_analytics)                                                   │
│                                              ▲                                            │
│                                              │ (Model Context Protocol)                   │
│                               [ coordinator-agent ]                                       │
│                                              │                                            │
│                                              ▼ (AgentGateway / HTTPRoute)                 │
│                               [ llm-d / vLLM (Qwen3-0.6B) ]                               │
└───────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                              4. FULL-STACK OBSERVABILITY & TELEMETRY                      │
│                                                                                           │
│   • Traces: Apps ──> [ OTel SDK ] ──> [ OTel Collector ] ──> [ Jaeger UI (:16686) ]       │
│   • Logs:   Pods ──> [ Fluent Bit ] ──> [ Elasticsearch ] ──> [ Kibana UI (:5601) ]       │
│   • Metrics:Apps ──> [ Prometheus ] ──> [ Grafana Dashboard (:8082) ]                     │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Cấu Trúc Thư Mục Dự Án

```
.
├── minicoursework/                      # PHẦN 1: MEDALLION LAKEHOUSE & DATA PIPELINES
│   ├── data_pipeline/
│   │   ├── batch_jobs/                 # PySpark ETL (Bronze, Silver, Gold, Compaction)
│   │   └── streaming_jobs/              # PyFlink Streaming Job (Kafka ➔ Redis)
│   ├── dags/                           # Airflow DAGs (Batch, Streaming, RAG)
│   ├── trino/                          # SQL DDL đăng ký toàn bộ bảng Lakehouse
│   ├── data_generation/                # Synthetic Data Generator
│   ├── jars/                           # Flink Kafka Connector JAR
│   └── feature_store/                  # Feast Feature Store Repository
│
├── final_llm_agent/                    # PHẦN 2: KUBERNETES AI AGENT & MLOPS INFRASTRUCTURE
│   │
│   ├── 📂 agentic_ai/                  # [1] Phân hệ Multi-Agent & llm-d (Chuẩn Downloads/agentic_ai)
│   │   ├── model-config/               # ModelConfig CRD & LLM Secret dùng chung
│   │   ├── ecom-mcp/                   # FastMCP Server E-Commerce (server.py, Dockerfile, deployments/)
│   │   ├── drift-mcp/                  # FastMCP Server Drift Detection (server.py, Dockerfile, deployments/)
│   │   ├── coordinator-agent/          # Coordinator Declarative Agent CRD
│   │   ├── agentgateway-routing.yaml   # AgentGateway & HTTPRoute
│   │   ├── agentgateway_policy.yaml    # AgentGateway Telemetry Policy
│   │   ├── notebooks/                  # Demo Notebooks (agent_demo.ipynb)
│   │   └── README.md
│   │
│   ├── 📂 observability/               # [2] Phân hệ Observability (Chuẩn Downloads/observability)
│   │   ├── helm_charts/                # Values Helm cho otel, kibana, langfuse
│   │   ├── imgs/                       # Minh chứng Langfuse API keys & metadata
│   │   ├── grafana_dashboards/         # agent_observability.json (5 Panels)
│   │   └── README.md
│   │
│   ├── 📂 apps/                        # [3] Phân hệ Backend REST APIs (FastAPI)
│   │   ├── feature_api.py              # Feature Store REST API
│   │   ├── drift_api.py                # Real-time Drift Detection API
│   │   ├── telemetry.py                # OpenTelemetry Instrumentation
│   │   └── deployments/                # K8s Deployments cho feature-api, drift-api, ingress
│   │
│   ├── 📂 cicd/                        # [4] Phân hệ CI/CD (Chuẩn Downloads/cicd)
│   │   ├── Jenkinsfile                 # Jenkins Declarative Pipeline (5 Stages)
│   ├── 📂 iac/                         # [5] Phân hệ IaC (Terraform & Ansible)
│   ├── 📂 tests/                       # [6] Bộ kiểm thử tự động (Unit, Property, Load)
│   ├── 📂 docs/                        # [7] Toàn bộ 12 Báo Cáo Kỹ Thuật
│   ├── pytest.ini                      # Cấu hình Pytest
│   ├── HUONG_DAN_CHAY.md               # Hướng dẫn chạy từng bước toàn diện
│   └── README.md                       # Hướng dẫn chi tiết
│
├── pytest.ini                          # Root Pytest config
└── README.md                           # Báo cáo tổng hợp toàn hệ thống
```

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh (Quickstart)

Vui lòng xem chi tiết toàn bộ 5 giai đoạn triển khai tại tài liệu: **[HUONG_DAN_CHAY.md](file:///home/nhan/Projects/final_coursework/final_llm_agent/HUONG_DAN_CHAY.md)**.

### 1. Chạy Bộ Kiểm Thử Tự Động Toàn Diện (36 Tests)
```bash
pytest -v
```

### 2. Triển Khai Nền Tảng K8s & Observability (Helm)
```bash
# 1. Cài đặt NGINX Ingress, KAgent Platform, AgentGateway, KEDA
# (Xem chi tiết Giai đoạn 2 trong HUONG_DAN_CHAY.md)

# 2. Cài đặt Observability Stack (OTel, EFK, Jaeger, Prometheus/Grafana, Langfuse)
# (Xem chi tiết Bước 10 trong HUONG_DAN_CHAY.md)
```

### 3. Triển Khai Ứng Dụng Tự Động Bằng Jenkins CI/CD
```bash
git add .
git commit -m "feat: deploy entire ecommerce ai agent and mlops system"
git push origin main
```
