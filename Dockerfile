# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# Set work directory
WORKDIR /app

# Install system dependencies including build tools for some Python packages
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements-minimal.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY src/ ./src/
COPY transqa.toml ./
COPY whitelist.txt ./
COPY examples/ ./examples/

# Create directories for models and cache
RUN mkdir -p /app/models /app/cache /app/reports

# Set default configuration
ENV TRANSQA_DATA_DIR=/app/data
ENV TRANSQA_MODELS_DIR=/app/models
ENV TRANSQA_CACHE_DIR=/app/cache

# Create a non-root user
RUN useradd --create-home --shell /bin/bash transqa && \
    chown -R transqa:transqa /app
USER transqa

# Set the default entry point
ENTRYPOINT ["python", "-m", "transqa.cli.main"]

# Default command (can be overridden)
CMD ["--help"]
