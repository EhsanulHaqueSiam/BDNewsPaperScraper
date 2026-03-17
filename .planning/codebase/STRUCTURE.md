# Codebase Structure

**Analysis Date:** 2026-03-17

## Directory Layout

```
BDNewsPaperScraper/
├── BDNewsPaper/                    # Main package (Scrapy project)
│   ├── spiders/                    # 75+ newspaper spider implementations
│   ├── __init__.py
│   ├── items.py                    # Unified NewsArticleItem definition
│   ├── settings.py                 # Scrapy settings and middleware stack
│   ├── pipelines.py                # Item processing pipeline
│   ├── middlewares.py              # Downloader and spider middleware
│   ├── config.py                   # Centralized spider configuration
│   ├── cli.py                      # Command-line interface
│   ├── api.py                      # FastAPI REST API
│   ├── graphql_api.py              # GraphQL API
│   ├── extractors.py               # Content extraction strategies
│   ├── stealth_headers.py          # Anti-bot header middleware
│   ├── cloudflare_bypass.py        # CF challenge handling
│   ├── scrapling_integration.py    # Scrapling anti-bot integration
│   ├── proxy.py                    # Proxy rotation middleware
│   ├── antibot.py                  # Anti-bot detection utilities
│   ├── geo_mimicry.py              # Geographic spoofing
│   ├── link_discovery.py           # Article link finding utilities
│   ├── checkpoints.py              # Checkpoint/resume logic
│   ├── monitoring.py               # Statistics and monitoring
│   ├── dynamc_config.py            # Runtime configuration updates
│   ├── search.py                   # Full-text search utilities
│   ├── postgres_pipeline.py        # PostgreSQL storage pipeline
│   ├── hybrid_request.py           # Multi-handler request routing
│   └── distributed.py              # Celery task distribution
├── app.py                          # Streamlit web dashboard
├── quickstart.py                   # Quick start example script
├── pyproject.toml                  # Project metadata and dependencies
├── docker-compose.yml              # Docker services definition
├── Dockerfile                      # Container image
├── kubernetes.yml                  # Kubernetes deployment
├── init.sql                        # SQLite database schema
├── tests/                          # Test suite
├── scripts/                        # Utility scripts
├── data/                           # Data exports/reports
├── config/                         # Configuration files
├── docs/                           # Documentation
├── notebooks/                      # Jupyter notebooks
├── reports/                        # Generated reports
├── feeds/                          # RSS feed outputs
├── timeline/                       # Historical data archives
├── k8s/                            # Kubernetes manifests
├── maps/                           # Geographic mapping data
├── chrome_extension/               # Browser extension (if any)
├── .planning/codebase/             # GSD planning documents (this directory)
├── news_articles.db                # SQLite database
└── .pre-commit-config.yaml         # Pre-commit hooks
```

## Directory Purposes

**BDNewsPaper/:**
- Purpose: Main Python package containing all scraping logic
- Contains: Spiders, settings, middleware, pipelines, utilities
- Key files: `__init__.py` (empty), `settings.py` (Scrapy config)
- Entry: Imported by CLI, API, Streamlit app

**BDNewsPaper/spiders/:**
- Purpose: Individual newspaper spider implementations
- Contains: 75+ spider classes (one per newspaper)
- Key files: `base_spider.py` (abstract base), `auto_spider.py` (template), individual spiders (`prothomalo.py`, `thedailystar.py`, etc.)
- Naming: Lowercase spider name (e.g., `prothomalo.py` for ProthomaloSpider)
- Inheritance: All inherit from `BaseNewsSpider` in `base_spider.py`

**tests/:**
- Purpose: Test suite for core functionality
- Contains: Unit tests, integration tests, smoke tests
- Key files: `test_pipelines.py`, `test_middlewares.py`, `test_extractors.py`, `test_cloudflare_bypass.py`
- Config: `conftest.py` (pytest fixtures), `pytest.ini` in pyproject.toml
- Run: `pytest` or `pytest tests/test_*.py`

**scripts/:**
- Purpose: Utility scripts for maintenance and analysis
- Contains: Database cleanup, data export, monitoring scripts
- Run manually or via cron

**data/, reports/, feeds/, timeline/:**
- Purpose: Data storage and export locations
- Contains: JSON/CSV exports, generated reports, RSS feeds, historical archives
- Not committed: Usually in .gitignore

