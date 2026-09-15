#!/usr/bin/env bash
# ==============================================================================
# Cầu Nối Mạng Nội Bộ Cho Môi Trường Local (Kind -> Docker Compose Host)
# Ánh xạ DNS redis-master.data-platform và trino-coordinator.data-platform
# về IP Gateway của Docker Host để FastMCP truy vấn được Redis & Trino.
# ==============================================================================
set -e

echo "🔍 Đang phát hiện IP Host từ mạng Kind..."
HOST_IP=$(docker inspect agentic-ai-control-plane -f '{{.NetworkSettings.Networks.kind.Gateway}}' 2>/dev/null || docker network inspect kind -f '{{with index .IPAM.Config 1}}{{.Gateway}}{{else}}{{(index .IPAM.Config 0).Gateway}}{{end}}' 2>/dev/null || echo "172.24.0.1")

echo "✅ IP Docker Host: ${HOST_IP}"

# Tạo namespace data-platform nếu chưa có
kubectl create ns data-platform --dry-run=client -o yaml | kubectl apply -f -

# Tạo Service và Endpoints cầu nối
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: redis-master
  namespace: data-platform
spec:
  ports:
    - name: redis
      port: 6379
      targetPort: 6379
---
apiVersion: v1
kind: Endpoints
metadata:
  name: redis-master
  namespace: data-platform
subsets:
  - addresses:
      - ip: ${HOST_IP}
    ports:
      - name: redis
        port: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: trino-coordinator
  namespace: data-platform
spec:
  ports:
    - name: http
      port: 8080
      targetPort: 8085
---
apiVersion: v1
kind: Endpoints
metadata:
  name: trino-coordinator
  namespace: data-platform
subsets:
  - addresses:
      - ip: ${HOST_IP}
    ports:
      - name: http
        port: 8085
YAML

echo "🎉 Đã thiết lập cầu nối dữ liệu thành công:"
echo "   - redis-master.data-platform.svc.cluster.local:6379 -> Host Redis:6379"
echo "   - trino-coordinator.data-platform.svc.cluster.local:8080 -> Host Trino:8085"
