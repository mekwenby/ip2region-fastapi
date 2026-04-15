FROM python:3.10 AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.10

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

COPY main.py .
COPY python/ ./python/
COPY data/ ./data/
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FASTAPI_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f -X GET http://localhost:5000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
