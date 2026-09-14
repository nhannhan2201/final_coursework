# 🚀 HƯỚNG DẪN TRIỂN KHAI TOÀN DIỆN DỰ ÁN TỪ ĐẦU (FROM SCRATCH)

Tài liệu hướng dẫn quy trình vận hành và triển khai toàn bộ hệ thống **E-Commerce Lakehouse, Multi-Agent & MLOps Infrastructure** từ khi **chưa có gì** đến khi hệ thống hoạt động hoàn chỉnh 100%.

---

## 📑 TỔNG QUAN CÁC GIAI ĐOẠN TRIỂN KHAI

```
[ GIAI ĐOẠN 1: CẤP PHÁT HẠ TẦNG IaC ]
   Terraform tạo GKE & VM ➔ Ansible cài đặt Data Stack (MinIO, Trino, Redis, Kafka, Airflow)
                           │
                           ▼
[ GIAI ĐOẠN 2: THIẾT LẬP K8S OPERATORS & INGRESS ]
   Cài NGINX Ingress Controller, KAgent CRDs, Gateway API, AgentGateway, AgentRegistry (1 lần)
                           │
                           ▼
[ GIAI ĐOẠN 3: THIẾT LẬP JENKINS CI/CD ]
   Khởi chạy Jenkins Server trên VM ➔ Cấp quyền RBAC Kubeconfig ➔ Cài GitHub Webhook
                           │
                           ▼
[ GIAI ĐOẠN 4: KÍCH HOẠT CI/CD ĐẨY TOÀN BỘ HỆ THỐNG ]
   Gõ `git push origin main` ➔ Jenkins tự động Test, Build, Push Images, và Deploy K8s
                           │
                           ▼
[ GIAI ĐOẠN 5: VẬN HÀNH & KIỂM TRA CHỨC NĂNG ]
   Chatbot KAgent UI, Jaeger Tracing, Kibana Logging, Grafana Metrics, KEDA Autoscaling
```

---

## 🗺️ LỰA CHỌN PHƯƠNG ÁN TRIỂN KHAI

Hệ thống hỗ trợ 2 lộ trình triển khai hoàn chỉnh:

* **🌟 PHẦN A (KHUYÊN DÙNG ĐẦU TIÊN): TRIỂN KHAI & TEST 100% CỤC BỘ (LOCAL DATA & AI AGENT)**
  * **Mục tiêu:** Chạy toàn bộ Data Stack (MinIO, Trino, Redis, Kafka, Airflow) bằng Docker Compose và hệ thống Agentic AI (KAgent, llm-d vLLM, FastMCP) trên cụm K8s Kind cục bộ.
  * **Ưu điểm:** **Zero chi phí Cloud**, phản hồi tức thì, xác thực logic nghiệp vụ trơn tru trước khi lên Cloud.
* **☁️ PHẦN B: TRIỂN KHAI PRODUCTION CLOUD (TERRAFORM IaC, GKE, ANSIBLE & JENKINS CI/CD)**
  * **Mục tiêu:** Tự động hóa toàn bộ việc cấp phát GKE, VM, cài đặt Data Stack qua Ansible và CI/CD qua Jenkins khi đẩy mã nguồn lên GitHub.

---

# 🌟 PHẦN A: TRIỂN KHAI & TEST 100% CỤC BỘ (DATA + AI AGENT + OBSERVABILITY)

