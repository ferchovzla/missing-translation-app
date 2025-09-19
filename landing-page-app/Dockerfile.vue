# Multi-stage build for TransQA Vue.js Landing Page
FROM node:18-alpine as vue-builder

WORKDIR /app

# Copy Vue.js frontend
COPY vue-frontend/package*.json ./
RUN npm ci --only=production

COPY vue-frontend/ ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim as backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements-web.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-web.txt

# Copy TransQA source code from parent directory  
COPY ../src ./src
COPY ../requirements.txt ./transqa-requirements.txt

# Install TransQA dependencies
RUN pip install --no-cache-dir -r transqa-requirements.txt

# Copy API backend
COPY api ./api

# Copy built Vue.js frontend from builder stage
COPY --from=vue-builder /app/dist ./static

# Copy configuration files
COPY ../transqa.toml ./transqa.toml
COPY ../whitelist.txt ./whitelist.txt

# Create necessary directories
RUN mkdir -p /app/models /app/cache /app/reports /app/logs

# Create user for security
RUN useradd --create-home --shell /bin/bash transqa && \
    chown -R transqa:transqa /app

USER transqa

# Set Python path to include src directory
ENV PYTHONPATH=/app/src:/app
ENV STATIC_FILES_DIR=/app/static

# Expose port
EXPOSE 8000

# Command with Vue.js static file serving
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