**config/:**
- Purpose: Configuration file storage (not environment variables)
- Contains: Default settings files, proxy lists, user-agent lists
- May include: yaml, json, or ini configuration files

**docs/, notebooks/:**
- Purpose: Documentation and exploratory analysis
- Contains: README, API docs, Jupyter notebooks for analysis
- Usage: Development reference, not production code

**k8s/, kubernetes.yml:**
- Purpose: Kubernetes deployment manifests
- Contains: Deployment specs, services, configmaps
- Usage: Production deployment to Kubernetes clusters

**chrome_extension/:**
- Purpose: Browser extension for supplementary functionality (if present)
- Contains: Manifest, popup HTML/JS
- Not core to scraper

## Key File Locations

**Entry Points:**
- `app.py`: Streamlit UI (run: `streamlit run app.py`)
- `quickstart.py`: Demo script (run: `python quickstart.py`)
- `BDNewsPaper/cli.py`: Command-line tool (run: `bdnews scrape [--args]`)
- `BDNewsPaper/api.py`: FastAPI REST server (run: `uvicorn BDNewsPaper.api:app`)

**Configuration:**
- `pyproject.toml`: Project metadata, dependencies, tool config (Black, isort, mypy, pytest)
- `BDNewsPaper/config.py`: Spider configurations, constants (SPIDER_CONFIGS, DEFAULT_START_DATE)
- `BDNewsPaper/settings.py`: Scrapy settings (middleware stack, pipelines, user-agent, timeouts)
- `.pre-commit-config.yaml`: Pre-commit hooks (black, isort, flake8, mypy)

**Core Logic:**
- `BDNewsPaper/items.py`: NewsArticleItem definition with processors
- `BDNewsPaper/spiders/base_spider.py`: Abstract spider base class (920 lines)
- `BDNewsPaper/spiders/prothomalo.py`: Example API-based spider (613 lines)
- `BDNewsPaper/spiders/playwright_spider.py`: JavaScript-rendering spider (837 lines)

**Middleware & Robustness:**
- `BDNewsPaper/middlewares.py`: Spider + downloader middleware (CircuitBreaker, RateLimit, Throttle)
- `BDNewsPaper/stealth_headers.py`: Anti-detection headers
- `BDNewsPaper/cloudflare_bypass.py`: Cloudflare challenge handling
- `BDNewsPaper/scrapling_integration.py`: Scrapling anti-bot fetcher integration
- `BDNewsPaper/proxy.py`: Proxy rotation middleware

**Pipelines & Storage:**
- `BDNewsPaper/pipelines.py`: Item validation, fallback extraction, deduplication, SQLite storage
- `BDNewsPaper/postgres_pipeline.py`: PostgreSQL storage alternative
- Database: `news_articles.db` (SQLite, created by init.sql)

**APIs & Interfaces:**
- `BDNewsPaper/api.py`: FastAPI REST endpoints (search, list, stats)
- `BDNewsPaper/graphql_api.py`: GraphQL API wrapper
- `BDNewsPaper/extractors.py`: Content extraction strategies (JSON-LD, trafilatura, heuristics)

**Database & Search:**
- `init.sql`: SQLite schema (articles table, FTS5 index)
- `BDNewsPaper/search.py`: Full-text search utilities

**Testing:**
- `tests/conftest.py`: Pytest fixtures
- `tests/test_pipelines.py`: Pipeline unit tests
- `tests/test_middlewares.py`: Middleware unit tests
- `tests/test_extractors.py`: Extractor unit tests
- `tests/test_smoke.py`: Full scrape integration tests

## Naming Conventions

**Files:**
- Spiders: Lowercase with underscores (e.g., `prothomalo.py`, `thedailystar.py`, `daily_sun.py`)
- Middleware: Descriptive lowercase (e.g., `stealth_headers.py`, `cloudflare_bypass.py`)
- Modules: Lowercase (e.g., `config.py`, `extractors.py`, `pipelines.py`)
- Main files: Lowercase (e.g., `app.py`, `quickstart.py`, `init.sql`)

**Directories:**
- Packages: Lowercase (e.g., `BDNewsPaper`, `spiders`, `tests`, `scripts`)
- Data directories: Plural or descriptive lowercase (e.g., `data`, `reports`, `feeds`)
- Config directories: Lowercase (e.g., `config`, `k8s`)

