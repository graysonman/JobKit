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

# Copy startup script and make executable
COPY start.sh .
RUN chmod +x start.sh

# Run migrations then start Gunicorn with Uvicorn workers
CMD ["./start.sh"]