```
[ BƯỚC A1: DOCKER COMPOSE DATA STACK ]
   MinIO (:9000), Redis (:6379), Trino (:8085), Kafka (:9092), Airflow (:8081)
                           │
                           ▼
[ BƯỚC A2: SINH DỮ LIỆU FEATURE STORE & LAKEHOUSE ]
   Chạy data_generation ➔ Nạp dữ liệu vào Redis Online Store & MinIO Gold Delta Lake
                           │
                           ▼
[ BƯỚC A3: KHỞI TẠO CỤM K8S KIND CỤC BỘ ]
   Tạo cụm `agentic-ai` qua `kind-config.yaml` ➔ Load Docker images vào Kind
                           │
                           ▼
[ BƯỚC A4: CÀI ĐẶT HẠ TẦNG OBSERVABILITY STACK (OTEL, JAEGER, GRAFANA) ]
   OTel Collector (:4317) ➔ Jaeger Tracing (:16686) ➔ Prometheus & Grafana (:8082)
                           │
                           ▼
[ BƯỚC A5: CÀI ĐẶT OPERATORS & LLM-D INFERENCE ENGINE ]
   KAgent Platform ➔ Gateway API & AgentGateway ➔ vLLM Qwen3-0.6B (Hermes Parser)
                           │
                           ▼
[ BƯỚC A6: KÍCH HOẠT AGENTGATEWAY TRACING POLICY & MODELCONFIG ]
   Áp dụng agentgateway_policy.yaml (Bắt token LLM) ➔ ModelConfig (timeout: 300)
                           │
                           ▼
[ BƯỚC A7: TRIỂN KHAI MCP SERVERS & COORDINATOR AGENT ]
   ecom-mcp ➔ drift-mcp (Gắn OTel Trace) ➔ coordinator-agent (Supervisor Pattern)
                           │
                           ▼
[ BƯỚC A8: TEST TOÀN DIỆN: CHATBOT UI + JAEGER TRACING + GRAFANA METRICS ]
   Chatbot tại :8080 ➔ Xem timeline trên Jaeger :16686 ➔ Xem chỉ số trên Grafana :8082
```

---

### Bước A1: Khởi Động Tầng Dữ Liệu Bằng Docker Compose
Toàn bộ Data Stack được định nghĩa sẵn trong thư mục `minicoursework`:
```bash
cd /home/nhan/Projects/final_coursework/minicoursework

# 1. Tạo Docker network chia sẻ (nếu chưa có)
docker network create datahub_network 2>/dev/null || true

# 2. Khởi chạy toàn bộ Data Stack
docker compose -f docker-compose.yml up -d
```
*Kiểm tra các cổng dịch vụ đang hoạt động:*
* **Redis Feature Store:** `localhost:6379`
* **MinIO Console UI:** `http://localhost:9001` (User: `admin` / Pass: `password123`)
* **Trino Query Engine Web UI:** `http://localhost:8085`
* **Airflow Web UI:** `http://localhost:8081` (User: `airflow` / Pass: `airflow`)

---

### Bước A2: Sinh Dữ Liệu Mẫu Cho Feature Store & Lakehouse
Sinh dữ liệu mẫu về hồ sơ khách hàng, các chính sách cửa hàng và nạp tính năng thời gian thực (Streaming Features) vào Redis:
```bash
# Đứng tại thư mục minicoursework
# 1. Sinh dữ liệu Batch (khách hàng, đơn hàng, nhãn churn) đẩy lên MinIO
python3 data_generation/main.py

# 2. Sinh tài liệu tri thức chính sách cửa hàng (RAG Documents) lên MinIO
python3 data_generation/generate_rag_documents.py

# 3. Nạp dữ liệu Streaming Features thời gian thực (lượt xem 30m, thêm giỏ 30m) vào Redis Feature Store (Port 6379)
python3 data_generation/generate_stream_features.py
```
*(Sau bước này, khách hàng mẫu `CUST_000001` cùng các feature streaming `f_stream_views_30m`, `f_stream_add_to_cart_30m` đã sẵn sàng trong Redis và MinIO).*

---

### Bước A3: Đóng Gói Docker Image FastMCP & Khởi Tạo Cụm K8s Kind
Chuyển về thư mục dự án `final_llm_agent`:
```bash
cd /home/nhan/Projects/final_coursework/final_llm_agent

# 1. Đóng gói Docker Images cho 2 FastMCP Tool Servers (Nếu máy bạn đã build sẵn thì có thể bỏ qua bước này)
docker build -t nhannguyen2201/ecom-mcp:0.0.1 agentic_ai/ecom-mcp
docker build -t nhannguyen2201/drift-mcp:0.0.1 agentic_ai/drift-mcp

# 2. Tạo cụm Kubernetes Kind cục bộ (ánh xạ cổng 80 & 443)
kind create cluster --name agentic-ai --config agentic_ai/kind-config.yaml

# 3. Kiểm tra ngữ cảnh kết nối
kubectl cluster-info --context kind-agentic-ai

# 4. Nạp 2 Docker Image FastMCP vào cụm Kind (giúp Pod kéo image trực tiếp không cần mạng Internet)
kind load docker-image nhannguyen2201/ecom-mcp:0.0.1 --name agentic-ai
kind load docker-image nhannguyen2201/drift-mcp:0.0.1 --name agentic-ai
```

