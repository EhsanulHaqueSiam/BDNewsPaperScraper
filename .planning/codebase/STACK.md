# Technology Stack

**Analysis Date:** 2026-03-17

## Languages

**Primary:**
- Python 3.9+ - Web scraping, API backends, CLI tools, data processing
- SQL - PostgreSQL and SQLite database schemas and queries

## Runtime

**Environment:**
- Python 3.11 (Docker default in `Dockerfile`)
- Supports Python 3.9, 3.10, 3.11, 3.12, 3.13 per `pyproject.toml`

**Package Manager:**
- pip (via setuptools via hatchling)
- Lockfile: Not detected (uses `pyproject.toml` with pinned versions)

## Frameworks

**Web Scraping:**
- Scrapy 2.14.0+ - Core web scraping framework (`BDNewsPaper/spiders/`)
- Scrapy-Playwright 0.0.46+ - JavaScript rendering and browser automation via Playwright
- Playwright 1.58.0+ - Headless browser automation for dynamic content
- Trafilatura 2.0.0+ - Article extraction fallback (`BDNewsPaper/items.py` pipeline)

**Web APIs:**
- FastAPI 0.135.0+ - REST API server (`BDNewsPaper/api.py`)
- Uvicorn 0.41.0+ - ASGI server for FastAPI and GraphQL
- Strawberry-GraphQL 0.308.0+ - GraphQL API interface (`BDNewsPaper/graphql_api.py`)
- Pydantic 2.12.0+ - Data validation for API request/response models

**Task Queue:**
- Celery 5.6.0+ - Distributed task queue for spider execution (`BDNewsPaper/distributed.py`)
- Redis 7.3.0+ - Message broker and result backend for Celery
- Flower 2.0.1+ - Web UI for Celery monitoring

**Monitoring & Observability:**
- Prometheus 0.24.0+ - Metrics export (`BDNewsPaper/prometheus_metrics.py`)
- Grafana (via docker-compose) - Metrics visualization dashboard
- psutil 7.2.0+ - System resource monitoring
- memory-profiler 0.61.0+ - Memory usage profiling
- py-spy 0.4.0+ - Statistical Python profiler

**Dashboards & UI:**
- Streamlit 1.55.0+ - Interactive dashboard (`app.py`, `dashboard_enhanced.py`)
- Pandas 3.0.0+ - Data manipulation and analysis
- Plotly 6.6.0+ - Interactive data visualization
- Matplotlib 3.10.0+ - Static plotting
- WordCloud 1.9.6+ - Word cloud generation
- OpenPyXL 3.1.5+ - Excel file export

**Testing:**
- pytest 9.0.0+ - Test runner
- pytest-cov 7.0.0+ - Code coverage reporting
- pytest-timeout 2.4.0+ - Test timeout enforcement

**Code Quality:**
- black 26.3.0+ - Code formatter
- isort 8.0.0+ - Import sorting
- flake8 7.3.0+ - Linting
- mypy 1.19.0+ - Static type checking
- pre-commit 4.5.0+ - Git hooks framework

## Key Dependencies

**Critical for Scraping:**
- requests 2.32.5+ - HTTP client
- curl_cffi 0.14.0+ - TLS/JA4/HTTP2 fingerprinting for Cloudflare bypass
- browserforge 1.2.4+ - Coherent browser fingerprint generation
- scrapling 0.4.1+ - Native Cloudflare Turnstile bypass via Patchright
- httpx 0.28.1+ - Modern async HTTP client

**Data Processing:**
- lxml 6.0.0+ - XML/HTML parsing
- parsel 1.11.0+ - CSS/XPath selectors
- w3lib 2.4.0+ - Web utilities (URL normalization, HTML utilities)
- cssselect 1.4.0+ - CSS selector parsing
- langdetect 1.0.9+ - Language detection
- textblob 0.19.0+ - Text analysis (optional, for analytics)

**Infrastructure:**
- cryptography 46.0.0+ - Encryption and TLS handling
- pyopenssl 25.3.0+ - OpenSSL wrapper
- brotli 1.2.0+ - Brotli compression support
- twisted 25.5.0+ - Async networking (Scrapy dependency)
- itemadapter 0.13.1+ - Unified dict/object interface for Scrapy items
- itemloaders 1.4.0+ - Scrapy item population utility
- queuelib 1.9.0+ - Queue implementations
- zope.interface 8.2+ - Interface definitions
- protego 0.6.0+ - robots.txt parser
- tldextract 5.3.0+ - TLD extraction
- service-identity 24.2.0+ - Service identity verification
- defusedxml 0.7.1+ - Safe XML parsing
- packaging 26.0+ - Package version parsing
- pytz 2026.1+ - Timezone support

**Database:**
- psycopg2-binary 2.9.11+ - PostgreSQL client/driver
- alembic 1.18.0+ - SQLAlchemy migration tool (optional)

**Performance:**
- uvloop 0.22.0+ - Faster event loop for asyncio (optional)
- cchardet 2.1.7+ - Faster character encoding detection (optional)

## Configuration

**Environment:**
- `.env` file support via `python-dotenv 1.2.0+`
- Key environment variables (from `docker-compose.yml`, `kubernetes.yml`):
  - `DATABASE_PATH` - SQLite database location (default: `news_articles.db`)
  - `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379/0`)
  - `RATE_LIMIT_REQUESTS` - API rate limit (default: 100 requests/minute)
  - `RATE_LIMIT_WINDOW` - Rate limit window in seconds (default: 60)
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - PostgreSQL credentials
  - `PLAYWRIGHT_BROWSERS_PATH` - Path to cached Playwright browsers
  - `LOG_LEVEL` - Logging level (default: INFO)
  - `CELERY_BROKER_URL` - Celery message broker URL
  - `CELERY_RESULT_BACKEND` - Celery result storage URL
  - `GRAFANA_PASSWORD` - Grafana admin password

**Build:**
- `pyproject.toml` - Package metadata, dependencies, tool configuration
  - Black: line-length 88, target Python 3.9+
  - isort: Black profile, multi-line mode 3
  - mypy: Python 3.9, type checking disabled for Scrapy-related modules
  - pytest: test discovery from `tests/`, verbose output, coverage reporting
- `Dockerfile` - Python 3.11-slim based container
- `.pre-commit-config.yaml` - Git hooks configuration

## Platform Requirements

**Development:**
- Python 3.9+
- pip/setuptools
- System libraries: gcc, libffi-dev (for cryptography)
- Playwright browsers (auto-installed first use)
- PostgreSQL 16 (optional, for production)
- Redis 7 (optional, for caching and Celery)

**Production:**
- Docker with Docker Compose or Kubernetes
- Kubernetes 1.20+ (for K8s deployment)
- Persistent volumes for SQLite/PostgreSQL data
- Redis service for caching and task queue
- Optional: Prometheus + Grafana for monitoring

---

*Stack analysis: 2026-03-17*
