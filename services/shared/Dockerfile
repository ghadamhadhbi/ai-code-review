
# =====================================================
# SHARED LIBRARY DOCKERFILE (Optional)
# services/shared/Dockerfile
# =====================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY . .

# This is a utility container, no CMD needed
# Other services mount this as a volume