---

### Bước A4: Cài Đặt Phân Hệ Observability Stack (OTel, Jaeger, Prometheus, Grafana)
Triển khai hạ tầng giám sát trước để sẵn sàng hứng Logs, Traces và Metrics từ Agent và Gateway:
```bash
# 1. Tạo namespace monitoring
kubectl create ns monitoring --dry-run=client -o yaml | kubectl apply -f -

# 2. Cài đặt OpenTelemetry Collector (Cổng 4317 gRPC / 4318 HTTP)
# Sử dụng values-local.yaml tinh gọn: Thu nhận Trace/Metrics và đẩy sang Jaeger + Prometheus, không yêu cầu Secret ngoài
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm upgrade --install opentelemetry-collector open-telemetry/opentelemetry-collector \
  -n monitoring \
  -f observability/helm_charts/otel/values-local.yaml

# 3. Cài đặt Jaeger Tracing (Thu thập timeline thực thi phân tán)
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm upgrade --install jaeger jaegertracing/jaeger -n monitoring

# 4. Cài đặt Prometheus & Grafana (Giám sát Metrics, RPS, Latency)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install kube-prometheus-stack oci://ghcr.io/prometheus-community/charts/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.additionalArgs[0].name=web.enable-otlp-receiver \
  --set prometheus.prometheusSpec.additionalArgs[0].value="" \
  --set coreDns.enabled=false

# 5. Kiểm tra Pods monitoring khởi động thành công (Running 1/1)
kubectl get pods -n monitoring
```

---

### Bước A5: Cài Đặt Nền Tảng KAgent, Gateway API & AgentGateway
```bash
# 1. Cài đặt KAgent Operator & UI qua Helm
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds     --namespace kagent     --create-namespace

helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent     --namespace kagent     --set global.agents.enabled=false

# 2. Cài đặt Gateway API & GAIE CRDs (chuẩn v1-manifests.yaml)
export GATEWAY_API_VERSION=v1.5.1
export GAIE_VERSION=v1.5.0
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/${GAIE_VERSION}/v1-manifests.yaml

# 3. Cài đặt AgentGateway Operator (với tính năng inferenceExtension)
export AGENTGATEWAY_VERSION=v1.3.1
helm upgrade --install agentgateway-crds     oci://cr.agentgateway.dev/charts/agentgateway-crds     --namespace agentgateway-system     --create-namespace     --version ${AGENTGATEWAY_VERSION}

helm upgrade --install agentgateway     oci://cr.agentgateway.dev/charts/agentgateway     --namespace agentgateway-system     --create-namespace     --version ${AGENTGATEWAY_VERSION}     --set inferenceExtension.enabled=true
```

---

### Bước A6: Triển Khai llm-d Inference Platform & Bật LLM Tracing Policy
```bash
export NAMESPACE=llm-d-quickstart
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 1. Tạo Secret HF_TOKEN
export HF_TOKEN=<YOUR_HUGGINGFACE_TOKEN>
kubectl create secret generic llm-d-hf-token   --from-literal="HF_TOKEN=${HF_TOKEN}"   --namespace "${NAMESPACE}"   --dry-run=client -o yaml | kubectl apply -f -

# 2. Cấu hình biến môi trường
export REPO_ROOT="$(pwd)/agentic_ai/llm-d"
export GUIDE_NAME="optimized-baseline"
export PROVIDER_NAME=agentgateway
export ACCELERATOR_TYPE=cpu
export MODEL_SERVER=vllm
export ROUTER_GATEWAY_CHART="oci://ghcr.io/llm-d/charts/llm-d-router-gateway"
export ROUTER_CHART_VERSION="v0.9.0"
export INFERENCE_GATEWAY_NAME="llm-d-inference-gateway"

# 3. Triển khai AI Gateway
kubectl apply -k ${REPO_ROOT}/guides/recipes/gateway/agentgateway -n ${NAMESPACE}

# 4. Cài đặt llm-d Router Gateway & HTTPRoute qua Helm
helm upgrade --install ${GUIDE_NAME} ${ROUTER_GATEWAY_CHART} --version ${ROUTER_CHART_VERSION} \
    -f ${REPO_ROOT}/guides/recipes/router/base.values.yaml \
    -f ${REPO_ROOT}/guides/${GUIDE_NAME}/router/${GUIDE_NAME}.values.yaml \
    --set provider.name=${PROVIDER_NAME} \
    --set httpRoute.create=true \
    --set httpRoute.inferenceGatewayName=${INFERENCE_GATEWAY_NAME} \
    --set router.epp.resources.requests.cpu=500m \
    --set router.epp.resources.requests.memory=512Mi \
    --set router.epp.resources.limits.memory=2Gi \
    -n ${NAMESPACE}

# 5. Khởi chạy ModelServer phục vụ Qwen3-0.6B (vLLM Engine với hermes parser)
kubectl apply -n ${NAMESPACE} -k ${REPO_ROOT}/guides/${GUIDE_NAME}/modelserver/${ACCELERATOR_TYPE}/${MODEL_SERVER}/

# 6. Chờ vLLM Pod hoàn tất khởi động (READY 1/1)
kubectl rollout status deployment/${GUIDE_NAME}-${ACCELERATOR_TYPE}-${MODEL_SERVER}-decode -n ${NAMESPACE}

# 7. Kích hoạt LLM Tracing Policy (AgentGateway tự động bắn traces sang OTel Collector)
kubectl apply -f agentic_ai/agentgateway_policy.yaml
```

