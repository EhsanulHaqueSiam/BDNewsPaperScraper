# Project To-Do List

- [x] **Test Locally Testable Features**
  - [x] Test CLI commands (`bdnews list`, `bdnews scrape`) - ✅ Working
  - [x] Run pytest suite - ✅ 27 tests passing
  - [ ] Verify `app.py` (Streamlit GUI) - requires `uv sync --extra gui`
  - [ ] Check reports generation (analytics, dashboard)
  - [ ] Verify script execution in `scripts/` directory

- [ ] **Test & Fix Spiders**


### 🔍 Full Project Analysis & Potential Issues

#### 1. Critical Failure Points (High Priority)
- **Invalid URL Extraction:**
  - `ValidationPipeline` drops any item where URL does not start with `http://` or `https://`.
  - **Risk:** Spiders extracting `#`, `javascript:...`, or relative paths without `response.urljoin` will fail 100% of items.
  - **Affected:** Confirmed `dailysun`. Suspected `prothomalo` (if API returns paths) and HTML-based spiders.
- **Strict Content Validation:**
  - `ValidationPipeline` drops items with `article_body` < 50 chars.
  - **Risk:** Photo stories, video reports, or "stub" articles are silently discarded.
  - **Affected:** ALL spiders.

#### 2. API & Selector Fragility
- **Dynamic API Shifts:**
  - `dailysun` and `prothomalo` rely heavily on specific JSON structures (`items`, `cards`, `url` fields).
  - **Risk:** Any API schema change (e.g., renaming `url` to `link`) breaks the spider completely.
- **Date Parsing:**
  - `BaseNewsSpider` has a list of formats. If a site changes date format (e.g., "2 mins ago"), parsing returns `None`.
  - **Risk:** Articles might be skipped or dated incorrectly.

#### 3. Systemic Risks
- **Concurrency & Database:**
  - `SharedSQLitePipeline` uses WAL mode but high concurrency (64 requests) might still hit generic `database is locked` errors, causing item drops.
- **Anti-Bot Defenses:**
  - Cloudflare (mentioned in `dailysun` docstring) may be serving CAPTCHA pages which parse as empty content, triggering "Content too short" drops.

### 🛠️ Updated Action Plan
- [x] **Fix URL Logic:** Added `is_valid_article_url()` to `BaseNewsSpider` for all 79 spiders.
- [x] **Relax Validation:** Added `VALIDATION_STRICT_MODE` setting to log warnings instead of dropping items for short content.
- [x] **Spider-Specific Fixes:**
  - [x] `prothomalo`: ✅ **WORKING** - URL validation added, successfully scrapes articles.
  - [x] `dailysun`: ✅ Created `dailysun_playwright` spider to bypass Cloudflare (needs testing with Playwright installed)
- [ ] **Monitor Drops:** Enable `LOG_LEVEL=DEBUG` globally for a test run to catch `DropItem` exceptions.

### 🚨 Cloudflare-Protected Sites
- **dailysun** - ✅ Created `dailysun_playwright` spider
  - Run: `uv run playwright install chromium` (one-time setup)
  - Test: `uv run scrapy crawl dailysun_playwright -s CLOSESPIDER_ITEMCOUNT=5`

- [ ] **Test Playwright Scripts**
  - [ ] Verify `kalerkantho_playwright` works
  - [x] Created `dailysun_playwright` spider
  - [ ] Check `GenericPlaywrightSpider` functionality
  - [ ] Ensure browser installation is correct (`uv run playwright install`)


### 🚀 Roadmap: Universal Robustness (Scrape Any Site)

#### 1. Smart Fallback Architecture ✅ IMPLEMENTED
- **Status:** Complete - `extractors.py` created
- **Implementation:**
  1. **Primary:** JSON-LD / Microdata extraction
  2. **Secondary:** `trafilatura` ML-based extraction  
  3. **Tertiary:** Generic CSS heuristics (`<article>`, `h1`, p-dense div)
  4. **Pipeline:** `FallbackExtractionPipeline` auto-rescues short content

#### 2. Hybrid Request Engine ✅ IMPLEMENTED
- **Status:** Complete - `hybrid_request.py` created
- **Features:**
  - Auto-detects JS challenges/Cloudflare
  - Switches to Playwright on detection
  - Learns domains needing browser rendering

