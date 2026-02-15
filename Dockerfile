# =============================================================================
# JobKit - Production Dockerfile
# =============================================================================
# Build:  docker build -t jobkit .
# Run:    docker run -p 8000:8000 --env-file .env jobkit
# =============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for PDF/DOCX parsing
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite (if used)
RUN mkdir -p data

EXPOSE 8000

# Run with Gunicorn + Uvicorn workers for production
# - Workers: 4 (adjust based on CPU cores: 2 * cores + 1)
# - Graceful timeout: 120s (matches AI call timeout)
# - Access log to stdout for container logging
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--graceful-timeout", "120", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