---

### Bước A7: Thiết Lập Cầu Nối Dữ Liệu & Triển Khai FastMCP Servers, Coordinator Agent
```bash
# 1. Thiết lập cầu nối mạng nội bộ (DNS Bridge) từ Kind sang Docker Compose Host:
# Tự động ánh xạ DNS redis-master.data-platform (Port 6379) và trino-coordinator.data-platform (Port 8080 -> Host 8085)
# giúp FastMCP Server bên trong Kubernetes truy vấn trực tiếp vào Redis/Trino đang chạy trên máy Host.
bash agentic_ai/apply-local-bridge.sh

# 2. Triển khai ModelConfig (đã cấu hình timeout: 300) & Secret LLM
kubectl apply -f agentic_ai/model-config/

# 3. Triển khai 2 FastMCP Tool Servers (tự động gắn OpenTelemetry Tracing)
kubectl apply -f agentic_ai/ecom-mcp/deployments/
kubectl apply -f agentic_ai/drift-mcp/deployments/

# 4. Triển khai Master Coordinator Agent (Supervisor Pattern)
kubectl apply -f agentic_ai/coordinator-agent/deployments/

# 5. Kiểm tra toàn bộ Pods trong namespace kagent
kubectl get pods -n kagent
```

---

### Bước A8: Test Toàn Diện (Chatbot UI + Jaeger Tracing + Grafana)

#### 1. Trò Chuyện Trực Tiếp Qua KAgent UI:
```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```
Truy cập: **`http://localhost:8080`**, chọn agent **`coordinator-agent`** và thử các câu hỏi:
* **Hỏi hồ sơ mua sắm:** `"Cho tôi xem hồ sơ và lịch sử mua sắm của khách hàng CUST_000001"`
* **Hỏi trôi lệch dữ liệu:** `"Kiểm tra xem dữ liệu feature f_stream_views_30m có bị drift không?"`

#### 2. Xem Distributed Tracing Trên Jaeger UI:
```bash
kubectl port-forward -n monitoring svc/jaeger 16686:16686
```
Truy cập: **`http://localhost:16686`** ➔ Chọn service `ecom-mcp`, `drift-mcp` hoặc `llm-d-inference-gateway` ➔ Bạn sẽ thấy toàn bộ dòng thời gian chi tiết: từ lúc AgentGateway nhận câu hỏi, đo số token tiêu thụ, đến lúc MCP Server truy vấn Redis/Trino.

#### 3. Giám Sát Hiệu Năng Trên Grafana:
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 8082:80
```
Truy cập: **`http://localhost:8082`** (User: `admin` / Password: `kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d`) để xem biểu đồ hiệu năng hệ thống.

---

# ☁️ PHẦN B: TRIỂN KHAI PRODUCTION CLOUD (TERRAFORM IaC, GKE, ANSIBLE & JENKINS CI/CD)

