# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

# Copy source
COPY src/ ./src/
COPY config/ ./config/
COPY tests/fixtures/ ./tests/fixtures/

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "src.agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
