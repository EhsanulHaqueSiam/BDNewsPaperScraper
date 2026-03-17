# Codebase Concerns

**Analysis Date:** 2026-03-17

## Tech Debt

**High Concurrency vs. SQLite Lock Contention:**
- Issue: Settings define `CONCURRENT_REQUESTS = 64` and `CONCURRENT_REQUESTS_PER_DOMAIN = 16`, but SQLite is single-writer and under high concurrency can trigger "database is locked" errors
- Files: `BDNewsPaper/settings.py` (lines 68, 76, 245-246), `BDNewsPaper/spiders/base_spider.py` (lines 200-229)
- Impact: Items silently dropped during high-load scraping; duplicate detection fails; potential data loss
- Fix approach: Either reduce concurrency to match SQLite capabilities (4-8 concurrent requests max), or migrate to PostgreSQL (already partially implemented in `settings.py` lines 196-209). The `CONCURRENT_REQUESTS_PER_DOMAIN` should be <= 4 for safe SQLite operation.

**Bare Exception Handlers - Silent Failures:**
- Issue: 17 instances of bare `except:` blocks with no logging or recovery, masking real errors
- Files: `BDNewsPaper/cloudflare_bypass.py` (lines 364, 439), `BDNewsPaper/spiders/playwright_spider.py` (lines 267, 335, 527, 579, 698, 756, 826), `BDNewsPaper/extractors.py` (lines 259, 273, 287, 387), `BDNewsPaper/prometheus_metrics.py` (line 216), `BDNewsPaper/proxy.py` (lines 299, 422), `BDNewsPaper/ai_repair.py` (line 103)
- Impact: Silently failures in bypass mechanisms, extraction, and metrics collection; impossible to debug real issues vs. expected fallbacks
- Fix approach: Replace all `except:` with specific exception types (`except Exception as e:`) with `logger.warning()` or `logger.debug()` at minimum. At least log the exception type, message, and context before silencing.

**Untyped Spider Parse Methods (327+ instances):**
- Issue: Heavy use of `return None`, `return []`, `return {}` in spider parse chains without type hints or fallback documentation
- Files: Multiple spiders throughout `BDNewsPaper/spiders/`, base methods in `base_spider.py`
- Impact: Hard to debug empty results; impossible to know which extraction method failed; refactoring breaks silently
- Fix approach: Add return type hints (e.g., `-> Optional[Dict]`, `-> List[NewsArticleItem]`) to all parse/extraction methods. Add guard clauses that log when fallbacks are triggered (`logger.debug(f"Fallback extraction triggered for {response.url}")`).

**Large Monolithic Files - Maintenance Risk:**
- Issue: Several files exceed 700+ lines with multiple concerns mixed:
  - `base_spider.py`: 923 lines (base spider, extraction, fallbacks, database)
  - `cloudflare_bypass.py`: 878 lines (stealth headers, cookies, Flaresolverr, TLS, Scrapling)
  - `middlewares.py`: 899 lines (multiple middleware stacked)
  - `pipelines.py`: 726 lines (validation, fallback, cleaning, quality, language detection, database)
- Files: As listed above
- Impact: Risk of unintended side effects when modifying; cognitive overload; hard to test individual components
- Fix approach: Break into focused modules (e.g., `extraction_strategies.py`, `cf_levels.py`, `database_layer.py`). Use composition instead of inheritance.

**Missing Error Boundary in app.py (996 lines):**
- Issue: Streamlit app auto-installs dependencies on import failure (lines 20-26) with no safety checks
- Files: `app.py` (lines 20-26)
- Impact: Unsafe automatic package installation in production; could install malicious/wrong versions; breaks containerized deployments
- Fix approach: Fail fast with clear error message directing user to `uv sync --extra gui`. Never auto-install dependencies in production code.

## Known Bugs

**Playwright Spiders Return Zero Articles:**
- Symptoms: `kalerkantho_playwright`, `dailysun_playwright`, `generic_playwright` all report zero articles scraped despite sites being available
- Files: `BDNewsPaper/spiders/playwright_spider.py` (lines 95-280), referenced in `todo.md` (lines 15-20, 131-137)
- Trigger: Running `scrapy crawl kalerkantho_playwright` or similar
- Root cause: CSS selectors outdated (line 135 in `playwright_spider.py` and others); Cloudflare challenge timing may be insufficient (8 seconds hardcoded at line 58)
- Workaround: Fall back to API-based spiders; use `autonews` universal spider instead

