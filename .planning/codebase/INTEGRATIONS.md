# External Integrations

**Analysis Date:** 2026-03-17

## APIs & External Services

**Bangladeshi Newspaper Content APIs:**
- ProthomAlo - Advanced search API with date and category filtering
  - Client: Requests/Scrapy (`BDNewsPaper/spiders/prothomalo.py`)
  - Uses: API-based scraping with category support

- The Daily Star - Archive and search API via Google Custom Search Engine (CSE)
  - Client: Requests/Scrapy (`BDNewsPaper/spiders/thedailystar.py`)
  - Uses: API-based article discovery

- Daily Sun - REST API with date/category filtering
  - Client: Requests/Scrapy (`BDNewsPaper/spiders/dailysun.py`)
  - Uses: JSON API with structured response parsing

- Other Newspapers (75+ total) - HTML scraping
  - Client: Scrapy with Playwright for JS-heavy sites
  - Examples: `BDNewsPaper/spiders/bdpratidin.py`, `BDNewsPaper/spiders/bbcbangla.py`

**Anti-Bot & Cloudflare:**
- Scrapling (StealthyFetcher) - Native Cloudflare Turnstile bypass
  - SDK: scrapling 0.4.1+
  - Auth: N/A (no credentials required)
  - Files: `BDNewsPaper/scrapling_integration.py`, `BDNewsPaper/cloudflare_bypass.py`
  - Purpose: Bypass Cloudflare challenges with native browser automation via Patchright

- curl_cffi - TLS fingerprinting for Chrome impersonation
  - SDK: curl_cffi 0.14.0+
  - Auth: N/A
  - Files: `BDNewsPaper/cloudflare_bypass.py`
  - Purpose: HTTP requests with Chrome-like TLS profiles

- browserforge - Browser fingerprint generation
  - SDK: browserforge 1.2.4+
  - Auth: N/A
  - Files: `BDNewsPaper/cloudflare_bypass.py`
  - Purpose: Generate statistically coherent browser fingerprints

- FlareSolverr / Byparr - Challenge solving service (optional escalation)
  - URL: `FLARESOLVERR_URL` (default: `http://localhost:8191/v1`)
  - Auth: N/A
  - Files: `BDNewsPaper/cloudflare_bypass.py`
  - Purpose: Last-resort Cloudflare solving via Docker service

## Data Storage

**Databases:**

**SQLite (Default):**
- Provider: Embedded SQLite
- Connection: `DATABASE_PATH` environment variable (default: `news_articles.db`)
- Client: sqlite3 (Python stdlib)
- Schema: `init.sql` defines articles table, bookmarks, scrape_logs, api_cache, materialized views
- Location: `news_articles.db` (repo root)
- Used for: Development, single-instance deployments

**PostgreSQL (Optional/Production):**
- Provider: PostgreSQL 16 (Docker image: postgres:16-alpine)
- Connection: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (docker-compose.yml sets defaults)
- Port: 5432 (docker-compose only)
- Client: psycopg2-binary 2.9.11+
- Pipeline: `BDNewsPaper/postgres_pipeline.py`
- Schema: Same as SQLite, with additional full-text search indices
- Migrations: alembic 1.18.0+ available but not yet implemented
- Used for: Production deployments, distributed architectures

**File Storage:**
- Local filesystem only (no cloud storage integration)
- Data directory: `./data/` (mounted in docker-compose)
- Playwright browsers cache: `$PLAYWRIGHT_BROWSERS_PATH` or `~/.cache/ms-playwright/`

**Caching:**
- Redis 7-alpine (optional)
- Connection: `REDIS_URL` environment variable (default: `redis://localhost:6379/0`)
- Port: 6379
- Purpose:
  - Celery message broker (database 0)
  - Celery result backend (database 1)
  - API response caching (via API cache pipeline)
- Docker container: bdnews-redis (docker-compose.yml line 67-77)

## Authentication & Identity

**Auth Provider:**
- None - All newspaper APIs accessed without authentication
- No user authentication layer in REST API (open access)
- Rate limiting by IP address (in-memory or Redis-based)

