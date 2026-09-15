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
├── final_llm_agent/                    # PHẦN 2: KUBERNETES MULTI-AGENT & MLOPS INFRASTRUCTURE
│   ├── agentic_ai/                     # Phân hệ Multi-Agent & llm-d Serving (FastMCP Tools & KAgent CRDs)
│   ├── observability/                  # Phân hệ Observability (OTel Collector, Jaeger, Prometheus, Grafana)
│   ├── cicd/                           # Phân hệ CI/CD (Jenkinsfile & docker-compose)
│   ├── iac/                            # Phân hệ IaC (Terraform GKE & Ansible VM)
│   ├── tests/                          # Bộ kiểm thử tự động Pytest cho FastMCP tools
│   ├── docs/                           # 9 Báo Cáo Kỹ Thuật & Master Architecture Diagram (PNG/PDF)
│   ├── promptfooconfig.yaml            # Cấu hình Prompt Quality Gate
│   ├── pytest.ini                      # Cấu hình Pytest
│   ├── HUONG_DAN_CHAY.md               # Hướng dẫn chạy từng bước toàn diện
│   └── README.md                       # Master Documentation & Workflow Guide
│
├── pytest.ini                          # Root Pytest config
└── README.md                           # Báo cáo tổng hợp toàn hệ thống
```

---

## 🚀 Hướng Dẫn Vận Hành Hệ Thống

Để xem sơ đồ kiến trúc tổng thể, luồng vận hành chi tiết và hướng dẫn chạy toàn bộ hệ thống từ đầu (From Scratch), vui lòng xem trực tiếp:
👉 **[TÀI LIỆU MASTER README (final_llm_agent/README.md)](./final_llm_agent/README.md)**  
hoặc **[HƯỚNG DẪN TRIỂN KHAI TOÀN DIỆN (HUONG_DAN_CHAY.md)](./final_llm_agent/HUONG_DAN_CHAY.md)**.
