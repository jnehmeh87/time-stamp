# --- Builder Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev libc-dev apt-transport-https ca-certificates gnupg curl
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get update && apt-get install -y google-cloud-sdk

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt && ls -l /app/wheels


# --- Runner Stage ---
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev apt-transport-https ca-certificates gnupg curl
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get update && apt-get install -y google-cloud-sdk

# Create a non-root user
RUN useradd --create-home appuser

# Copy Python dependencies from builder
COPY --from=builder /app/wheels /app/wheels
RUN ls -l /app/wheels && pip install --no-cache /app/wheels/*

# Copy application code
COPY . .

# Make entrypoint script executable and change ownership
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh && chown appuser:appuser /app -R

# Switch to the non-root user
USER appuser

# Expose the port Gunicorn will run on
EXPOSE 8080

# Run Gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]