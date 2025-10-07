# --- Builder Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev libc-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# --- Runner Stage ---
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser
USER appuser

# Copy Python dependencies from builder
COPY --from=builder /app/wheels /app/wheels
RUN pip install --no-cache /app/wheels/*

# Copy application code
COPY . .

# Make entrypoint script executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose the port Gunicorn will run on
EXPOSE 8080

# Run Gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]
