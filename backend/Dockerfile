# Use Python 3.9 slim image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Production command; docker-compose overrides it with --reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