**No External Identity Services:**
- No OAuth/OIDC integration
- No API key management system
- No user login mechanism

## Monitoring & Observability

**Error Tracking:**
- None detected - No Sentry, error reporting service, or centralized error tracking

**Logs:**
- File-based: Rotating log files in `logs/` directory
- Console: stdout/stderr in Docker containers
- Scrapy built-in logging to `bdpratidin_log.txt`
- No centralized log aggregation (ELK stack, CloudWatch, etc.)

**Metrics:**
- Prometheus 0.24.0+
  - Metrics endpoint: Port 9100 (via `PrometheusMetricsExtension`)
  - Optional Pushgateway: `PROMETHEUS_PUSHGATEWAY` env var
  - Files: `BDNewsPaper/prometheus_metrics.py`
  - Exports: Items scraped, requests/responses per domain, error counts, response time histograms

**Visualization:**
- Grafana (optional, docker-compose profile: monitoring)
  - Port: 3000
  - Data source: Prometheus
  - Admin password: `GRAFANA_PASSWORD` env var

## CI/CD & Deployment

**Hosting:**
- Docker with Docker Compose (development/staging)
- Kubernetes 1.20+ (production-ready manifest)
- Local development (Python env)

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, or similar
- Pre-commit hooks configured (`.pre-commit-config.yaml`)
- Manual testing via pytest

**Deployment Targets:**
- Docker Compose (3.8+):
  - Services: api, dashboard, scraper, redis, postgres, prometheus, grafana
  - Profiles: scrape, production, monitoring
  - Volumes: redis-data, postgres-data, prometheus-data, grafana-data

- Kubernetes (v1.19+):
  - Namespace: bdnews
  - Deployments: redis, postgres, scraper, api
  - Services: expose ports for Redis (6379), PostgreSQL (5432), API (8000)
  - ConfigMaps: environment variables
  - PersistentVolumes: 10Gi for data storage

## Environment Configuration

**Required env vars (for production):**
- `DATABASE_PATH` - Path to SQLite DB or PostgreSQL connection string
- `REDIS_URL` - Redis connection URL
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - PostgreSQL credentials
- `RATE_LIMIT_REQUESTS` - API rate limit per minute (default: 100)

**Optional env vars:**
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `PLAYWRIGHT_BROWSERS_PATH` - Playwright browser cache location
- `CELERY_BROKER_URL` - Celery broker URL (default: redis://localhost:6379/0)
- `CELERY_RESULT_BACKEND` - Celery result backend (default: redis://localhost:6379/1)
- `FLARESOLVERR_URL` - Challenge solving service URL
- `GRAFANA_PASSWORD` - Grafana admin password
- `CF_BYPASS_ENABLED` - Enable Cloudflare bypass (default: true)
- `CF_SCRAPLING_ENABLED` - Use Scrapling for CF bypass (default: true)

**Secrets location:**
- Environment variables only (no .env files committed)
- Docker: via docker-compose environment section and .env file (not committed)
- Kubernetes: via Secrets (not yet implemented, currently uses ConfigMap)
- Development: Python-dotenv loads from .env (local only)

## Webhooks & Callbacks

**Incoming:**
- None - No webhook ingestion endpoints

**Outgoing:**
- None - No external webhook callbacks

## HTTP Client Configuration

**Default User-Agent:**
- `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36`
- Overridable per spider via custom_settings

**Playwright Context (JavaScript rendering):**
- Viewport: 1920x1080
- Locale: en-US
- Timezone: Asia/Dhaka
- Ignore HTTPS errors: true (for self-signed certs)
- Headless mode: true

**Request Settings (Scrapy):**
- DOWNLOAD_DELAY: 0.5s (randomized)
- CONCURRENT_REQUESTS: 64 (global)
- CONCURRENT_REQUESTS_PER_DOMAIN: 16
- DOWNLOAD_TIMEOUT: 180s (3 minutes, for slow Bangladesh news sites)
- ROBOTSTXT_OBEY: false

---

*Integration audit: 2026-03-17*
