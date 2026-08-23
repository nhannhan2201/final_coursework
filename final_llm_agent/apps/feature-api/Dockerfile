FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    redis \
    trino[sqlalchemy] \
    requests \
    prometheus_client

COPY apps/__init__.py /app/apps/__init__.py
COPY apps/feature_api.py /app/apps/feature_api.py
COPY apps/telemetry.py /app/apps/telemetry.py

EXPOSE 8000

CMD ["uvicorn", "apps.feature_api:app", "--host", "0.0.0.0", "--port", "8000"]
