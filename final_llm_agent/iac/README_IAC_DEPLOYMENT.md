# 📘 HƯỚNG DẪN VẬN HÀNH HẠ TẦNG CLOUD (IaC DEPLOYMENT GUIDE)

Tài liệu này tổng hợp **toàn bộ quy trình chuẩn** để cấp phát tài nguyên Google Cloud (GCP) bằng **Terraform**, tự động cấu hình Data Stack bằng **Ansible**, build & push Docker Image lên **Docker Hub cá nhân (`nhannguyen2201`)**, và triển khai cụm **KAgent + LLM-d + Microservices** trên **GKE (Google Kubernetes Engine)** bằng **Helm**.

---

## 🛠️ TIỀN ĐỀ: CÀI ĐẶT CÔNG CỤ LOCAL (PREREQUISITES)

```bash
# 1. Cài đặt Ansible Core engine
pip install ansible-core

# 2. Cài đặt collection ansible.posix (cho module synchronize/rsync)
ansible-galaxy collection install ansible.posix
```

---

## 📌 BƯỚC 1: ĐĂNG NHẬP GOOGLE CLOUD (AUTHENTICATION)

```bash
gcloud auth application-default login
```

---

## 📌 BƯỚC 2: CẤP PHÁT HẠ TẦNG CLOUD VỚI TERRAFORM

```bash
cd iac/terraform
terraform init
terraform apply
```

---

## 📌 BƯỚC 3: CẤU HÌNH ANSIBLE INVENTORY WITH GCP OS LOGIN

File `iac/ansible/inventory.ini`:
```ini
[data_stack_vm]
35.247.171.59 ansible_user=nhannhutnhat2201_gmail_com ansible_ssh_private_key_file=~/.ssh/google_compute_engine
```

---

## 📌 BƯỚC 4: TỰ ĐỘNG DỰNG DATA STACK BẰNG ANSIBLE

```bash
cd iac/ansible
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory.ini site.yml
```

---

## 📌 BƯỚC 5: BUILD & PUSH DOCKER IMAGES (ĐỒNG BỘ 1 CÁCH DUY NHẤT VỚI BUILD.SH)

### 🔹 Đăng nhập Docker Hub (1 lần duy nhất)
```bash
docker login
```

### 🔹 Build & Push Dịch vụ 1: `feature-api`
```bash
cd /home/nhan/Projects/final_coursework/final_llm_agent/apps/feature-api
bash build.sh
```

### 🔹 Build & Push Dịch vụ 2: `drift-api`
```bash
cd /home/nhan/Projects/final_coursework/final_llm_agent/apps/drift-api
bash build.sh
```

### 🔹 Build & Push Dịch vụ 3: `ecom-mcp`
```bash
cd /home/nhan/Projects/final_coursework/final_llm_agent/ecom-mcp
bash build.sh
```

### 🔹 Build & Push Dịch vụ 4: `drift-mcp`
```bash
cd /home/nhan/Projects/final_coursework/final_llm_agent/drift-mcp
bash build.sh
```

---

## 📌 BƯỚC 6: CÀI ĐẶT KAGENT & LLM-D INFERENCE GATEWAY TRÊN GKE

### 🔹 Bước 6.1: Kết nối `kubectl` tới cụm GKE Cluster
```bash
gcloud container clusters get-credentials ecom-kagent-gke-cluster --zone asia-southeast1-a --project k8s-sentiment
```

### 🔹 Bước 6.2: Cài đặt KAgent CRDs & KAgent Operator qua Helm
```bash
# 1. Install KAgent CRDs
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
    --namespace kagent \
    --create-namespace

# 2. Install KAgent Operator & UI
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --namespace kagent \
  --set global.agents.enabled=false

# 3. Create Groq API Secret placeholder in kagent namespace
kubectl create secret generic groq-secret -n kagent --from-literal=api-key="placeholder" --dry-run=client -o yaml | kubectl apply -f -
```

