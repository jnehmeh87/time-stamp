# --- Builder Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev

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

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "time_stamp.wsgi:application"]
