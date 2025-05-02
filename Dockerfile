FROM python:3.11-slim

WORKDIR /app

# Install Git so pip can install from Git-based URLs
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app and templates
COPY . .
COPY templates /app/templates

ENV MODEL_SERVICE_URL=http://model-service:8080/predict

CMD ["python", "app.py"]
