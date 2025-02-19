FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/app/api

# Copy requirements first for better caching
COPY app/api/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

# Create log directory and set permissions
RUN mkdir -p /var/log/api && \
    chmod 777 /var/log/api

# Copy the application code
COPY app/api /app/app/api

# Copy alembic.ini and create migrations directory
COPY app/api/alembic.ini /app/alembic.ini
COPY app/api/migrations /app/migrations

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create a new entrypoint script
RUN echo '#!/bin/bash\n\
cd /app\n\
alembic upgrade head\n\
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Use the new entrypoint script
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"] 