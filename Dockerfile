FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml scrapy.cfg ./
COPY BDNewsPaper/ BDNewsPaper/
COPY scripts/ scripts/
COPY app.py quickstart.py run_spiders_optimized.py ./

# Install core dependencies first (most likely to succeed)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[api]"

# Install anti-bot dependencies (may fail on some platforms — non-fatal)
RUN pip install --no-cache-dir curl_cffi browserforge scrapling patchright || \
    echo "Warning: Some anti-bot deps failed to install (optional)"

# Install browser for stealth fetching (optional)
RUN python -m patchright install chromium --with-deps 2>/dev/null || \
    echo "Warning: Browser install skipped (optional for API-only mode)"

# Create directories
RUN mkdir -p /app/data /app/logs /app/.checkpoints /app/config

# Environment variables
ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/news_articles.db
ENV SCRAPLING_ENABLED=true
ENV LOG_LEVEL=INFO

# Expose API port
EXPOSE 8000

# Default command: run API server
CMD ["uvicorn", "BDNewsPaper.api:app", "--host", "0.0.0.0", "--port", "8000"]
