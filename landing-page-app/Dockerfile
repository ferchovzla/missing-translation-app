# Multi-stage build for TransQA Landing Page
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY landing-page-app/requirements-web.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-web.txt

# Copy TransQA source code from parent directory
COPY src ./src
COPY requirements.txt ./transqa-requirements.txt

# Install TransQA dependencies
RUN pip install --no-cache-dir -r transqa-requirements.txt

# Copy web application
COPY landing-page-app/api ./api
COPY landing-page-app/static ./static
COPY landing-page-app/templates ./templates

# Create necessary directories
RUN mkdir -p /app/models /app/cache /app/reports

# Create user for security
RUN useradd --create-home --shell /bin/bash transqa && \
    chown -R transqa:transqa /app

USER transqa

# Set Python path to include src directory
ENV PYTHONPATH=/app/src:/app

# Expose port
EXPOSE 8000

# Command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
