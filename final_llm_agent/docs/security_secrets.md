# 🔐 Centralized Secret Management & Security Sandboxing Report

Báo cáo cấu hình quản lý thông tin bảo mật tập trung (**Kubernetes Secrets**) và cơ chế cô lập an toàn (**Security Sandboxing**) cho các tác tử AI Agent.

---

## 🏛️ 1. Quản Lý Mã Bí Mật Tập Trung (Kubernetes Secrets)

Hệ thống loại bỏ hoàn toàn việc lưu trữ cứng mật khẩu, API keys hay thông tin chứng thực trong mã nguồn, thay vào đó nạp thông qua Kubernetes Secrets:

1. **HuggingFace Access Token (`llm-d-hf-token`):** Cung cấp quyền tải trọng số mô hình cho pod `vLLM decode`.
2. **Jenkins CI/CD Token (`jenkins-token`):** ServiceAccount Token có thẩm quyền kiểm soát việc cập nhật các Deployment trên cụm.
3. **Database Credentials:** Thông tin kết nối Redis, Trino và MinIO S3 được nạp tự động qua biến môi trường của Pod.

```bash
# Kiểm tra danh sách Secrets an toàn trong cụm:
kubectl get secrets -n llm-d-quickstart
kubectl get secrets -n kagent
kubectl get secrets -n monitoring
```

---

## 🛡️ 2. Cơ Chế Cô Lập Sandbox (SecurityContext)

Các Pod Agent và FastMCP Tool Servers đều tuân thủ nguyên tắc phân quyền tối thiểu (**Principle of Least Privilege**):

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

- **`runAsNonRoot: true`:** Ngăn chặn việc container chạy với quyền root của máy chủ host.
- **`readOnlyRootFilesystem: true`:** Khóa tệp hệ thống chỉ đọc, vô hiệu hóa khả năng tiêm nhiễm hoặc chỉnh sửa nhị phân trái phép từ các đoạn mã độc.
- **`capabilities.drop: ["ALL"]`:** Tước bỏ toàn bộ đặc quyền kernel không cần thiết của Linux.
