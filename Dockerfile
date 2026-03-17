FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files needed for install
COPY pyproject.toml scrapy.cfg ./
COPY BDNewsPaper/ BDNewsPaper/
COPY scripts/ scripts/
COPY app.py quickstart.py run_spiders_optimized.py ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[cloudflare,api]" && \
    pip install --no-cache-dir scrapling curl_cffi browserforge patchright

# Install browser for stealth fetching
RUN python -m patchright install chromium --with-deps 2>/dev/null || true

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
