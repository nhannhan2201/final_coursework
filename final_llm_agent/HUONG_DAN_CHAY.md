# 📘 HƯỚNG DẪN TRIỂN KHAI TOÀN DIỆN & MINH CHỨNG DỰ ÁN (MASTER DEPLOYMENT GUIDE)

Tài liệu này cung cấp quy trình triển khai chi tiết **từ đầu đến cuối (A đến Z)**, từng bước một (**19 bước, 9 giai đoạn**), kèm hướng dẫn chi tiết về **những gì cần chụp màn hình (Capture)** và **file báo cáo tương ứng** cần đính kèm để thỏa mãn 100% các tiêu chí trong Rubric chấm điểm đồ án.

---

## 📋 DANH SÁCH CÁC BƯỚC THỰC THI & CHỤP MINH CHỨNG

### 🏁 Giai Đoạn 1: Kiểm Thử Độc Lập & Xác Minh Cục Bộ (Local Testing)

#### **Bước 1: Chạy Unit Tests & Đo Lường Độ Phủ Mã Nguồn (Code Coverage)**
* **Hành động:** Chạy bộ kiểm thử tự động 31 bài Unit Tests cho API và MCP Servers.
  ```bash
  export PYTHONPATH=.
  pytest tests/unit/ -v --cov=apps --cov-report=term-missing
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Bảng tổng hợp của `pytest-cov` hiển thị danh sách các file trong `apps/` và tỷ lệ coverage chung **đạt trên 90%** (ví dụ: `apps/feature_api.py`, `apps/drift_api.py`).
  * Đoạn code test có sử dụng `@pytest.mark.parametrize` để minh chứng kỹ thuật phân tích giá trị biên (Boundary Value) và phân hoạch tương đương (Equivalence Partitioning).
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/Testing.md`](./docs/Testing.md) (Mục 1 & 2).

#### **Bước 2: Chạy Kiểm Thử Đột Biến (Mutation Testing) & Property-Based Testing**
* **Hành động:**
  1. Cài đặt các gói phụ thuộc bổ sung cho môi trường:
     ```bash
     python -m pip install mutmut hypothesis
     ```
  2. Chạy công cụ `mutmut` thông qua trình thông dịch của môi trường để chèn đột biến giả lập lỗi code và đánh giá bộ test:
     ```bash
     python -m mutmut run
     python -m mutmut results
     ```
  3. Chạy bài kiểm thử sinh dữ liệu ngẫu nhiên có quy luật sử dụng thư viện `Hypothesis`:
     ```bash
     pytest tests/property/ -v
     ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Terminal hiển thị Mutation Score của `mutmut` **đạt trên 80%** (số lượng đột biến bị "tiêu diệt" - killed mutants).
  * Đoạn mã nguồn test sử dụng decorator `@given` của Hypothesis để thực hiện Property-based testing.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/Testing.md`](./docs/Testing.md) (Mục 3 & 4).

---

### 🏗️ Giai Đoạn 2: Cấp Phát Hạ Tầng & Triển Khai Data Stack Bằng IaC (Infrastructure as Code)

#### **Bước 3: Cấp Phát Máy Chủ Ảo VM & Cụm GKE Đám Mây Bằng Terraform**
* **Hành động:** Áp dụng Terraform để khởi tạo máy ảo Compute Engine VM và cụm Kubernetes GKE kèm GPU Node Pool (phục vụ mô hình vLLM serving).
  ```bash
  cd iac/terraform
  terraform init
  terraform apply -auto-approve
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Dòng log kết thúc thành công: `Apply complete! Resources: X added, 0 changed, 0 destroyed`.
  * Trang quản trị Google Cloud Console hiển thị cụm GKE với nhóm máy ảo GPU và Compute Engine VM đang chạy.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/iac_ansible_terraform.md`](./docs/iac_ansible_terraform.md) (Mục 1).

#### **Bước 4: Tự Động Dựng Data Stack Trực Tiếp Trên VM Bằng Ansible**
* **Hành động:** Khởi chạy playbook Ansible để tự động SSH vào VM trên GCP, cài Docker, đồng bộ mã nguồn `minicoursework` sang thư mục `/opt/ecom_datalake` trên VM, và bật toàn bộ Data Stack (MinIO, Trino, Airflow, DataHub, Redis) bằng Docker Compose.
  ```bash
  cd ../ansible
  ansible-playbook -i inventory.ini site.yml
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Terminal hiển thị bảng kết quả `PLAY RECAP` với trạng thái `failed=0` cho máy chủ VM đích.
  * Màn hình log Ansible thể hiện việc tự động đồng bộ code và kích hoạt Docker Compose cho Data Stack.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/iac_ansible_terraform.md`](./docs/iac_ansible_terraform.md) (Mục 2).

