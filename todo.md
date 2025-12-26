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

#### 1. Smart Fallback Architecture
- **Concept:** Never fail completely; degrade gracefully.
- **Implementation:**
  1. **Primary:** Specific Selectors (Fastest, High Precision).
  2. **Secondary:** JSON-LD / Microdata (Standardized schemas).
  3. **Tertiary:** Generic Heuristics (e.g., `<article>`, `h1` near top, p-dense div).
  4. **Final Fallback:** Library-based extraction (`trafilatura` or `newspaper3k`).

#### 2. Hybrid Request Engine
- **Concept:** Balance speed (Requests) vs. Access (Browser).
- **Implementation:**
  - Start with `httpx/requests` (Speed).
  - If 403/429/JS-Challenge detected -> **Auto-switch** to `Playwright` (Stealth).
  - Use `scrapy-playwright` only for difficult sites/pages.

#### 3. AI-Powered Repair
- **Concept:** Use LLMs for "Last Mile" fixing.
- **Implementation:**
  - If ValidationPipeline drops an item due to "Bad Content", send HTML snippet to a local LLM (small model).
  - Prompt: "Extract headline and body from this messy HTML."

#### 4. Anti-Bot Evasion "Arms Race"
- **Implementation:**
  - **TLS Fingerprinting:** Use `curl_cffi` or `tls-client` to mimic real Chrome TLS handshakes (defeats Cloudflare).
  - **Residential Proxies:** Rotate IPs per request for strict sites.
  - **Browser Fingerprints:** Randomize Canvas/WebGL fingerprints in Playwright.

#### 5. Dynamic Configuration
- **Concept:** Spiders that heal themselves.
- **Implementation:**
  - Database stores "Working Selectors".
  - If failure rate > 10%, a "Doctor" script runs to find new selectors and updates the DB.

#### 6. "Time Travel" & External Archives
- **Concept:** If direct access fails, check the archives.
- **Implementation:**
  - If a specific article URL returns 404/403:
  - Check **Internet Archive (Wayback Machine)** API.
  - Check **Google Cache** version.
  - Check **Bing Cache**.

#### 7. Geographic Mimicry
- **Concept:** Be where the user is.
- **Implementation:**
  - Many Bangladeshi news sites block foreign IPs or serve limited "International Editions".
  - **Strategy:** Use dedicated **Bangladesh Proxy/VPN nodes** for local-only content.

#### 8. Synthetic Health Checks (Canary Scrapes)
- **Concept:** Know it's broken before the main job.
- **Implementation:**
  - Run a lightweight "Canary" spider every hour on just the Homepage.
  - If Canary fails (0 items or Layout shift detected) -> **Alert Admin** & **Pause Main Job**.

#### 9. Cloudflare Countermeasures (The "Red Button")
- **Level 1 (TLS Mimicry):**
  - Replace `requests` with `curl_cffi` or `tls_client`.
  - **Why:** Cloudflare blocks Python's default SSL handshake. These libraries copy Chrome's handshake exactly.
- **Level 2 (The "Stealth" Browser):**
  - Use `scrapy-playwright` with `args=["--disable-blink-features=AutomationControlled"]`.
  - Inject `stealth.min.js` to hide webdriver properties.
- **Level 3 (Cookie Hijacking):**
  - Run a local browser, login/solve Captcha manually.
  - Export `cf_clearance` cookie and User-Agent.
  - Inject these into Scrapy middleware (`CookieMiddleware`).
- **Level 4 (Solver Services):**
  - Integrate **Flaresolverr** (Docker container) that solves JS challenges and returns cookies.
  - Use commercial API solvers (2Captcha, CapMonster) for "Turnstile".
- **Level 5 (Network Layer Mastery):**
  - **JA3/JA4 Randomization:** Randomize TLS Client Hello packets to prevent fingerprinting.
  - **HTTP/2 & HTTP/3 (QUIC):** Force newer protocols which are harder for WAFs to filter without false positives.
  - **Header Order Hacking:** Mimic Chrome's exact header order (e.g., `Host` before `User-Agent`) using custom middleware.

#### 10. Distributed "Hydra" Infrastructure
- **Concept:** Cut off one head, two more appear.
- **Implementation:**
  - **Celery/Redis Queue:** Decouple scheduling from execution.
  - **Kubernetes Scaling:** Auto-scale spider pods based on CPU/Memory load.
  - **Ephemeral Workers:** Use AWS Lambda or Google Cloud Run for specific, hard-to-scrape pages (rotates IP/Infrastructure automatically).

#### 11. Defensive Scraping (Honeypot Detection)
- **Concept:** Don't get trapped by anti-bot fake links.
- **Implementation:**
  - Detect "invisible" links (CSS `display: none`, `visibility: hidden`) and avoid them.
  - Analyze link distribution: If a page has 10,000 links, it's a trap.
  - Track "Trap URLs" in a shared Redis blocklist.

#### 12. Observability & Monitoring (Ops Layer)
- **Concept:** Visual proof of health.
- **Implementation:**
  - **Prometheus Exporter:** Spider pushes metrics (items/min, errors/min) to Pushgateway.
  - **Grafana Dashboard:** real-time view of all 79 spiders.
  - **Dead Man's Switch:** If no successful scrape for 24h -> Critical Alert to Discord/Slack.

#### 13. Adaptive Throttling (Compliance Engine)
- **Concept:** Be a polite guest, never crash the host.
- **Implementation:**
  - **Dynamic Delay:** If server response time > 500ms, automatically double `DOWNLOAD_DELAY`.
  - **Circuit Breaking:** If 500/503 errors > 5%, pause spider for 10 minutes.
  - **Robots.txt Watchdog:** Re-check `robots.txt` every 24h for rule changes.
