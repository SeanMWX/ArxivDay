FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_PORT=8000 \
    SYNC_DB_PATH=/data/sync.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data_api.py .

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "data_api.py", "--host", "0.0.0.0"]