#### 3. AI-Powered Repair ✅ IMPLEMENTED
- **Status:** Complete - `ai_repair.py` created
- **Features:**
  - `AIRepairPipeline` for failed extractions
  - Ollama (local LLM) and OpenAI support

#### 4. Anti-Bot Evasion "Arms Race" ✅ FULLY IMPLEMENTED
- **Status:** Complete - `antibot.py` (350+ lines)
- **Features:**
  - Canvas fingerprint noise injection
  - WebGL vendor/renderer randomization
  - Audio context fingerprint protection
  - Screen/resolution randomization  
  - Timezone/language consistency (Asia/Dhaka)
  - Hardware concurrency randomization
  - Plugin/MIME type simulation
  - WebRTC leak prevention

#### 5. Dynamic Configuration ✅ IMPLEMENTED
- **Status:** Complete - `dynamic_config.py` created
- **Features:**
  - SelectorConfig stores working selectors per paper
  - Tracks success/failure rates
  - Auto-fallback to backup selectors

#### 6. "Time Travel" & External Archives ✅ IMPLEMENTED
- **Status:** Complete - `ArchiveFallbackMiddleware` in middlewares.py
- **Checks Wayback Machine API on 404/403/410**

#### 7. Geographic Mimicry ✅ FULLY IMPLEMENTED
- **Status:** Complete - `geo_mimicry.py` (350+ lines)
- **Features:**
  - Bangladesh proxy provider integration (BrightData, Oxylabs, SmartProxy)
  - BD-specific headers (Accept-Language, ISP headers)
  - Geo-block detection and retry
  - `BangladeshProxyMiddleware` for settings.py
  - 5 BD cities for geo context

#### 8. Synthetic Health Checks (Canary Scrapes) ✅ IMPLEMENTED
- **Status:** Complete - Pre-flight canary added to `daily-scrape.yml`
- **Script:** `scripts/canary_check.py --all`

#### 9. Cloudflare Countermeasures ✅ FULLY IMPLEMENTED
- **Status:** Complete - `cloudflare_bypass.py` (650+ lines)
- **Level 1:** Stealth headers → `stealth_headers.py`
- **Level 2:** Stealth Playwright (21 args, 3KB JS injection)
- **Level 3:** Cookie Management (cf_clearance caching)
- **Level 4:** Flaresolverr integration (Docker solver)
- **Level 5:** TLS Fingerprinting (curl_cffi Chrome mimicry)
- **Level 6:** Challenge Detection (10 patterns, auto-identify)
- **Level 7:** Progressive Escalation (retry with stronger methods)
- **Install:** `uv sync --extra cloudflare` for curl_cffi

#### 10. Distributed "Hydra" Infrastructure
- **Concept:** Cut off one head, two more appear.
- **Implementation:**
  - **Celery/Redis Queue:** Decouple scheduling from execution.
  - **Kubernetes Scaling:** Auto-scale spider pods based on CPU/Memory load.
  - **Ephemeral Workers:** Use AWS Lambda or Google Cloud Run for specific, hard-to-scrape pages (rotates IP/Infrastructure automatically).

#### 11. Defensive Scraping (Honeypot Detection) ✅ IMPLEMENTED
- **Status:** Complete - `honeypot.py` created
- **Features:**
  - `HoneypotDetectionMiddleware` for invisible link blocking
  - Suspicious URL pattern detection
  - Trap page detection (pages with >500 links)
  - `is_invisible_link()` helper function

#### 12. Observability & Monitoring (Ops Layer) ✅ IMPLEMENTED
- **Status:** Complete - `prometheus_metrics.py` created
- **Features:**
  - Prometheus metrics endpoint (items, requests, errors, response times)
  - Optional Pushgateway integration
  - Per-spider and per-domain metrics

#### 13. Adaptive Throttling (Compliance Engine) ✅ IMPLEMENTED
- **Status:** Complete - `AdaptiveThrottlingMiddleware` created
- **Implementation:**
  - **Dynamic Delay:** Tracks response times per domain, auto-adjusts on >500ms
  - **Circuit Breaking:** Existing `CircuitBreakerMiddleware` handles this
  - **Robots.txt Watchdog:** Future enhancement