---

### 📊 Giai Đoạn 3: Sinh Dữ Liệu & Giả Lập Trôi Lệch Dữ Liệu (Data Drift)

#### **Bước 5: Khởi Chạy Data Generator & Giả Lập Data Drift Trên VM**
* **Hành động:** Sau khi Ansible đã dựng xong Data Stack trên VM, thực thi script sinh dữ liệu giả lập có cấu hình drift và kiểm tra bảng đặc trưng nhãn (label table) đẩy trực tiếp lên MinIO (`landing-zone`).
  ```bash
  # Chạy sinh dữ liệu qua Airflow Scheduler container trên VM
  docker exec -it ecom_airflow_scheduler python /opt/airflow/project/data_generation/main.py
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Nội dung tệp cấu hình sinh dữ liệu `generator_config.yaml`.
  * Kết quả bảng nhãn (Label Table) sau khi thực hiện ghép nối (Merge / Join) khóa `id` với nhãn phục vụ huấn luyện mô hình.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/data_generation.md`](./docs/data_generation.md).

---

### 🔄 Giai Đoạn 4: Đóng Gói Ảo Hóa & Tích Hợp Liên Tục (CI/CD)

#### **Bước 6: Tự Động Hóa Build & Deploy Thông Qua GitHub Actions / Jenkins**
* **Hành động:** Push code lên repository để trigger CI/CD pipeline tự động chạy kiểm thử, đóng gói docker image, và cập nhật ứng dụng.
  ```bash
  git add .
  git commit -m "feat: trigger production pipeline"
  git push origin feature
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Sơ đồ chạy thành công (màu xanh lá cây) của các pipelines:
    1. Pipeline build/test và deploy các API & MCP Servers.
    2. Pipeline deploy các tác vụ Kubernetes Jobs đồng bộ dữ liệu (Push stream feature sang Offline/Online store).
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/cicd.md`](./docs/cicd.md).

---

### 🤖 Giai Đoạn 5: Triển Khai AI Serving & Kubernetes-native Agents

#### **Bước 7: Triển Khai Custom Model Server (llm-d) & Model Config**
* **Hành động:** Cài đặt `kagent-crds` và `agentgateway` bằng Helm theo đúng giáo trình thầy dạy, sau đó deploy cụm Model Server running mô hình Qwen3-0.6B tự phục vụ (Self-host) và áp dụng cấu hình Gateway định tuyến.
  ```bash
  # 1. Cài đặt kagent CRDs & Operator qua Helm
  helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds --namespace kagent --create-namespace
  helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent --namespace kagent --set global.agents.enabled=false --reuse-values

  # 2. Cài đặt Gateway API CRDs & AgentGateway qua Helm (theo giáo trình)
  kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
  AGENTGATEWAY_VERSION=v1.3.1
  helm upgrade --install agentgateway-crds oci://cr.agentgateway.dev/charts/agentgateway-crds --namespace agentgateway-system --create-namespace --version ${AGENTGATEWAY_VERSION}
  helm upgrade --install agentgateway oci://cr.agentgateway.dev/charts/agentgateway --namespace agentgateway-system --create-namespace --version ${AGENTGATEWAY_VERSION} --set inferenceExtension.enabled=true

  # 3. Deploy Custom Model Server
  kubectl create namespace llm-d-quickstart --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply -f deployments/llm_d_modelserver.yaml
  
  # 4. Cấu hình Secret, ModelConfig toàn cục và AgentGateway Routing
  kubectl apply -f ecom-mcp/deployments/groq-secret.yaml
  kubectl apply -f ecom-mcp/deployments/model-config.yaml
  kubectl apply -f agentgateway-routing.yaml
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Output của lệnh `kubectl get deployment -n llm-d-quickstart` và `kubectl get httproute -n agentgateway-system` chứng minh cấu hình định tuyến của custom model server đã được apply thành công.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/llm_inference_platform.md`](./docs/llm_inference_platform.md).

