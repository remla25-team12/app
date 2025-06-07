# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /app


RUN apt-get update && \
    apt-get install -y \
      git \
      build-essential \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt



# Final stage
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .
COPY templates /app/templates

ENV MODEL_SERVICE_URL=http://model-service:8080/predict

CMD ["python", "app.py"]