**Classes:**
- Spiders: PascalCase with "Spider" suffix (e.g., `ProthomaloSpider`, `TheDailyStarSpider`)
- Items: PascalCase (e.g., `NewsArticleItem`)
- Middleware: PascalCase with "Middleware" suffix (e.g., `StealthHeadersMiddleware`, `CircuitBreakerMiddleware`)
- Pipelines: PascalCase with "Pipeline" suffix (e.g., `ValidationPipeline`, `SqLitePipeline`)
- Config: PascalCase or CONSTANT (e.g., `SpiderConfig`, `SPIDER_CONFIGS`)

**Functions:**
- Utility functions: Lowercase with underscores (e.g., `clean_text()`, `validate_url()`, `normalize_date()`)
- Private functions: Single leading underscore (e.g., `_parse_date_args()`, `_generate_metadata()`)

## Where to Add New Code

**New Newspaper Spider:**
- Primary code: `BDNewsPaper/spiders/{newspaper_name}.py`
  - Inherit from `BaseNewsSpider`
  - Define `name`, `paper_name`, `allowed_domains`
  - Override `start_requests()`, `parse()`, `parse_article()` as needed
  - Copy pattern from similar spider (API-based → prothomalo.py, HTML-based → bdnews24.py)
- Configuration: Add entry to `SPIDER_CONFIGS` dict in `BDNewsPaper/config.py`
- Tests: Add test in `tests/test_smoke.py` for basic scraping validation
- Example: See `BDNewsPaper/spiders/prothomalo.py` (API-based) or `BDNewsPaper/spiders/bdnews24.py` (HTML-based)

**New Middleware Feature:**
- Implementation: `BDNewsPaper/middlewares.py` (downloader) or new file if significant
- Registration: Add to DOWNLOADER_MIDDLEWARES dict in `BDNewsPaper/settings.py` with priority (300-650 range)
- Pattern: Inherit from Scrapy middleware base, implement `from_crawler()`, `process_request()`
- Example: See `CircuitBreakerMiddleware` in `BDNewsPaper/middlewares.py` (lines 200-300)

**New Extraction Strategy:**
- Implementation: `BDNewsPaper/extractors.py`
- Registration: Add to extractor chain in `FallbackExtractionPipeline.process_item()`
- Pattern: Class with `extraction(html, url, spider)` method returning dict or None
- Example: See `TrafilaturaExtractor` in `BDNewsPaper/extractors.py`

**New API Endpoint:**
- Implementation: Add route in `BDNewsPaper/api.py` using @app.get() or @app.post()
- Response model: Define Pydantic BaseModel (e.g., ArticleResponse)
- Testing: Add test in `tests/test_integration.py`
- Example: See existing /articles endpoint in `BDNewsPaper/api.py`

**New Utility Module:**
- Location: `BDNewsPaper/{feature_name}.py`
- Imports: Import in relevant spiders/pipelines/middlewares
- Tests: Add test in `tests/test_{feature_name}.py`
- Example: `BDNewsPaper/search.py` (full-text search), `BDNewsPaper/honeypot.py` (anti-honeypot)

**CLI Command:**
- Implementation: Add subparser in `create_parser()` in `BDNewsPaper/cli.py`
- Logic: Implement handler function (e.g., `list_spiders()`, `run_scrapers()`)
- Example: See `scrape` command implementation (lines 56-103)

## Special Directories

**news_articles.db:**
- Purpose: SQLite database holding all scraped articles
- Generated: Yes, by init.sql on first run
- Committed: No (ignored by .gitignore)
- Schema: articles table with columns: url (PRIMARY KEY), headline, article_body, author, publication_date, image_url, category, paper_name, scraped_at, content_hash, etc.

**.planning/codebase/:**
- Purpose: GSD planning documents (Architecture, Structure, Conventions, Testing, Concerns, Stack, Integrations)
- Generated: Yes, by Claude agent for GSD orchestration
- Committed: Yes
- Usage: Read by /gsd:plan-phase and /gsd:execute-phase for context

**logs/ (if present):**
- Purpose: Scrapy run logs
- Generated: Yes, by Scrapy during execution
- Committed: No

**.venv/ or venv/ (if present):**
- Purpose: Python virtual environment
- Generated: Yes, by `python -m venv`
- Committed: No

**__pycache__/ (if present):**
- Purpose: Python bytecode cache
- Generated: Yes, automatically
- Committed: No

---

*Structure analysis: 2026-03-17*
