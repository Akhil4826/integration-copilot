# Multi-stage lightweight Dockerfile for Integration Copilot
FROM python:3.11-slim

# Prevents Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PYTHONPATH=/app

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and migrations
COPY pyproject.toml alembic.ini .
COPY app/ app/
COPY mcp_server/ mcp_server/
COPY evaluation/ evaluation/
COPY scripts/ scripts/
COPY data/ data/

# Install application package in editable mode
RUN pip install --no-cache-dir -e .

# Initialize and seed database if not exists
RUN python scripts/seed_db.py

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