**BDNewsPaper/distributed.py - Undefined Symbol Reference:**
- Symptoms: Code references features not implemented (Celery task definitions incomplete)
- Files: `BDNewsPaper/distributed.py` (509 lines)
- Impact: Distributed scraping feature is non-functional; users expecting parallel processing via Celery will fail
- Status: Marked as "ready" in `todo.md` but appears incomplete; tested only in todo planning phase

**ValidationPipeline Silently Drops Short Articles:**
- Symptoms: Articles under 50 characters dropped even if they're valid stub articles or photo stories
- Files: `BDNewsPaper/pipelines.py` (lines 74-80)
- Trigger: Spider extracts article with body length < 50 chars
- Root cause: Strict validation by default; `VALIDATION_STRICT_MODE = True` by default in settings
- Workaround: Set `-s VALIDATION_STRICT_MODE=false` or adjust `MIN_ARTICLE_LENGTH` in settings

**Date Parsing Fails Silently on Format Mismatch:**
- Symptoms: Articles are skipped or dated incorrectly when sites use non-standard date formats (e.g., "2 days ago", relative times)
- Files: `BDNewsPaper/spiders/base_spider.py` (lines 139-149)
- Impact: Many articles lose correct publish date; filtering by date range may skip valid articles
- Affected: Confirmed in `todo.md` (line 167); any spider using Bengali date format needs special handling via `bengalidate_to_englishdate.py`

## Security Considerations

**Secrets in Configuration Files:**
- Risk: Environment variables loaded but `.env` file in `config/` directory (see `docker-compose.yml` references)
- Files: Docker configuration references environment injection
- Current mitigation: `.gitignore` should exclude `.env*` files (verify in `.gitignore`)
- Recommendations: Audit `config/` directory for hardcoded credentials; use only env vars for Flaresolverr URL, proxy credentials, and Scrapling API keys. Never commit `config/cf_cookies.json` if it contains live Cloudflare clearance tokens (currently committed at `config/cf_cookies.json`).

**Scrapling API Integration Without Rate Limiting:**
- Risk: If Scrapling fetcher is enabled globally, unlimited API calls could exhaust quota or trigger abuse detection
- Files: `BDNewsPaper/cloudflare_bypass.py` (line 783+), `BDNewsPaper/scrapling_integration.py`
- Current mitigation: Lazy initialization; per-domain session pooling in `ScraplingSessionManager`
- Recommendations: Add per-domain request counter and throttle if API quota detected; implement fallback to Playwright if Scrapling exhausted.

**Proxy Credentials in Rotating Pool:**
- Risk: Proxy credentials could be logged in debug mode or exposed in error messages
- Files: `BDNewsPaper/proxy.py` (432 lines)
- Current mitigation: Credentials parsed from URL safely via urlparse
- Recommendations: Ensure proxy URLs are never logged; add `?` redaction in any debug output.

**Flaresolverr Endpoint Default to Localhost:**
- Risk: If accidentally pointed to external Flaresolverr endpoint, request body (including scraped URLs) is sent unencrypted to third-party server
- Files: `BDNewsPaper/cloudflare_bypass.py` (line 27), `BDNewsPaper/settings.py`
- Current mitigation: Default is `http://localhost:8191/v1` (local Docker)
- Recommendations: Warn if FLARESOLVERR_URL is not localhost in logs; consider HTTPS requirement.

## Performance Bottlenecks

**SQLite Serialization Under Load:**
- Problem: SQLite can only handle one write at a time; 64 concurrent requests cause queue buildup and timeouts
- Files: `BDNewsPaper/spiders/base_spider.py` (lines 207-229), `BDNewsPaper/pipelines.py` (SharedSQLitePipeline)
- Cause: No connection pooling for SQLite; each thread may open its own connection; high concurrency means lock contention
- Improvement path: Migrate to PostgreSQL for parallel writes. Alternatively, reduce `CONCURRENT_REQUESTS` to 4-8 max and use batch inserts in `SharedSQLitePipeline`.

**Missing Request Deduplication at Spider Level:**
- Problem: Duplicate link detection happens late in pipeline; generates unnecessary HTTP requests for known URLs
- Files: `BDNewsPaper/spiders/base_spider.py` (lines 207-229 has DB check but not always called before generating Request)
- Cause: No Dupefilter enabled by default; spiders should filter before yielding requests
- Improvement path: Use Scrapy's built-in DUPEFILTER_DEBUG and DUPEFILTER_CLASS. Pre-check URLs in `start_requests()` and `parse()` before `response.follow()`.

