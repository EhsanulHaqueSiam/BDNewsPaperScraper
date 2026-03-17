# Architecture

**Analysis Date:** 2026-03-17

## Pattern Overview

**Overall:** Multi-layer Scrapy-based web scraping framework with pluggable middleware, pipeline processing, and dual retrieval strategies (API and HTML parsing).

**Key Characteristics:**
- Plugin-based middleware architecture for robustness and extensibility
- Dual extraction pathways: API-first with HTML/trafilatura fallback
- Configurable spider framework with centralized settings
- Layered request processing with circuit breakers, rate limiting, and anti-bot bypass
- Unified item model with automatic metadata generation

## Layers

**Request Preparation Layer (300-450):**
- Purpose: Prepare requests with anti-bot headers and capabilities
- Location: `BDNewsPaper/stealth_headers.py`, `BDNewsPaper/proxy.py`, `BDNewsPaper/cloudflare_bypass.py`, `BDNewsPaper/middlewares.py`
- Contains: Header rotation, proxy rotation, Cloudflare bypass (Scrapling + curl_cffi), user-agent middleware
- Depends on: Scrapy middleware hooks, external anti-bot libraries
- Used by: Downloader layer (processes all requests)

**Traffic Control Layer (450-550):**
- Purpose: Manage request throttling, rate limiting, and circuit breaking
- Location: `BDNewsPaper/middlewares.py` (CircuitBreakerMiddleware, StatisticsMiddleware, AdaptiveThrottlingMiddleware, RateLimitMiddleware)
- Contains: Dynamic throttling, request statistics, circuit breaker logic
- Depends on: Request metadata, spider state
- Used by: All spiders for graceful backoff

**Content Extraction Layer (550-650):**
- Purpose: Route requests to appropriate fetchers (Playwright, HTTP, Scrapling)
- Location: `BDNewsPaper/middlewares.py` (HybridRequestMiddleware), `BDNewsPaper/hybrid_request.py`, `BDNewsPaper/scrapling_integration.py`
- Contains: Playwright browser handling, multi-handler fallback, Scrapling integration
- Depends on: Request metadata (playwright=True flag), browser availability
- Used by: Spiders for JavaScript-heavy sites

**Spider Logic Layer:**
- Purpose: Extract article links and metadata from target websites
- Location: `BDNewsPaper/spiders/` directory (75+ newspaper spiders inheriting from BaseNewsSpider)
- Contains: Site-specific parsing logic, API endpoint definitions, category/date filters
- Depends on: Base spider class, configuration, extractors
- Used by: Scrapy framework for URL generation and response parsing

**Item Processing Pipeline:**
- Purpose: Validate, clean, and store items before persistence
- Location: `BDNewsPaper/pipelines.py`, `BDNewsPaper/postgres_pipeline.py`
- Contains: ValidationPipeline, FallbackExtractionPipeline, DuplicatePipeline, DeduplicationPipeline, SqLitePipeline
- Depends on: Item definition, extractors, database connections
- Used by: Scrapy for post-parse item handling

**Storage Layer:**
- Purpose: Persist scraped articles to SQLite/PostgreSQL
- Location: Database files (`news_articles.db`), `BDNewsPaper/pipelines.py` (SqLitePipeline)
- Contains: SQLite schema, insert/update logic
- Depends on: DatabaseConnection, item validation
- Used by: API and CLI tools for data retrieval

**API Layer:**
- Purpose: Expose articles via REST/GraphQL APIs
- Location: `BDNewsPaper/api.py`, `BDNewsPaper/graphql_api.py`
- Contains: FastAPI routes, Pydantic models, rate limiting, full-text search
- Depends on: SQLite FTS5, thread-safe database access
- Used by: External clients, web dashboards

**CLI Layer:**
- Purpose: Orchestrate scraper execution from command line
- Location: `BDNewsPaper/cli.py`
- Contains: Argument parsing, spider selection, output formatting
- Depends on: Scrapy CrawlerProcess, settings
- Used by: Users for batch scraping

**UI Layer:**
- Purpose: Web interface for monitoring and control
- Location: `app.py` (Streamlit dashboard)
- Contains: Real-time statistics, spider controls, article visualization
- Depends on: SQLite database, subprocess calls to scrapers
- Used by: Desktop/web monitoring

