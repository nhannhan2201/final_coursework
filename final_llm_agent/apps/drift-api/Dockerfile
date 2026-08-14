FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    scipy \
    numpy \
    redis \
    trino[sqlalchemy] \
    prometheus_client

COPY apps/__init__.py /app/apps/__init__.py
COPY apps/drift_api.py /app/apps/drift_api.py
COPY apps/telemetry.py /app/apps/telemetry.py

EXPOSE 8003

CMD ["uvicorn", "apps.drift_api:app", "--host", "0.0.0.0", "--port", "8003"]