**Cloudflare Bypass Chain Progressive - No Caching:**
- Problem: Each 403/challenge triggers re-solving; no caching of cf_clearance cookies across runs
- Files: `BDNewsPaper/cloudflare_bypass.py` (lines 650+), `config/cf_cookies.json` referenced but cache management unclear
- Cause: Cookie cache file exists but unclear how/when it's loaded or validated
- Improvement path: Load cf_clearance from persistent cache on spider startup; validate age; auto-refresh if >1 hour old. Add cache hit/miss metrics.

**Playwright Page Creation Per Request:**
- Problem: If playwright enabled globally, creates new browser context per request (slow, resource-heavy)
- Files: `BDNewsPaper/settings.py` (lines 44-52 context config, but note line 55-56 warns against global enablement)
- Cause: No persistent page/context pool
- Improvement path: Use `PLAYWRIGHT_CONTEXTS` pooling; reuse contexts for same domain. Implement context lifecycle management.

## Fragile Areas

**CSS Selector-Based Extraction (79 Spiders):**
- Files: All spiders in `BDNewsPaper/spiders/` except `auto_spider.py` and API-based ones
- Why fragile: Sites update HTML structure every 3-6 months; selectors become stale and return zero results
- Safe modification: Always add fallback to `extract_from_jsonld()` or `FallbackExtractionPipeline`. Test selectors monthly. Use `link_discovery.py` pattern matching as final fallback.
- Test coverage: No unit tests for individual spider selectors; integration tests exist but are outdated (see `todo.md` lines 108-128)

**API Endpoints with Schema Assumptions:**
- Files: `BDNewsPaper/spiders/prothomalo.py`, `thedailystar.py`, `bdnews24.py`, `financialexpress.py`, etc.
- Why fragile: Assumes JSON response has specific keys (`items`, `cards`, `url`); API upgrades break silently
- Safe modification: Wrap JSON parsing in `try/except` with fallback to generic JSON-LD extraction. Log API response structure on first run.
- Test coverage: No schema validation tests; only happy-path integration tests

**Date Parsing with Timezone Assumptions:**
- Files: `BDNewsPaper/bengalidate_to_englishdate.py` (810 lines), `BDNewsPaper/spiders/base_spider.py` (lines 139-149)
- Why fragile: Hardcoded Dhaka timezone; assumes all spiders set publish_date in consistent format
- Safe modification: Add explicit timezone checks; log any timezone-unaware datetimes. Support both Bengali numerals and English.
- Test coverage: Basic tests exist but no Bengali date format matrix

**Hybrid Request Middleware (Auto HTTP/Playwright Switch):**
- Files: `BDNewsPaper/hybrid_request.py` (inferred from middlewares.py line 121)
- Why fragile: Automatic detection of JS-heavy sites may be incorrect; could trigger expensive Playwright rendering unnecessarily
- Safe modification: Add config flag to disable auto-switching; log decision rationale. Add metrics for false positives.
- Test coverage: No unit tests for detection logic

## Scaling Limits

**SQLite Single Database File:**
- Current capacity: ~1M articles before WAL mode breaks down (typical limit is 2-5GB file size)
- Limit: 1M+ articles, concurrent write pressure exceeds SQLite WAL capability
- Scaling path: Switch to PostgreSQL (`postgres_pipeline.py` partially implemented). OR use sharded SQLite (separate DB per day/source).

**Memory Usage with Large Scrapy Queues:**
- Current capacity: 64 concurrent requests * average response size (~200KB) = 12.8MB queue pressure
- Limit: Memory limit set in `settings.py` is 2048MB (reasonable for small deployments)
- Scaling path: Use distributed queue (Celery + Redis) already scaffolded in `distributed.py`. Enable `MEMUSAGE_LIMIT_MB` enforcement.

**Playwright Browser Pool:**
- Current capacity: Single Playwright context per spider; no connection pooling
- Limit: >10 concurrent Playwright spiders exhaust browser processes
- Scaling path: Implement browser context pooling; use BrowserPool library or custom context manager.

**Proxy Rotation with Fixed Provider:**
- Current capacity: Single proxy provider configured at a time
- Limit: Proxy provider bans domain; no fallback to next provider
- Scaling path: Implement provider failover; pre-test proxies on startup with canary requests.

## Dependencies at Risk

