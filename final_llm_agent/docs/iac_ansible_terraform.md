# 🛠️ Infrastructure as Code (IaC) — Terraform & Ansible Report

Tài liệu báo cáo chi tiết thiết lập hạ tầng đám mây tự động bằng Terraform và cấu hình máy chủ ảo tự động sử dụng Ansible.

---

## ☁️ 1. Cấp Phát Tài Nguyên Cloud Với Terraform (Terraform Setup GKE)
Sử dụng mã nguồn Terraform (`iac/terraform/`) để khởi tạo cụm Google Kubernetes Engine (GKE) cùng với các GPU Node Pools (NVIDIA Tesla T4/L4) nhằm tăng tốc xử lý cho vLLM model server.

> 📸 **[CAPTURE MINH CHỨNG - TERRAFORM APPLY SUCCESS]**
> *Hãy chụp màn hình kết quả chạy lệnh `terraform apply` thành công hiển thị số tài nguyên đã thêm (`Apply complete! Resources: X added, 0 changed, 0 destroyed`).*
> 
> **🖼️ Ảnh minh chứng:**
> *(Dán ảnh vào dòng này)*

---

## 📦 2. Cấu Hình Máy Chủ Tự Động Với Ansible (Ansible VM Configuration)
Sử dụng Ansible playbook (`iac/ansible/`) để cấu hình hệ điều hành, cài đặt driver NVIDIA CUDA, thiết lập Docker, Helm và chuẩn bị môi trường chạy Kubernetes cục bộ.

> 📸 **[CAPTURE MINH CHỨNG - ANSIBLE PLAYBOOK SUCCESS]**
> *Hãy chụp màn hình kết quả chạy lệnh `ansible-playbook -i inventory.ini site.yml` hiển thị phần tổng kết `PLAY RECAP` với trạng thái `failed=0`.*
> 
> **🖼️ Ảnh minh chứng:**
> *(Dán ảnh vào dòng này)*
