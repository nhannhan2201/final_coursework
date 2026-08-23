# 🔐 Centralized Secret Management Report

Báo cáo cấu hình quản lý mã bí mật tập trung (Secrets) nhằm loại bỏ hoàn toàn việc lưu trữ các API Keys, thông tin đăng nhập cơ sở dữ liệu (Database Credentials) trực tiếp trong mã nguồn dự án.

---

## 🏛️ 1. Giải Pháp Quản Lý Mã Bí Mật Tập Trung (Kubernetes Secrets)
Hệ thống sử dụng **Kubernetes Secret Management** để lưu giữ các API keys, mật khẩu database của AgentRegistry, `kubeconfig` của CI/CD runner, và thông tin đăng nhập LLM / OTel:

- `agentic_ai/model-config/llm-secret.yaml`: Quản lý API Key cho LLM Endpoint.
- `observability/helm_charts/otel/values.yaml`: Quản lý Secret xác thực `langfuse-otel-auth` và `elasticsearch-es-elastic-user`.
- `cicd/`: Quản lý `jenkins-token` RBAC Secret.

```bash
# Kiểm tra danh sách Secrets trong namespace kagent và monitoring:
kubectl get secrets -n kagent
kubectl get secrets -n monitoring
```

> 📸 **MINH CHỨNG QUẢN LÝ SECRETS TẬP TRUNG:**
>
> *(Chèn ảnh chụp màn hình terminal lệnh `kubectl get secrets -n kagent` và `kubectl get secrets -n monitoring` tại đây)*
> 
> ![Kubernetes Secrets Management](screenshot_kubernetes_secrets.png)
