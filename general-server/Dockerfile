# Use Python 3.11 slim image as base
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser

# Final stage
FROM python:3.11-slim

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /etc/passwd /etc/passwd

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Use non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8004

# Command to run the application
CMD ["uvicorn", "pr-listener:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "4"]