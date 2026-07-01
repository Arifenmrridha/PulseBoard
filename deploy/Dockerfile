# Use official Python runtime as base image
FROM python:3.11-slim

# Prevent Python from writing pyc files to disk and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY agents/ ./agents/
COPY skills/ ./skills/
COPY tools/ ./tools/
COPY config/ ./config/
COPY mcp_config/ ./mcp_config/
COPY main.py .

# Expose port (if web interface is needed, otherwise pipeline is execution-only)
EXPOSE 8080

# Default entrypoint runs the pipeline orchestrator
ENTRYPOINT ["python", "main.py"]
CMD ["--recipient", "executive@company.com", "--role", "Executive"]
