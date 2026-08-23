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
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/${GAIE_VERSION}/manifests.yaml

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

### Bước 9: Triển Khai llm-d ModelServer (vLLM Qwen3-0.6B)
```bash
export NAMESPACE=llm-d-quickstart
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 1. Tạo Secret HF_TOKEN cho ModelServer
kubectl create secret generic llm-d-hf-token \
    -n ${NAMESPACE} \
    --from-literal=HF_TOKEN="hf_placeholder" \
    --dry-run=client -o yaml | kubectl apply -f -

# 2. Deploy ModelServer phục vụ Qwen3-0.6B trên CPU
export REPO_ROOT=/home/nhan/Downloads/agentic_ai/agentic_ai/llm-d
export GUIDE_NAME="optimized-baseline"
export ACCELERATOR_TYPE=cpu
export MODEL_SERVER=vllm

kubectl apply -n ${NAMESPACE} -k ${REPO_ROOT}/guides/${GUIDE_NAME}/modelserver/${ACCELERATOR_TYPE}/${MODEL_SERVER}/

# 3. Tối ưu hóa định mức CPU/RAM cho máy e2-standard-4 (2 vCPUs / 4GiB)
kubectl set resources deployment optimized-baseline-cpu-vllm-decode -n ${NAMESPACE} --requests=cpu=2,memory=4Gi --limits=cpu=3,memory=6Gi
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
2. **Stage 2 (Test):** Chạy tự động **36 test cases** Pytest (`pytest tests/ -v`).
3. **Stage 3 (Build & Push):** Đóng gói và đẩy 4 images (`feature-api`, `drift-api`, `ecom-mcp`, `drift-mcp`) lên Docker Hub.
4. **Stage 4 (Tag Release):** Gắn Semantic Tag Release (`vX.Y.Z`) lên GitHub.
5. **Stage 5 (Deploy):** Tự động áp dụng toàn bộ manifests ứng dụng lên K8s:
   - Triển khai Backend REST APIs & NGINX Ingress (`apps/deployments/`).
   - Triển khai ModelConfig & AgentGateway (`agentic_ai/model-config/`, `agentgateway-routing.yaml`, `agentgateway_policy.yaml`).
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
Truy cập: **`http://localhost:16686`** ➔ Chọn service `ecom-agent-service` hoặc `feature-api` ➔ Xem toàn bộ timeline chi tiết từng mili-giây truy vấn Redis và Trino.

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

### 6. Kiểm Tra Tự Động Co Giãn Tải KEDA & Rate Limiting 10 RPS
Lấy Public IP của NGINX Ingress:
```bash
INGRESS_IP=$(kubectl get ingress ecom-agentic-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Gửi 15 request liên tục trong 1 giây để kiểm tra Rate Limiting (10 RPS)
for i in {1..15}; do curl -s -o /dev/null -w "%{http_code}\n" http://${INGRESS_IP}/api/v1/features/health; done
# Kết quả: 10 request đầu trả về 200 OK, các request vượt ngưỡng trả về 429 Too Many Requests

# Kiểm tra trạng thái KEDA tự động scale Pods từ 1 -> 5 khi tải tăng
kubectl get scaledobject -A
kubectl get pods -l app=feature-api -w
```