## Data Flow

**Standard Scraping Flow:**

1. User invokes CLI (`bdnews scrape`) or Streamlit app
2. CLI parses arguments and creates CrawlerProcess with spider names
3. Scrapy loads settings from `BDNewsPaper/settings.py`
4. Spider.start_requests() generates initial URLs (API or index pages)
5. Downloader middleware processes request:
   - StealthHeadersMiddleware: Adds anti-detection headers
   - UserAgentMiddleware: Rotates user-agent
   - ProxyMiddleware: Rotates proxy if needed
   - CloudflareBypassMiddleware: Handles CF challenges (Scrapling/curl_cffi)
   - HybridRequestMiddleware: Routes to Playwright/HTTP handler
6. Response returned to spider
7. Spider.parse() extracts article links → generates follow-up requests
8. Spider.parse_article() extracts fields → yields NewsArticleItem
9. Item pipeline processes:
   - ValidationPipeline: Checks required fields, URL format
   - FallbackExtractionPipeline: Recovers missing content via trafilatura
   - DuplicatePipeline: Checks SQLite for duplicates
   - SqLitePipeline: Inserts/updates database record
10. Database persists article
11. Statistics middleware tracks metrics
12. API queries database and returns articles to clients

**Fallback Extraction Flow (if initial parse fails):**

1. Spider extracts partial item with missing body
2. FallbackExtractionPipeline triggers (if body < MIN_LENGTH)
3. Attempts JSON-LD schema extraction
4. Falls back to trafilatura for DOM extraction
5. If successful, updates item and continues
6. If all fail, item dropped or logged depending on VALIDATION_STRICT_MODE

**State Management:**

- **Spider State:** Tracked in BaseNewsSpider instance (`processed_urls`, `should_stop`, statistics dict)
- **Request Metadata:** Stored in `request.meta` dict (playwright flag, retry count, extraction metadata)
- **Database State:** SQLite with unique constraint on `url` column for deduplication
- **Statistics:** Global stats via Scrapy's `crawler.stats` and spider middleware (counts, timings, errors)
- **Rate Limiting:** Per-IP tracking in RateLimiter.clients dict (time-window sliding window)

## Key Abstractions

**NewsArticleItem:**
- Purpose: Standardized data model for all newspaper articles
- Examples: `BDNewsPaper/items.py`
- Pattern: Scrapy Item with processors, auto-generated metadata, validation methods
- Fields: headline, article_body, url (required); author, publication_date, image_url, keywords (optional); scraped_at, content_hash, word_count (auto-generated)

**BaseNewsSpider:**
- Purpose: Template base class for all spiders
- Examples: `BDNewsPaper/spiders/base_spider.py`, `BDNewsPaper/spiders/prothomalo.py`, `BDNewsPaper/spiders/dailysun.py`
- Pattern: Abstract spider with lifecycle hooks for date parsing, category filtering, pagination, link discovery
- Responsibilities: Date range validation, duplicate checking via database, statistics tracking, pagination limits

**SpiderConfig:**
- Purpose: Declarative configuration for spider capabilities
- Examples: `BDNewsPaper/config.py` (SPIDER_CONFIGS dataclass)
- Pattern: Immutable dataclass defining API support, filters, categories, language
- Used by: CLI list command, spider selection logic, capability discovery

**Middleware Chain:**
- Purpose: Compose robustness features in priority order
- Examples: `BDNewsPaper/middlewares.py`, `BDNewsPaper/cloudflare_bypass.py`, `BDNewsPaper/stealth_headers.py`
- Pattern: Class-based Scrapy middleware with from_crawler() factory, process_request/response/exception hooks
- Ordering: 300-450 (request prep) → 450-550 (traffic control) → 550-650 (content retrieval)

**ItemPipeline Chain:**
- Purpose: Sequential validation, enrichment, deduplication, persistence
- Examples: `BDNewsPaper/pipelines.py` (ValidationPipeline, FallbackExtractionPipeline, SqLitePipeline)
- Pattern: Class-based Scrapy pipeline with from_crawler() factory, process_item() hook
- Ordering: Low priority (100-200) validation → medium (300-400) fallback/dedup → high (900) storage