## 🏗️ GIAI ĐOẠN 1: CẤP PHÁT HẠ TẦNG BẰNG IaC (TERRAFORM & ANSIBLE)

### Bước 1: Khởi Tạo Cụm GKE & Máy Ảo VM Bằng Terraform
```bash
cd final_llm_agent/iac/terraform

# 1. Khởi tạo Terraform provider
terraform init

# 2. Cấp phát tài nguyên trên Google Cloud (GKE Cluster + Compute Engine VM)
terraform apply -auto-approve
```

### Bước 2: Mở Cổng Firewall Cho VM Trên Google Cloud
Cho phép GitHub gửi Webhook tới Jenkins (Port `8081`) và mở các cổng truy cập:
```bash
gcloud compute firewall-rules create allow-cicd-jenkins \
    --allow tcp:8081,tcp:8080,tcp:8082,tcp:9090,tcp:5601,tcp:16686 \
    --direction INGRESS \
    --priority 1000 \
    --description "Cho phep truy cap Jenkins, Webhook va cac cong Observability"
```

### Bước 3: Tự Động Thiết Lập Data Stack Bằng Ansible
```bash
cd ../ansible

# Chạy Ansible Playbook (tự động quét IP VM trên GCP qua Dynamic Inventory):
ansible-playbook -i inventory.gcp.yml site.yml
```

### Bước 4: Khởi Chạy Pipeline Dữ Liệu & Sinh Dữ Liệu
Trên máy ảo VM (hoặc qua SSH), chạy generator sinh dữ liệu và kích hoạt Airflow:
```bash
# 2. Sinh dữ liệu ban đầu (Batch & RAG Documents) qua container Airflow:
docker exec -it -u 0 -w /opt/airflow/project/data_generation -e MINIO_ENDPOINT="http://minio:9000" ecom_airflow_scheduler python main.py
docker exec -it -u 0 -w /opt/airflow/project/data_generation ecom_airflow_scheduler python generate_rag_documents.py

# 3. Chạy luồng giả lập sự kiện Clickstream thời gian thực (Streaming Data -> Kafka):
docker exec -d -w /opt/airflow/project -e KAFKA_BOOTSTRAP_SERVERS="kafka:29092" -e MINIO_ENDPOINT="http://minio:9000" ecom_airflow_scheduler python data_pipeline/streaming_jobs/kafka_stream_producer.py

# 4. Kích hoạt các DAGs xử lý Bronze ➔ Silver ➔ Gold trên Airflow UI (:8080)
# Airflow UI: http://<IP_PUBLIC_VM>:8080 (User: airflow / Pass: airflow)
```

---

## ☸️ GIAI ĐOẠN 2: THIẾT LẬP K8S OPERATORS & INGRESS (CHẠY 1 LẦN DUY NHẤT)

Kết nối máy tính của bạn tới cụm GKE vừa tạo:
```bash
# Lấy file cấu hình kết nối GKE
gcloud container clusters get-credentials ecom-kagent-gke-cluster --zone asia-southeast1-b --project k8s-sentiment
```

### Bước 5: Cài Đặt NGINX Ingress Controller
Cài đặt Controller để Google Cloud cấp 1 địa chỉ **External IP / Load Balancer**:
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx
```

### Bước 6: Cài Đặt KAgent Operator & Custom Resource Definitions (CRDs) Qua Helm OCI
```bash
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
    --namespace kagent \
    --create-namespace

helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
    --namespace kagent \
    --set global.agents.enabled=false
```

### Bước 7: Cài Đặt Kubernetes Gateway API & AgentGateway Operator
```bash
# 1. Cài đặt Gateway API & GAIE CRDs
export GATEWAY_API_VERSION=v1.5.1
export GAIE_VERSION=v1.5.0
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/${GAIE_VERSION}/v1-manifests.yaml

# 2. Cài đặt AgentGateway Operator
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

