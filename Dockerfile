FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies if needed (e.g., for building extensions)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd -m botuser && chown -R botuser /app
USER botuser

# Copy application source code
COPY . .

# Expose ports for webhooks, health checks, and metrics
EXPOSE 8000 8080 9090

# Healthcheck targeting the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Default command to run the main bot
CMD ["python", "main.py"]
