# Sử dụng Airflow gốc làm nền tảng
FROM apache/airflow:2.7.1

# Chuyển sang quyền Root để cài đặt phần mềm lõi
USER root

# Cài đặt Java (cho Spark) và procps (để sửa lỗi lệnh ps)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     default-jre-headless \
     procps \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Trả lại quyền user mặc định cho Airflow
USER airflow

# Thiết lập biến môi trường Java
ENV JAVA_HOME=/usr/lib/jvm/default-java