### Bước 8: Cài Đặt AgentRegistry (Catalog UI) & KEDA Autoscaler
```bash
# 1. Cài đặt AgentRegistry
helm upgrade -i agentregistry oci://ghcr.io/agentregistry-dev/agentregistry/charts/agentregistry \
    --namespace agentregistry \
    --create-namespace \
    --set config.jwtPrivateKey=$(openssl rand -hex 32) \
    --set image.tag=v0.3.3 \
    --set database.host=postgres-pgvector.agentregistry.svc.cluster.local \
    --set database.password=agentregistry \
    --set database.sslMode=disable

# 2. Cài đặt KEDA Autoscaler
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

### Bước 9: Triển Khai llm-d Inference Gateway, Helm Router & ModelServer (vLLM Qwen3-0.6B)
```bash
export NAMESPACE=llm-d-quickstart
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 1. Tạo Secret HF_TOKEN cho vLLM
export HF_TOKEN=<YOUR_HUGGINGFACE_TOKEN>
kubectl create secret generic llm-d-hf-token \
  --from-literal="HF_TOKEN=${HF_TOKEN}" \
  --namespace "${NAMESPACE}" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Đường dẫn thư mục llm-d đã tích hợp sẵn trong repo (đã fix Qwen3-0.6B + hermes tool parser)
cd /home/nhan/Projects/final_coursework/final_llm_agent
export REPO_ROOT="$(pwd)/agentic_ai/llm-d"
export GUIDE_NAME="optimized-baseline"
export PROVIDER_NAME=agentgateway
export ACCELERATOR_TYPE=cpu
export MODEL_SERVER=vllm
export ROUTER_GATEWAY_CHART="oci://ghcr.io/llm-d/charts/llm-d-router-gateway"
export ROUTER_CHART_VERSION="v0.8.0"
export INFERENCE_GATEWAY_NAME="llm-d-inference-gateway"

# 3. Triển khai AI Gateway (tạo Gateway llm-d-inference-gateway sinh ra baseUrl cho KAgent)
kubectl apply -k ${REPO_ROOT}/guides/recipes/gateway/agentgateway -n ${NAMESPACE}

# 4. Cài đặt llm-d Router Gateway & HTTPRoute qua Helm
helm upgrade --install ${GUIDE_NAME} ${ROUTER_GATEWAY_CHART} --version ${ROUTER_CHART_VERSION} \
    -f ${REPO_ROOT}/guides/recipes/router/base.values.yaml \
    -f ${REPO_ROOT}/guides/${GUIDE_NAME}/router/${GUIDE_NAME}.values.yaml \
    --set provider.name=${PROVIDER_NAME} \
    --set httpRoute.create=true \
    --set httpRoute.inferenceGatewayName=${INFERENCE_GATEWAY_NAME} \
    --set resources.requests.cpu=500m \
    --set resources.requests.memory=512Mi \
    -n ${NAMESPACE}

# 5. Khởi chạy ModelServer phục vụ Qwen3-0.6B trên CPU (đã cấu hình sẵn patch-vllm.yaml với hermes parser và định mức 4 CPU / 8GiB)
kubectl apply -n ${NAMESPACE} -k ${REPO_ROOT}/guides/${GUIDE_NAME}/modelserver/${ACCELERATOR_TYPE}/${MODEL_SERVER}/
```

### Bước 10: Cài Đặt Phân Hệ Observability Stack Bằng Helm (OTel, EFK, Jaeger, Prometheus, Langfuse)
*(Theo đúng chuẩn hướng dẫn trong `observability/README.md`)*
```bash
# 1. Cài đặt OpenTelemetry Collector
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
kubectl create ns monitoring --dry-run=client -o yaml | kubectl apply -f -
helm install opentelemetry-collector open-telemetry/opentelemetry-collector -n monitoring -f observability/helm_charts/otel/values.yaml

# 2. Cài đặt Elasticsearch & Kibana (EFK Logging)
helm repo add elastic https://helm.elastic.co && helm repo update
helm install elastic-operator elastic/eck-operator -n elastic-system --create-namespace
helm install elastic elastic/eck-stack -n monitoring -f observability/helm_charts/kibana/values.yaml

# 3. Cài đặt Jaeger Tracing
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm install jaeger jaegertracing/jaeger -n monitoring

# 4. Cài đặt Prometheus & Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus-stack oci://ghcr.io/prometheus-community/charts/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.additionalArgs[0].name=web.enable-otlp-receiver \
  --set prometheus.prometheusSpec.additionalArgs[0].value="" \
  --set coreDns.enabled=false

