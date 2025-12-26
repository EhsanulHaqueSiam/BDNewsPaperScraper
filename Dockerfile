FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY pyproject.toml .
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir .

# Copy application code
COPY BDNewsPaper/ BDNewsPaper/
COPY scrapy.cfg .

# Create directories
RUN mkdir -p /app/data /app/logs /app/.checkpoints

# Environment variables
ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/news_articles.db
ENV LOG_LEVEL=INFO

# Expose API port
EXPOSE 8000

# Default command: run API server
CMD ["uvicorn", "BDNewsPaper.api:app", "--host", "0.0.0.0", "--port", "8000"]