**Extractor Framework:**
- Purpose: Multiple extraction strategies with automatic fallback
- Examples: `BDNewsPaper/extractors.py` (JSONLDExtractor, TrafilaturaExtractor, HeuristicExtractor)
- Pattern: Pluggable extractors with extraction() method returning dict or None
- Chain: JSON-LD → trafilatura → heuristics → None (dropped or logged)

## Entry Points

**CLI Entry Point:**
- Location: `BDNewsPaper/cli.py`, function `main()`
- Triggers: User runs `bdnews scrape [--arguments]`
- Responsibilities: Parse arguments, instantiate CrawlerProcess, add spiders, call process.start()

**Streamlit UI Entry Point:**
- Location: `app.py`
- Triggers: User runs `streamlit run app.py`
- Responsibilities: Display UI, read database, launch subprocess scrapers, show statistics

**Quickstart Script:**
- Location: `quickstart.py`
- Triggers: User runs `python quickstart.py`
- Responsibilities: Demo scraping with minimal setup, initialize database

**Scrapy Framework Entry Point:**
- Location: Implicit via Scrapy CrawlerProcess
- Triggers: CLI/UI launches CrawlerProcess
- Responsibilities: Load settings, instantiate spiders, run event loop, emit signals

## Error Handling

**Strategy:** Multi-level resilience with automatic fallback and graceful degradation.

**Patterns:**

**Request Failure → Circuit Breaker:**
- CircuitBreakerMiddleware tracks domain failures
- Opens circuit after N failures, prevents cascading requests
- Reopens after cooldown period

**Invalid Item → Validation Pipeline:**
- ValidationPipeline drops items with missing required fields
- VALIDATION_STRICT_MODE=False logs warnings instead of dropping
- FallbackExtractionPipeline attempts recovery before validation fails

**Missing Article Body → Fallback Extraction:**
- FallbackExtractionPipeline triggers if body < MIN_BODY_LENGTH
- Attempts JSON-LD, trafilatura, heuristics in sequence
- Logs extraction method used; item dropped if all fail

**Cloudflare Block → Middleware Chain:**
- CloudflareBypassMiddleware detects CF pages (503, JsChallenge detection)
- Routes to Scrapling fetcher (native anti-bot bypass)
- Fallback: Routes to Playwright for JavaScript rendering
- Final fallback: Logs error, marks request for retry

**Database Connection Error:**
- Thread-local database connections in SqLitePipeline
- Automatic reconnection with exponential backoff (max 3 retries)
- Item dropped if persistent connection failure

**Spider Crash:**
- BdnewspaperSpiderMiddleware catches process_spider_exception
- Logs exception with context (spider name, URL)
- Continues scraping other URLs

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module
- Approach: Per-spider loggers (`self.logger` in spiders), per-middleware loggers
- Levels: DEBUG (item extraction), INFO (spider lifecycle), WARNING (validation issues), ERROR (request failures)

**Validation:**
- Framework: ItemLoaders processors in `BDNewsPaper/items.py`
- Approach: Input processors clean/normalize; output processors extract single value
- Pipeline: ValidationPipeline enforces required fields and content length

**Authentication:**
- Not applicable (public news sites)
- Header-based anti-detection via StealthHeadersMiddleware instead

**Rate Limiting:**
- Per-domain: DOWNLOAD_DELAY, CONCURRENT_REQUESTS_PER_DOMAIN in settings
- Per-IP: RateLimiter in API layer (100 req/min)
- Adaptive: AdaptiveThrottlingMiddleware adjusts delays based on server response

**Deduplication:**
- Content-based: content_hash field in NewsArticleItem (MD5 of headline + body)
- URL-based: Unique constraint on `url` column in SQLite
- Pipeline: DuplicatePipeline checks both before insert

**Anti-bot:**
- Headers: StealthHeadersMiddleware adds Referer, Accept-Language, DNT, Accept-Encoding
- User-Agent: UserAgentMiddleware rotates from list of 7 modern browsers
- Proxy: ProxyMiddleware rotates if configured
- JavaScript: Playwright for sites requiring execution
- Cloudflare: CloudflareBypassMiddleware with Scrapling + curl_cffi

---

*Architecture analysis: 2026-03-17*