# 5. Cài đặt Langfuse LLM Observability
kubectl create secret generic langfuse-secrets -n monitoring \
  --from-literal=salt="$(openssl rand -base64 32)" \
  --from-literal=nextauthSecret="$(openssl rand -base64 32)" \
  --from-literal=encryptionKey="$(openssl rand -hex 32)" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic langfuse-postgresql-auth -n monitoring --from-literal=password="$(openssl rand -hex 24)" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic langfuse-clickhouse-auth -n monitoring --from-literal=password="$(openssl rand -hex 24)" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic langfuse-redis-auth -n monitoring --from-literal=password="$(openssl rand -hex 24)" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic langfuse-s3-auth -n monitoring --from-literal=rootUser="langfuse-admin" --from-literal=rootPassword="$(openssl rand -base64 24)" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic langfuse-otel-auth -n monitoring --from-literal=basicAuth="$(printf '%s' 'pk-lf-placeholder:sk-lf-placeholder' | base64 -w0)" --dry-run=client -o yaml | kubectl apply -f -

helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm install langfuse langfuse/langfuse --version 1.5.41 -n monitoring -f observability/helm_charts/langfuse/values.yaml
```

---

## 🔄 GIAI ĐOẠN 3: KHỞI CHẠY JENKINS CI/CD SERVER TRÊN VM

### Bước 11: Khởi Chạy Jenkins Container Bằng Docker Compose
Trên máy ảo VM:
```bash
cd final_llm_agent/cicd
docker compose up -d
```
*Lấy mật khẩu ban đầu của Jenkins:*
```bash
docker exec -it jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```
Truy cập: **`http://<IP_PUBLIC_VM>:8081`** để hoàn tất cài đặt plugin cơ bản.

### Bước 12: Cấu Hình Phân Quyền RBAC Cho Jenkins Trên K8s
Tạo ServiceAccount `jenkins` với quyền cluster-admin để Jenkins deploy ứng dụng:
```bash
# 1. Tạo ServiceAccount và RoleBinding
kubectl create serviceaccount jenkins -n default
kubectl create clusterrolebinding jenkins --clusterrole=cluster-admin --serviceaccount=default:jenkins

# 2. Tạo Secret Token dài hạn
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: jenkins-token
  namespace: default
  annotations:
    kubernetes.io/service-account.name: jenkins
type: kubernetes.io/service-account-token
EOF

# 3. Tạo file kubeconfig cho Jenkins
TOKEN=$(kubectl get secret jenkins-token -n default -o jsonpath='{.data.token}' | base64 -d)
CA_DATA=$(kubectl config view --raw --minify --flatten -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
SERVER_URL=$(kubectl config view --raw --minify --flatten -o jsonpath='{.clusters[0].cluster.server}')

cat <<EOF > kubeconfig
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: ${SERVER_URL}
    certificate-authority-data: ${CA_DATA}
  name: gke
contexts:
- context:
    cluster: gke
    user: jenkins
  name: gke
current-context: gke
users:
- name: jenkins
  user:
    token: ${TOKEN}
EOF
```

### Bước 13: Thiết Lập Credentials Trên Jenkins & Webhook Trên GitHub
1. **Trên Jenkins (`http://<IP_PUBLIC_VM>:8081/credentials`):**
   - **`github`** (Username with Password): Username GitHub + GitHub PAT (Personal Access Token).
   - **`dockerhub`** (Username with Password): Username `nhannguyen2201` + Docker Hub Token.
   - **`kubeconfig`** (Secret File): Tải file `kubeconfig` vừa tạo ở bước trên lên.
2. **Trên GitHub Repository:**
   - Vào **Settings ➔ Webhooks ➔ Add webhook**.
   - Payload URL: `http://<IP_PUBLIC_VM>:8081/github-webhook/`
   - Content type: `application/json`
   - Event: `Just the push event`.

---

## 🚀 GIAI ĐOẠN 4: KÍCH HOẠT CI/CD TỰ ĐỘNG TRIỂN KHAI TOÀN BỘ HỆ THỐNG

Bây giờ hạ tầng đã sẵn sàng 100%. Bạn chỉ cần push code lên GitHub:

```bash
git add .
git commit -m "feat: deploy entire ecommerce ai agent and mlops system"
git push origin main
```