#### **Bước 8: Cài Đặt KAgent, Multi-replica Agents Với Phân Quyền Sandbox & Registry**
* **Hành động:** 
  1. Triển khai các agents dưới dạng Multi-replica, thiết lập sandbox bảo mật (`runAsNonRoot: true`, cấm truy cập hệ thống file gốc, Drop capabilities):
     ```bash
     kubectl apply -f ecom-mcp/deployments/agent.yaml
     kubectl apply -f drift-mcp/deployments/agent.yaml
     kubectl apply -f coordinator-agent/deployments/agent.yaml
     ```
  2. Deploy AgentRegistry thông qua Helm (theo giáo trình):
     ```bash
     helm upgrade -i agentregistry oci://ghcr.io/agentregistry-dev/agentregistry/charts/agentregistry \
         --namespace agentregistry \
         --create-namespace \
         --set config.jwtPrivateKey=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
         --set image.tag=v0.3.3 \
         --set database.host=postgres-pgvector.agentregistry.svc.cluster.local \
         --set database.password=agentregistry \
         --set database.sslMode=disable
     ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Màn hình thể hiện **Registry đã được deploy thành công** (qua giao diện UI hoặc CLI `kubectl get all -n agentregistry`).
  * Lệnh `kubectl get pods -n kagent` hiển thị **Multi-replica active** (ví dụ: `ecom-agent-deployment` có 3 replicas chạy song song).
  * Đoạn cấu hình YAML chứng minh **Agent được giới hạn quyền qua Sandbox** (`securityContext` cô lập).
  * Giao diện UI Registry hiển thị danh sách các Agent đã được đăng ký công khai (Catalog).
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/agent_registry.md`](./docs/agent_registry.md).

#### **Bước 9: Cấu Hình Agent Warm Up & Tối Ưu Cold Start**
* **Hành động:** Áp dụng cấu hình Warm Up cho Agent pods: initContainer pre-warm kết nối, startupProbe cho khởi tạo nội bộ, và KEDA warm pool (idle replicas = 1).
  ```bash
  kubectl apply -f deployments/warmup_config.yaml

  # Kiểm tra initContainer warmup đã chạy thành công
  kubectl logs -n kagent <agent-pod-name> -c warmup-init
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Benchmark trước/sau Warm Up: thời gian first response giảm từ ~35s xuống ~1s.
  * `kubectl get scaledobject -n kagent` hiển thị KEDA warm pool đang hoạt động (`idleReplicaCount: 1`).
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/warmup_benchmark.md`](./docs/warmup_benchmark.md).

---

### 🌐 Giai Đoạn 6: Biên Ingress Gateway, Bảo Mật & Tự Động Co Giãn

#### **Bước 10: Triển Khai NGINX Ingress Gateway, Rate Limiting & HTTPS**
* **Hành động:** Thiết lập cổng Ingress mặt tiền, giới hạn tần suất yêu cầu 10 RPS để chống DDoS, phân quyền đăng nhập Basic Auth cho UI thử nghiệm.
  ```bash
  kubectl apply -f deployments/nginx_ingress.yaml
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Kết quả chạy curl liên tục thể hiện việc **Rate limit 10 RPS hoạt động chính xác** (nhận về mã lỗi HTTP `429 Too Many Requests` khi gửi yêu cầu dồn dập).
  * Hộp thoại Basic Authentication yêu cầu nhập Username/Password khi truy cập UI chat.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/ingress_gateway.md`](./docs/ingress_gateway.md).

#### **Bước 11: Tự Động Co Giãn Nhờ KEDA (Kubernetes Event-Driven Autoscaler)**
* **Hành động:** Cài đặt KEDA và áp dụng ScaledObjects tự động scale pods dựa trên chỉ số RPS từ Prometheus.
  ```bash
  kubectl apply -f deployments/keda/
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Trạng thái co giãn thực tế: Khi chạy test tải, số lượng pods tự động tăng từ 1 lên 5 (`kubectl get pods -w` / Grafana co giãn).
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/agent_registry.md`](./docs/agent_registry.md) (Mục Multi-replica & KEDA).

---

### 📊 Giai Đoạn 7: Giám Sát, Logging, Tracing, A/B Testing & Quản Trị Dữ Liệu

#### **Bước 12: Triển Khai EFK Logging Stack & Jaeger Distributed Tracing**
* **Hành động:** Deploy hệ thống thu thập log tập trung (EFK) và hệ thống theo dõi luồng yêu cầu phân tán (Jaeger).
  ```bash
  # 1. Deploy EFK Stack (Elasticsearch + Fluent Bit + Kibana)
  kubectl apply -f deployments/efk_logging.yaml

  # 2. Deploy Jaeger + OpenTelemetry Collector
  kubectl apply -f deployments/jaeger_tracing.yaml
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Giao diện **Kibana Discover** hiển thị logs từ các pods (`feature-api`, `drift-api`, `ecom-mcp`).
  * Giao diện **Jaeger UI** hiển thị distributed trace của một request đi qua Feature API → Redis → Trino.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/logging_tracing.md`](./docs/logging_tracing.md).

