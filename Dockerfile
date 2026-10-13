# Multi-stage lightweight Python container
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5001 \
    FLASK_ENV=production \
    FLASK_DEBUG=0 \
    MPLCONFIGDIR=/tmp/matplotlib_aref

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Run benchmark once at build time if results are missing
RUN python benchmark.py

# Expose port
EXPOSE 5001

# Run with production Gunicorn server
CMD ["gunicorn", "app:app", "--workers", "4", "--bind", "0.0.0.0:5001", "--timeout", "120"]