**Jenkins sẽ tự động thực thi 5 giai đoạn liên hoàn:**
1. **Stage 1 (Checkout):** Tải commit mới nhất.
2. **Stage 2 (Test):** Chạy tự động bộ kiểm thử FastMCP Tools (`pytest tests/ -v`).
3. **Stage 3 (Build & Push):** Đóng gói và đẩy 2 FastMCP images (`ecom-mcp`, `drift-mcp`) lên Docker Hub.
4. **Stage 4 (Tag Release):** Gắn Semantic Tag Release (`vX.Y.Z`) lên GitHub.
5. **Stage 5 (Deploy):** Tự động áp dụng toàn bộ manifests ứng dụng lên K8s:
   - Triển khai ModelConfig & AgentGateway Policy (`agentic_ai/model-config/`, `agentgateway_policy.yaml`).
   - Triển khai FastMCP Servers & Coordinator Agent (`agentic_ai/ecom-mcp/`, `agentic_ai/drift-mcp/`, `agentic_ai/coordinator-agent/`).
   - Zero-Downtime Rollout Restart toàn bộ Pods.

---

## 🎯 GIAI ĐOẠN 5: TRẢI NGHIỆM & VẬN HÀNH HỆ THỐNG LIVE

### 1. Trò Chuyện Trực Tiếp Với AI Agent Qua KAgent UI
Mở port-forward vào giao diện Chatbot:
```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```
Truy cập: **`http://localhost:8080`** và thử các câu lệnh:
- **Tư vấn khách hàng:** `"Cho tôi xem hồ sơ và lịch sử mua sắm của khách hàng CUST_000001"` ➔ Agent tự động gọi `ecom-mcp` lấy feature từ Redis/Trino.
- **Phân tích xu hướng:** `"Xu hướng sản phẩm nào đang bán chạy nhất?"` ➔ Agent tự động gọi `ecom-mcp` phân tích Gold Layer.
- **Giám sát trôi lệch dữ liệu:** `"Kiểm tra xem dữ liệu streaming feature f_stream_views_30m có bị drift không?"` ➔ Agent tự động gọi `drift-mcp` tính toán KS-test & PSI score.

---

### 2. Xem Distributed Tracing Trên Jaeger UI
```bash
kubectl port-forward -n monitoring svc/jaeger 16686:16686
```
Truy cập: **`http://localhost:16686`** ➔ Chọn service `ecom-mcp` hoặc `drift-mcp` ➔ Xem toàn bộ timeline chi tiết từng mili-giây truy vấn Redis và Trino.

---

### 3. Tra Cứu Log Tập Trung Trên Kibana UI
```bash
kubectl port-forward -n monitoring svc/elastic-eck-kibana-kb-http 5601:5601
```
Truy cập: **`https://localhost:5601`** (User: `elastic` / Pass lấy từ secret `elasticsearch-es-elastic-user`) ➔ Vào mục **Discover** ➔ Tìm kiếm log theo từ khóa `level: ERROR` hoặc `customer_id`.

---

### 4. Giám Sát Hiệu Năng Thời Gian Thực Trên Grafana
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 8082:80
```
Truy cập: **`http://localhost:8082`** (User: `admin` / Pass: `kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d`) ➔ Mở Dashboard **E-Commerce Agent Observability** để xem 5 biểu đồ:
1. Throughput (RPS)
2. P95 / P99 Latency
3. Error Rate (5xx/4xx)
4. Data Drift Detection Rate
5. Active Connections

---

### 5. Giám Sát LLM Traces & Tokens Trên Langfuse UI
```bash
kubectl port-forward -n monitoring svc/langfuse-web 3000:3000
```
Truy cập: **`http://localhost:3000`** ➔ Xem chi tiết từng lượt gọi Agent, Prompt Tokens, Completion Tokens và độ trễ sinh từ đầu tiên (TTFT).

---

### 6. Kiểm Tra Tự Động Co Giãn Tải KEDA & Ingress Routing
Lấy Public IP của NGINX Ingress:
```bash
INGRESS_IP=$(kubectl get ingress ecom-agentic-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Kiểm tra định tuyến Ingress tới FastMCP Servers
curl -s http://${INGRESS_IP}/mcp/ecom
curl -s http://${INGRESS_IP}/mcp/drift

# Kiểm tra trạng thái KEDA tự động scale Pods từ 1 -> 5 khi tải tăng
kubectl get scaledobject -A
kubectl get pods -n kagent -l app=ecom-mcp -w
```
