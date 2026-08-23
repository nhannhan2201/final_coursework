#!/usr/bin/env bash
# Script tự động kích hoạt Conda và chạy sinh dữ liệu mẫu locally trên máy thật

# Thoát ngay lập tức nếu gặp lỗi
set -e

# Xác định đường dẫn thư mục hiện tại
CDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$CDIR"

echo "======================================================="
echo "🚀 BẮT ĐẦU CHẠY LOCAL GENERATOR VỚI CONDA ENV"
echo "======================================================="

# 1. Kích hoạt môi trường conda 'learn_database' nếu chưa được kích hoạt
TARGET_ENV="learn_database"

if [ "$CONDA_DEFAULT_ENV" != "$TARGET_ENV" ]; then
    echo "⏳ Đang thử kích hoạt môi trường conda '$TARGET_ENV'..."
    
    # Tìm đường dẫn conda base để lấy profile script của conda
    if command -v conda &> /dev/null; then
        CONDA_BASE=$(conda info --base)
        source "$CONDA_BASE/etc/profile.d/conda.sh"
        conda activate "$TARGET_ENV"
        echo "🔌 Đã kích hoạt conda env: $CONDA_DEFAULT_ENV"
    else
        echo "⚠️ Cảnh báo: Không tự động định vị được lệnh conda."
        echo "👉 Vui lòng chạy lệnh 'conda activate learn_database' bằng tay trước khi chạy script này."
    fi
else
    echo "✔️ Đang ở trong môi trường Conda: $CONDA_DEFAULT_ENV"
fi

# 2. Thiết lập biến môi trường trỏ kết nối về cổng MinIO máy thật (9005)
export MINIO_ENDPOINT="http://localhost:9005"

# 3. Khởi chạy file sinh dữ liệu
echo "🏃 Đang chạy kịch bản sinh dữ liệu mẫu..."
python data_generation/main.py

echo "======================================================="
echo "✅ HOÀN THÀNH! Dữ liệu đã được đẩy lên MinIO (Port 9005)."
echo "======================================================="
