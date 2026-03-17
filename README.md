# 📰 BD Newspaper Scraper

> The most comprehensive Bangladeshi newspaper scraping framework. Collect articles from **95+ sources** with state-of-the-art anti-bot bypass, full-text search, and REST/GraphQL APIs.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Scrapy 2.14+](https://img.shields.io/badge/Scrapy-2.14+-60A839?logo=scrapy&logoColor=white)](https://scrapy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Spiders](https://img.shields.io/badge/Spiders-95+-blue)](#available-spiders)
[![Tests](https://img.shields.io/badge/Tests-239_passing-brightgreen)](#development)

---

## Features

### 📡 Data Collection — 95+ Newspaper Spiders

- 📰 **95+ Newspaper Spiders:** English, Bangla, and international sources covering all major Bangladeshi newspapers, TV channels, wire services, and regional papers.
- 🔄 **Multiple Discovery Methods:** RSS feeds, Google News sitemaps, JSON/AJAX APIs, WordPress REST API, and intelligent HTML scraping — each spider uses the most reliable method for its source.
- 📅 **Smart Date Filtering:** Scrape articles within any date range with `start_date` and `end_date` arguments. Full Bengali-to-English date conversion (জুলাই ১০, ২০২৪ → July 10, 2024).
- 📂 **Category Filtering:** Target specific news categories (politics, sports, business, etc.) per spider.
- 🧠 **4-Layer Fallback Extraction:** JSON-LD → Trafilatura (ML-based) → Heuristic CSS → Regex. If one method fails, the next takes over automatically.
- 🔗 **Intelligent Link Discovery:** URL scoring algorithm to identify article links vs navigation/tag pages.

### 🛡️ Anti-Bot Bypass — State of the Art (2026)

- 🔒 **9-Level Cloudflare Bypass:** Progressive escalation from stealth headers → TLS fingerprinting → FlareSolverr → Scrapling → Camoufox → Playwright. Each level tried automatically on failure.
- 🕷️ **Scrapling Integration (Default):** TLS fingerprint impersonation via curl_cffi. Impersonates Chrome 128-133, Safari 18, Firefox 133 with matching JA3/JA4/HTTP2 fingerprints. Enabled by default for all spiders.
- 🦊 **Camoufox:** Firefox-based stealth browser — harder to detect than Chromium since bot detectors primarily target Chrome automation patterns.
- 🤖 **CAPTCHA Solving:** reCAPTCHA v2 (checkbox + invisible), reCAPTCHA v3 (score-based), hCaptcha, and Cloudflare Turnstile. 4 provider backends: 2Captcha, CapSolver, AntiCaptcha, CapMonster. Auto-retry with exponential backoff.
- 🛡️ **Akamai Bot Manager Bypass:** Detects `_abck`/`bm_sz` cookies and generates valid sensor data via browser automation.
- 🔐 **DataDome / PerimeterX / Incapsula Bypass:** Automatic detection and cookie extraction via headless browsers with behavioral simulation (mouse movement, scrolling).
- 🎭 **BrowserForge Fingerprints:** Statistically coherent browser fingerprints — GPU, screen, UA, platform, client hints all consistent. No random noise that detectors can spot.
- 📡 **TLS Profile Rotation:** Rotates between Chrome/Safari/Firefox JA3 fingerprints matching the User-Agent header sent with each request.
- 🆓 **Free by Default:** All browser-based bypasses (Akamai, DataDome, PerimeterX, Incapsula) are enabled out of the box — no API keys needed. Only CAPTCHA solving requires a paid provider key.

### 💾 Storage & Search

- 🗄️ **SQLite (Default):** Zero-config, WAL mode for concurrent writes, thread-safe connections. Just scrape and it works.
- 🐘 **PostgreSQL:** Production-grade with connection pooling, full-text search via `tsvector`, and automatic search vector triggers.
- 🔍 **Full-Text Search:** FTS5 with BM25 relevance ranking, phrase search with `"quoted terms"`, and highlighted results with `<mark>` tags.
- 🔒 **Content Deduplication:** SHA-256 content hash + URL uniqueness. No duplicate articles in your database.

### 🌐 REST & GraphQL APIs

- ⚡ **REST API (FastAPI):** Rate-limited (100 req/min per IP), paginated, filterable by paper/category/date/author. OpenAPI/Swagger docs at `/docs`.
- 🔮 **GraphQL API (Strawberry):** Query articles, papers, categories, and stats with flexible GraphQL queries.
- 🔎 **Search Endpoint:** Full-text search with relevance ranking, highlighting, and paper/category filters.
- 🔑 **Admin Auth:** Protected admin endpoints (index rebuild) require API key via `X-API-Key` header.

### 📊 Monitoring & Operations

- 📈 **Streamlit Dashboard:** Real-time scraping control with article browsing, search, and export. Premium dark UI.
- 📉 **Prometheus Metrics:** Scrape rates, error counts, response times, database size — all exportable to Grafana.
- 🏥 **Health Checks:** Automated database connectivity, article yield, and error rate monitoring with Slack alerting.
- 💾 **Checkpoint/Resume:** Crash recovery with periodic checkpoints. Restart a failed scrape from where it left off.
- 🐳 **Docker Ready:** Full Docker Compose setup with API, dashboard, Redis, PostgreSQL, Prometheus, and Grafana.

### 🏗️ Robust Architecture

- 🔄 **Circuit Breaker:** Per-domain circuit breaker with CLOSED → OPEN → HALF_OPEN state machine. Stops hammering failing sites.
- ⏱️ **Adaptive Throttling:** Dynamic delay adjustment based on server response times. Respects slow sites automatically.
- 🔁 **Smart Retry:** Exponential backoff with jitter for 500/502/503/504/429 errors. Configurable max retries.
- 📡 **Hybrid Request Engine:** Automatically switches from HTTP to Playwright when JavaScript challenges are detected.
- 🏛️ **Archive Fallback:** Queries Wayback Machine for 404/403 pages to recover deleted articles.
- 🐝 **Honeypot Detection:** Identifies and avoids anti-bot trap links on listing pages.

---

## Quick Start

### Installation

```bash
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper

# Install with uv (recommended)
uv pip install -e ".[cloudflare]"

# Or with pip
pip install -e ".[cloudflare]"

# Install browser for stealth fetching
python -m patchright install chromium
```

### Basic Usage

```bash
# Scrape Prothom Alo (latest articles)
scrapy crawl prothomalo

# Scrape with date range
scrapy crawl jugantor -a start_date=2026-03-01 -a end_date=2026-03-17

# Scrape specific categories
scrapy crawl thedailystar -a categories=sports,business

# Limit article count
scrapy crawl samakal -s CLOSESPIDER_ITEMCOUNT=50

# Run all spiders (optimized parallel execution)
python run_spiders_optimized.py
```

### Search & API

```bash
# REST API
uvicorn BDNewsPaper.api:app --reload

# GraphQL API
uvicorn BDNewsPaper.graphql_api:app --port 8001

# Dashboard
streamlit run app.py
```

---

## Available Spiders

79 spiders organized by category. The **Spider** column is the value you pass to `scrapy crawl`.

### Major Bangla Newspapers

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `prothomalo` | Prothom Alo | en.prothomalo.com | API |
| `jugantor` | Jugantor | jugantor.com | AJAX |
| `samakal` | Samakal | samakal.com | RSS + Sitemap |
| `ittefaq` | The Daily Ittefaq | ittefaq.com.bd | API |
| `kalerkantho_playwright` | Kaler Kantho | kalerkantho.com | HTML |
| `banglatribune` | Bangla Tribune | banglatribune.com | Sitemap |
| `nayadiganta` | Daily Naya Diganta | dailynayadiganta.com | Sitemap |
| `manabzamin` | Manab Zamin | mzamin.com | HTML |
| `janakantha` | Daily Janakantha | dailyjanakantha.com | HTML |
| `dailyinqilab` | Daily Inqilab | dailyinqilab.com | Sitemap |
| `dainikbangla` | Dainik Bangla | dainikbangla.com.bd | Sitemap |
| `sangbad` | Sangbad | sangbad.net.bd | RSS |
| `bhorerkagoj` | Bhorer Kagoj | bhorerkagoj.com | HTML |
| `dailysangram` | Daily Sangram | dailysangram.com | HTML |
| `amadershomoy` | Amader Shomoy | amadershomoy.com | Sitemap |
| `deshrupantor` | Desh Rupantor | deshrupantor.com | Sitemap |
| `ajkerpatrika` | Ajker Patrika | ajkerpatrika.com | RSS + Sitemap |
| `alokitobangladesh` | Alokito Bangladesh | alokitobangladesh.com | RSS + Sitemap |
| `risingbd` | Rising BD | risingbd.com | RSS |
| `jagonews24` | Jago News 24 | jagonews24.com | RSS |
| `dhakapost` | Dhaka Post | dhakapost.com | RSS + Sitemap |
| `barta24` | Barta24 | barta24.com | RSS + Sitemap |
| `sarabangla` | Sara Bangla | sarabangla.net | HTML |
| `bdpratidin_bangla` | Bangladesh Pratidin (Bangla) | bd-pratidin.com | RSS |
| `bdnews24_bangla` | bdnews24 (Bangla) | bangla.bdnews24.com | RSS + Sitemap |
| `dhakatimes24` | Dhaka Times 24 | dhakatimes24.com | RSS + Sitemap |

### Major English Newspapers

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `thedailystar` | The Daily Star | thedailystar.net | RSS |
| `dhakatribune` | Dhaka Tribune | dhakatribune.com | Sitemap |
| `bdnews24` | BD News 24 | bdnews24.com | Sitemap |
| `newage` | New Age | newagebd.net | RSS + Sitemap |
| `dailysun` | Daily Sun | daily-sun.com | RSS + Sitemap |
| `financialexpress` | The Financial Express | thefinancialexpress.com.bd | RSS + Sitemap |
| `theindependent` | The Independent | theindependentbd.com | RSS |
| `observerbd` | The Daily Observer | observerbd.com | HTML |
| `dailyasianage` | The Daily Asian Age | dailyasianage.com | RSS + Sitemap |
| `BDpratidin` | BD Pratidin (English) | en.bd-pratidin.com | RSS + Sitemap |
| `thedhakatimes` | The Dhaka Times | thedhakatimes.com | RSS + Sitemap |
| `bangladeshpost` | Bangladesh Post | bangladeshpost.net | HTML |
| `bangladesh_today` | The Bangladesh Today | thebangladeshtoday.com | HTML |
| `dhakacourier` | Dhaka Courier | dhakacourier.com.bd | RSS + Sitemap |

### TV Channels & Online Portals

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `ntvbd` | NTV BD (English) | en.ntvbd.com | Sitemap |
| `ntvbd_bangla` | NTV BD (Bangla) | ntvbd.com | Sitemap |
| `channeli` | Channel I Online | channelionline.com | RSS |
| `ekattor` | Ekattor TV | ekattor.tv | Sitemap |
| `ekusheytv` | Ekushey TV | ekushey-tv.com | RSS |
| `rtvonline` | RTV Online | rtvonline.com | RSS |
| `somoyertv` | Somoyer TV | somoyertv.com | RSS |
| `maasranga` | Maasranga TV | maasranga.tv | RSS |
| `itvbd` | ITV BD | itvbd.com | Sitemap |
| `banglavision` | Bangla Vision | banglavision.tv | HTML |
| `dbcnews` | DBC News | dbcnews.tv | RSS |
| `bd24live` | BD24Live | bd24live.com | RSS |
| `news24bd` | News24 BD | news24bd.tv | RSS |

### Wire Services

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `unb` | United News of Bangladesh (English) | unb.com.bd | API |
| `unbbangla` | UNB (Bangla) | unb.com.bd | API |
| `bssnews` | BSS News (English) | bssnews.net | Sitemap |
| `bssbangla` | BSS (Bangla) | bssnews.net | Sitemap |

### International Bangla Services

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `bbcbangla` | BBC Bangla | bbc.com | RSS + Sitemap |
| `dwbangla` | DW Bangla | dw.com | RSS + Sitemap |
| `voabangla` | VOA Bangla | voabangla.com | RSS + API |

### Business & Finance

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `tbsnews` | The Business Standard | tbsnews.net | RSS + Sitemap |
| `bonikbarta` | Bonik Barta | bonikbarta.com | Sitemap |
| `sharebiz` | ShareBiz | sharebiz.net | RSS + Sitemap |
| `arthosuchak` | Artho Suchak | arthosuchak.com | RSS + Sitemap |

### Tech

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `techshohor` | Tech Shohor | techshohor.com | RSS |

### Regional Newspapers

| Spider | Paper | Domain | Method |
|--------|-------|--------|--------|
| `ctgtimes` | CTG Times (Chittagong) | ctgtimes.com | RSS + Sitemap |
| `sylhetexpress` | Sylhet Express | sylhetexpress.net | HTML |
| `sylhetmirror` | Sylhet Mirror | sylhetmirror.com | RSS + Sitemap |
| `dailysylhet` | Daily Sylhet | dailysylhet.com | RSS + Sitemap |
| `khulnagazette` | Khulna Gazette | khulnagazette.com | RSS + Sitemap |
| `barishaltimes` | Barishal Times | barishaltimes.com | HTML |
| `rajshahipratidin` | Rajshahi Pratidin | rajshahipratidin.com | RSS + Sitemap |
| `dailybogra` | Daily Bogra | dailybogra.com | RSS + Sitemap |
| `comillarkagoj` | Comillar Kagoj | comillarkagoj.com | RSS + Sitemap |
| `coxsbazarnews` | Coxsbazar News | coxsbazarnews.com | RSS + Sitemap |
| `narayanganjtimes` | Narayanganj Times | narayanganjtimes.com | RSS + Sitemap |
| `netrokona24` | Netrokona 24 | netrokona24.com | RSS + Sitemap |
| `gramerkagoj` | Gramer Kagoj | gramerkagoj.com | RSS + Sitemap |

---

## Configuration

### Key Settings (`BDNewsPaper/settings.py`)

```python
# Anti-bot (all enabled by default)
SCRAPLING_ENABLED = True        # TLS fingerprint impersonation
CF_BYPASS_ENABLED = True        # Cloudflare bypass
STEALTH_HEADERS_ENABLED = True  # Browser-like headers
ANTIBOT_ENABLED = True          # Fingerprint randomization

# CAPTCHA solving (requires paid API key)
CAPTCHA_ENABLED = False
CAPTCHA_PROVIDER = 'capsolver'  # 2captcha, capsolver, anticaptcha, capmonster
CAPTCHA_API_KEY = ''            # Set via CAPTCHA_API_KEY env var

# Database
DATABASE_TYPE = 'sqlite'              # or 'postgresql'
SQLITE_DATABASE = 'news_articles.db'  # SQLite (default)
# PostgreSQL: Set DATABASE_TYPE=postgresql + POSTGRES_* env vars

# Date filtering (per-spider)
DATE_FILTER_ENABLED = False
# FILTER_START_DATE = '2026-01-01'
# FILTER_END_DATE = '2026-03-17'

# Concurrency
CONCURRENT_REQUESTS = 64
CONCURRENT_REQUESTS_PER_DOMAIN = 16
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_TYPE` | `sqlite` or `postgresql` | `sqlite` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DATABASE` | Database name | `bdnews` |
| `POSTGRES_USER` | Database user | `bdnews` |
| `POSTGRES_PASSWORD` | Database password | (required for pg) |
| `CAPTCHA_API_KEY` | CAPTCHA provider API key | (empty) |

---

## Docker

```bash
# Start API + Dashboard
docker compose up api dashboard

# Start with PostgreSQL
docker compose --profile production up

# Run a scrape
docker compose --profile scrape run scraper scrapy crawl prothomalo

# Full stack with monitoring (Prometheus + Grafana)
docker compose --profile monitoring up
```

---

## Development

```bash
# Install all dev dependencies
uv pip install -e ".[dev,cloudflare]"

# Run tests
python -m pytest tests/ -o "addopts=" -v

# Type checking
mypy BDNewsPaper/

# Format code
black BDNewsPaper/
isort BDNewsPaper/
```

---

## Architecture

```
BDNewsPaper/
├── spiders/                  # 79 newspaper spiders
│   └── base_spider.py       # Shared spider base class
├── items.py                  # NewsArticleItem data model
├── pipelines.py              # Validation, cleaning, dedup, SQLite storage
├── middlewares.py             # Retry, circuit breaker, throttling, archive fallback
├── cloudflare_bypass.py      # 9-level Cloudflare bypass
├── captcha_bypass.py         # CAPTCHA + Akamai/DataDome/PerimeterX/Incapsula
├── scrapling_integration.py  # Scrapling TLS impersonation
├── stealth_headers.py        # Browser-like request headers
├── antibot.py                # Browser fingerprint randomization
├── hybrid_request.py         # Auto HTTP/Playwright switching
├── honeypot.py               # Anti-bot trap link detection
├── proxy.py                  # Proxy rotation (single, rotating, residential, SOCKS5)
├── enums.py                  # Type-safe enums
├── api.py                    # REST API (FastAPI)
├── graphql_api.py            # GraphQL API (Strawberry)
├── search.py                 # Full-text search (FTS5 + BM25)
├── monitoring.py             # Health checks & alerts
├── postgres_pipeline.py      # PostgreSQL storage pipeline
└── extractors.py             # Fallback content extraction
```

---

## License

MIT
