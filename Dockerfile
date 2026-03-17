FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for building native Python packages and browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    curl \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml scrapy.cfg ./
COPY BDNewsPaper/ BDNewsPaper/
COPY scripts/ scripts/
COPY app.py quickstart.py run_spiders_optimized.py ./

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install core scrapy + dependencies (exclude playwright from initial install)
RUN pip install --no-cache-dir \
    "scrapy>=2.14.0" \
    "pytz>=2024.1" \
    "requests>=2.31.0" \
    "lxml>=5.0.0" \
    "itemadapter>=0.9.0" \
    "itemloaders>=1.3.0" \
    "w3lib>=2.2.0" \
    "trafilatura>=2.0.0" \
    "langdetect>=1.0.9"

# Install API dependencies
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.34.0" \
    "pydantic>=2.10.0"

# Install the project itself (deps already satisfied above)
RUN pip install --no-cache-dir --no-deps .

# Install anti-bot dependencies (optional — non-fatal if any fail)
RUN pip install --no-cache-dir scrapling curl_cffi browserforge patchright 2>/dev/null || \
    echo "Warning: Some anti-bot deps unavailable (scraping still works via Scrapy)"

# Install browser for stealth fetching (optional)
RUN (python -m patchright install chromium 2>/dev/null || \
     python -m playwright install chromium 2>/dev/null) || \
    echo "Warning: Browser not installed (API-only mode)"

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