#### **Bước 13: Đo Lường & Giám Sát Metrics Hệ Thống (Observability)**
* **Hành động:** Port-forward các dịch vụ giám sát và quan sát chỉ số vận hành thời gian thực.
  ```bash
  # Grafana Metrics Dashboard
  kubectl port-forward -n default svc/grafana 3000:80

  # Kibana Logging Dashboard
  kubectl port-forward -n logging svc/kibana 5601:5601

  # Jaeger Tracing Dashboard
  kubectl port-forward -n tracing svc/jaeger 16686:16686
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Panel hiển thị **Web API metrics** (RPS, CPU/RAM) — Grafana `http://localhost:3000`.
  * Panel hiển thị **LLM telemetry** (độ trễ TTFT, số lượng input/output tokens) — Grafana.
  * Panel hiển thị **Agent telemetry** (số lần Coordinator Agent / Ecom Agent được gọi, số lần MCP tools được chạy) — Grafana.
  * **Logs Dashboard** — Kibana `http://localhost:5601`.
  * **Traces Dashboard** — Jaeger `http://localhost:16686`.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/observability.md`](./docs/observability.md) & [`docs/logging_tracing.md`](./docs/logging_tracing.md).


#### **Bước 15: Đồng Bộ Dữ Liệu RAG & Đảm Bảo Data Governance Trên DataHub**
* **Hành động:** Khởi chạy Airflow DAG nạp dữ liệu, tạo embeddings vector lưu vào Feast, đồng bộ metadata sang DataHub.
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Màn hình Airflow DAG chạy thành công 100%.
  * **Sơ đồ Data Lineage và Assertions trên DataHub** thể hiện nguồn gốc từ text ➔ Gold ➔ Feast Feature Store.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/data_governance.md`](./docs/data_governance.md).

#### **Bước 16: Bảo Mật Secrets Tập Trung & Ứng Dụng Design Patterns**
* **Hành động:** 
  1. Kiểm tra cấu hình Secrets tập trung trong cụm.
  2. Xác định các Class trong mã nguồn thực thi Strategy Pattern và Adapter Pattern.
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Màn hình quản trị Secrets tập trung (kubectl / Vault).
  * Đoạn mã nguồn trong dự án thể hiện cách viết Strategy Pattern (chọn thuật toán drift) và Adapter Pattern (thích ứng các database Feature Store).
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/security_secrets.md`](./docs/security_secrets.md) & [`docs/design_patterns.md`](./docs/design_patterns.md).

---

### 💬 Giai Đoạn 8: Tương Tác Trực Tiếp & Kiểm Nghiệm Nghiệp Vụ (Chat & Notebook Validation)

#### **Bước 17: Chạy UI Chat Trực Tiếp Với Agent**
* **Hành động:** 
  1. Port-forward UI chat:
     ```bash
     kubectl port-forward -n kagent svc/kagent-ui 8080:8080
     ```
  2. Mở trình duyệt truy cập `http://localhost:8080` và thực hiện trò chuyện với Coordinator Agent.
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Giao diện UI Chat hiển thị cuộc trò chuyện thực tế: Người dùng yêu cầu tư vấn mua sắm, Agent tự động gọi MCP tools lấy dữ liệu từ Feature Store và trả về kết quả cá nhân hóa.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/agent_registry.md`](./docs/agent_registry.md).

#### **Bước 18: Chạy Jupyter Notebook Demo Agent Tương Tác Với MCP Servers**
* **Hành động:** Khởi chạy Jupyter Notebook để minh chứng Agent gọi trực tiếp MCP Tools kéo dữ liệu từ Feature Store, phân tích Drift, và RAG context retrieval.
  ```bash
  # Port-forward KAgent API trước
  kubectl port-forward -n kagent svc/kagent-controller-manager 8083:8083

  # Mở Jupyter Notebook
  jupyter notebook notebooks/agent_demo.ipynb
  ```
* **📸 CẦN CAPTURE MÀN HÌNH:**
  * Output của notebook cell gọi `get_customer_shopping_context` → kết quả Feature Store trả về.
  * Output của notebook cell gọi `detect_feature_drift` → kết quả Drift Detection.
  * Output của notebook cell Coordinator Agent tổng hợp đa MCP tools.
* **📂 LƯU VÀO FILE BÁO CÁO:** [`docs/agent_registry.md`](./docs/agent_registry.md) (Mục Jupyter Notebook Demo).

---

### 🧹 Giai Đoạn 9: Dọn Dẹp Tài Nguyên Đám Mây (Clean Up)

#### **Bước 19: Destroy Hạ Tầng Tránh Phát Sinh Chi Phí**
* **Hành động:** Thực hiện dọn dẹp sau khi kiểm tra xong:
  ```bash
  cd iac/terraform
  terraform destroy -auto-approve
  ```