**Scrapling Integration (Partial, Optional):**
- Risk: Scrapling v0.4.1 is new (released 2025); may have breaking changes; Patchright (underlying browser) is alternative to Playwright with less community support
- Files: `BDNewsPaper/scrapling_integration.py`, `BDNewsPaper/cloudflare_bypass.py` (lines 783-800), pyproject.toml line 84
- Impact: If Scrapling breaks, CF Turnstile bypass fails; fallback to Playwright which is slower
- Migration plan: Keep Playwright as primary; Scrapling as optional acceleration. If Scrapling breaks, remove from settings and reduce CF_BYPASS_ENABLED levels.

**BrowserForge (V1.2.4):**
- Risk: Statistically coherent browser fingerprint generation; relies on Browserforge.com API or local generation
- Files: `pyproject.toml` line 85 (listed in `all` extras)
- Impact: If API changes, fingerprinting breaks; could trigger re-detection
- Migration plan: Fall back to hardcoded Chrome useragent if BrowserForge fails.

**curl_cffi (V0.14.0+):**
- Risk: Depends on specific OpenSSL version and system curl; JA4 fingerprinting may break with Chrome updates
- Files: `pyproject.toml` line 82, `BDNewsPaper/cloudflare_bypass.py` (TLS fingerprinting level 5)
- Impact: If system curl breaks, TLS impersonation fails; fallback to Playwright needed
- Migration plan: Test curl_cffi availability on startup; fall back to standard curl if unavailable.

**Twisted 25.5.0:**
- Risk: Major version (25.x); async reactor changes could break Playwright integration
- Files: pyproject.toml line 44
- Impact: `TWISTED_REACTOR` setting may become incompatible
- Migration plan: Pin to 24.x for stability; test major upgrades in isolated environment first.

## Missing Critical Features

**No Spider Health Monitoring:**
- Problem: No systematic check for spider failure; user only notices when articles stop appearing
- Blocks: Automated alerting, SLA monitoring, proactive spider repairs
- Implementation: Add `scripts/canary_check.py` as scheduled job (hourly recommended); log per-spider success rates; alert if any spider <50% success for 2+ runs.

**No Persistent Configuration for Working Selectors:**
- Problem: Selectors are hardcoded in spider; when they break, must manually edit spider code
- Blocks: Dynamic selector updates without code deployment; A/B testing selectors
- Implementation: Use `DynamicConfig` system (referenced in `todo.md` line 232 but not found in codebase). Store working selectors in JSON file; auto-fallback to backup selectors on validation failure.

**No Audit Trail for Item Drops:**
- Problem: Items are dropped by pipelines; user doesn't know why
- Blocks: Debugging pipeline failures; identifying patterns in drops
- Implementation: Add `DropAuditPipeline` that logs every dropped item with reason, context, and suggested fixes.

**No A/B Testing Framework for Selectors:**
- Problem: Can't compare selector performance without manual testing
- Blocks: Data-driven selector optimization
- Implementation: Add selector variant support in spiders; track success rates per variant.

## Test Coverage Gaps

**No Tests for Spider Selectors:**
- What's not tested: CSS selector extraction for all 79 HTML-based spiders
- Files: `BDNewsPaper/spiders/` (all except `auto_spider.py` and API-based)
- Risk: Selectors break silently; only discovered when users report empty scrapes
- Priority: High - add parameterized tests that fetch live articles and validate selector output

**No Tests for API Response Parsing:**
- What's not tested: JSON response parsing for API-based spiders (prothomalo, thedailystar, etc.)
- Files: Spiders in `BDNewsPaper/spiders/` with API parsing logic
- Risk: API schema changes break without warning
- Priority: High - mock API responses and validate JSON parsing

**No Tests for Cloudflare Bypass Levels:**
- What's not tested: Progression through CF bypass levels 1-7; which sites need which level
- Files: `BDNewsPaper/cloudflare_bypass.py` (implementation complete but no level tests)
- Risk: Bypass escalation may not work; sites get mixed up in levels
- Priority: Medium - add integration tests for each CF level with test sites

**No Tests for Encoding/Bengali Text Handling:**
- What's not tested: Bengali character extraction, cleaning, validation with real Bengali articles
- Files: `BDNewsPaper/bengalidate_to_englishdate.py`, `BDNewsPaper/pipelines.py` (language detection)
- Risk: Bengali articles corrupted or rejected silently
- Priority: Medium - add test cases with actual Bengali news text

**No Regression Tests for Pipeline Order:**
- What's not tested: Pipeline execution order; interdependencies between validation, fallback, cleaning, quality
- Files: `BDNewsPaper/pipelines.py` (multiple pipelines stacked)
- Risk: Pipeline ordering changes cause silent failures
- Priority: Low - document pipeline contract (input/output requirements per step)

---

*Concerns audit: 2026-03-17*
