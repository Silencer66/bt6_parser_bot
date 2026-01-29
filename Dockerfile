FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    pstgresql-clienot \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./src .

# Create necessary directories
RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV APP_API_PORT=${PORT:-8000}

# Use Python script as entrypoint
CMD ["python3", "main.py"]