### 🔹 Bước 6.3: Cài đặt LLM-d Inference Gateway & ModelServer
```bash
# 1. Khởi tạo namespace llm-d-quickstart
export NAMESPACE=llm-d-quickstart
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 2. Cài đặt Gateway API & GAIE CRDs
GATEWAY_API_VERSION=v1.5.1
GAIE_VERSION=v1.5.0
kubectl apply -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml" -n "${NAMESPACE}"
kubectl apply -f "https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/${GAIE_VERSION}/v1-manifests.yaml" -n "${NAMESPACE}"

# 3. Cài đặt AgentGateway via Helm
AGENTGATEWAY_VERSION=v1.3.1
helm upgrade --install agentgateway-crds oci://cr.agentgateway.dev/charts/agentgateway-crds --namespace agentgateway-system --create-namespace --version ${AGENTGATEWAY_VERSION}
helm upgrade --install agentgateway oci://cr.agentgateway.dev/charts/agentgateway --namespace agentgateway-system --create-namespace --version ${AGENTGATEWAY_VERSION} --set inferenceExtension.enabled=true

# 4. Khởi tạo Secret HuggingFace Token & Routing
export HF_TOKEN=YOUR_HUGGINGFACE_TOKEN
kubectl create secret generic llm-d-hf-token --from-literal="HF_TOKEN=${HF_TOKEN}" --namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f agentgateway-routing.yaml

# 5. Triển khai LLM ModelServer
kubectl apply -f deployments/llm_d_modelserver.yaml

# 6. Tải mô hình Qwen 1.5B vào ModelServer
kubectl exec -n llm-d-quickstart deploy/llm-d-modelserver -- ollama pull qwen2.5:1.5b
```

---

## 📌 BƯỚC 7: TRIỂN KHÁI BACKEND APIS & AGENTS LÊN GKE

```bash
cd /home/nhan/Projects/final_coursework/final_llm_agent

# Deploy Backend APIs
kubectl apply -f deployments/backend/

# Deploy AI Agents, MCP Servers & Model Configs
kubectl apply -f ecom-mcp/deployments/
kubectl apply -f drift-mcp/deployments/
kubectl apply -f coordinator-agent/deployments/

# Deploy Nginx Ingress Gateway
kubectl apply -f deployments/nginx_ingress.yaml
```

---

## 📌 BƯỚC 8: TRUY CẬP HỆ THỐNG & KIỂM TRA

### 🔹 Mở Port-Forwarding KAgent Web UI
```bash
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

### 🔹 Danh sách Endpoints & Dashboards Quản trị
* 🤖 **KAgent Web UI:** `http://localhost:8080` (Môi trường tương tác AI Agents & MCP Tools)
* ⚡ **Airflow Workflow UI:** `http://<VM_IP>:8081` (Tài khoản: `admin` / `admin`)
* 🗄️ **MinIO Lakehouse Console:** `http://<VM_IP>:9001` (Tài khoản: `admin` / `admin123456`)
* 📊 **Trino Query Engine UI:** `http://<VM_IP>:8085`

### 🔹 Kiểm tra trạng thái Pods & Services
```bash
kubectl get pods -n kagent
kubectl get pods -n default
kubectl get pods -n llm-d-quickstart
```

---

## 📌 BƯỚC 9: HƯỚNG DẪN TẮT/MỞ LẠI HẠ TẦNG VÀ NẠP DỮ LIỆU (RESTART & DATA GUIDE)

### 🔹 1. Tắt tạm thời tài nguyên Cloud (Tránh tốn tiền qua đêm)
```bash
# Tắt Compute Engine VM
gcloud compute instances stop ecom-data-stack-vm --zone=asia-southeast1-a

# Thu hồi Pods trên cụm GKE về 0 nodes
gcloud container clusters resize ecom-kagent-gke-cluster --num-nodes=0 --zone=asia-southeast1-a --quiet
```

### 🔹 2. Bật lại tài nguyên Cloud & Cập nhật IP
```bash
# Bật lại Compute Engine VM
gcloud compute instances start ecom-data-stack-vm --zone=asia-southeast1-a

# Lưu ý: Kiểm tra IP mới của VM
gcloud compute instances list --filter="name=ecom-data-stack-vm"

# Khôi phục cụm GKE Cluster lên 2 nodes
gcloud container clusters resize ecom-kagent-gke-cluster --num-nodes=2 --zone=asia-southeast1-a --quiet

# Cập nhật IP mới vào deployments và apply lại GKE
kubectl apply -f deployments/backend/
```

### 🔹 3. Sinh dữ liệu mẫu E-Commerce 90 ngày (Data Generation)
Bạn có thể tự chạy lệnh sinh dữ liệu từ máy local để nạp vào MinIO & Redis:
```bash
cd /home/nhan/Projects/final_coursework/minicoursework/data_generation
MINIO_ENDPOINT="http://<VM_IP>:9005" /home/nhan/miniconda3/envs/learn_database/bin/python main.py
```

### 🔹 4. Kích hoạt Airflow DAGs tự động hóa
1. Truy cập Airflow Web UI tại: **`http://<VM_IP>:8081`** (Login: `admin` / `admin`).
2. Bật công tắc (Toggle ON) DAG `ecom_data_pipeline`.
3. Nhấn biểu tượng nút Play (▶️) chọn **Trigger DAG** để chạy quy trình biến đổi dữ liệu Delta Lake.
