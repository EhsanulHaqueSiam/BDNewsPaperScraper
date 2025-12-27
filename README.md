# 🗞️ BD Newspaper Scraper

<div align="center">

[![CI](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper/actions/workflows/ci.yml/badge.svg)](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper/actions/workflows/ci.yml)
[![Daily Scrape](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper/actions/workflows/daily-scrape.yml/badge.svg)](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper/actions/workflows/daily-scrape.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Scrapy](https://img.shields.io/badge/Scrapy-2.12+-60A839?logo=scrapy&logoColor=white)](https://scrapy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Spiders](https://img.shields.io/badge/Spiders-74-blue)](./todo.md)

**A high-performance web scraper for Bangladeshi newspapers built with [Scrapy](https://scrapy.org/).**

Collects news articles from **74+ major Bangladeshi news sources** (English & Bangla) and stores them in SQLite, PostgreSQL, or exports to various formats.

[Quick Start](#-quick-start) • [Usage](#%EF%B8%8F-usage) • [Spiders](#-available-spiders) • [API](#-api--integrations) • [Dashboard](#-dashboard--analytics) • [Deploy](#%EF%B8%8F-deployment)

</div>

---

## 📑 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Available Spiders](#-available-spiders)
- [Usage](#%EF%B8%8F-usage)
  - [Basic Commands](#basic-commands)
  - [Date Range Filtering](#date-range-filtering)
  - [Category Filtering](#category-filtering)
  - [Keyword Search](#keyword-search)
  - [Pagination Control](#pagination-control)
  - [Performance Settings](#performance-settings)
  - [CLI Interface](#cli-interface)
  - [Batch Running](#batch-running)
- [Data Export](#-data-export)
- [Database Schema](#%EF%B8%8F-database-schema)
- [Dashboard & Analytics](#-dashboard--analytics)
- [API & Integrations](#-api--integrations)
- [Bot Integrations](#-bot-integrations)
- [Cloud & Storage](#%EF%B8%8F-cloud--storage)
- [Deployment](#%EF%B8%8F-deployment)
- [Configuration](#%EF%B8%8F-configuration)
- [Configuration](#%EF%B8%8F-configuration)
- [Project Structure](#-project-structure-1)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ Features

### 🕷️ Web Scraping

| Feature | Description | Usage |
|---------|-------------|-------|
| **75+ Spiders** | English & Bangla newspapers | `scrapy crawl prothomalo` |
| **API-Based Scrapers** | Fast JSON API scraping | ProthomAlo, DailyStar, Jugantor |
| **Playwright Spider** | Cloudflare bypass | `scrapy crawl kalerkantho_playwright` |
| **Proxy Support** | Rotating, residential, SOCKS5 | `-s PROXY_ENABLED=true` |
| **Date Filtering** | Scrape by date range | `-a start_date=2024-01-01` |
| **Category Filtering** | Filter by news category | `-a categories=Sports,Politics` |

### 📊 Dashboards & Visualization

| Tool | Description | Command |
|------|-------------|---------|
| **Web GUI** | Streamlit control panel | `streamlit run app.py` |
| **Enhanced Dashboard** | Dark mode, mobile-friendly | `streamlit run scripts/dashboard_enhanced.py` |
| **Geo Mapping** | Leaflet.js Bangladesh maps | `python scripts/geo_mapping.py --generate` |
| **News Timeline** | Interactive timeline | `python scripts/news_timeline.py --generate` |
| **Status Page** | Spider health monitoring | `python scripts/status_page.py --serve` |

### 🔍 API & Search

| Tool | Description | Command |
|------|-------------|---------|
| **REST API** | FastAPI with rate limiting | `uvicorn BDNewsPaper.api:app` |
| **GraphQL API** | Flexible queries | `python scripts/graphql_api.py` |
| **Full-Text Search** | SQLite FTS5 | `python -m BDNewsPaper.search --query "..."` |
| **Elasticsearch** | Advanced search | `python scripts/elasticsearch_search.py --search "query"` |

### 🤖 ML & Analytics

| Tool | Description | Command |
|------|-------------|---------|
| **Topic Clustering** | K-Means, TF-IDF | `python scripts/topic_clustering.py --cluster` |
| **Sentiment Analysis** | Positive/negative | `python scripts/analytics.py --report` |
| **Bias Detection** | Political lean scoring | `python scripts/bias_detection.py --compare` |
| **Content Similarity** | Find duplicates | `python scripts/content_similarity.py --duplicates` |
| **Breaking News** | Spike detection | `python scripts/breaking_news.py --monitor` |

### 📡 Notifications & Bots

| Tool | Description | Command |
|------|-------------|---------|
| **Telegram Bot** | Daily summaries | `python scripts/telegram_bot.py --send` |
| **Slack Bot** | Slack notifications | `python scripts/slack_bot.py --send` |
| **Discord Bot** | Discord embeds | `python scripts/discord_bot.py --send` |
| **Webhook Alerts** | Custom webhooks | `python scripts/webhooks.py --monitor` |
| **Email Reports** | HTML email summaries | `python scripts/email_reports.py --send` |

### ☁️ Cloud & Storage

| Tool | Description | Command |
|------|-------------|---------|
| **S3 Backup** | AWS/DO Spaces | `python scripts/s3_storage.py --backup` |
| **Archive.org** | Wayback Machine | `python scripts/archive_org.py --archive-recent` |
| **Kaggle Upload** | Dataset publishing | `python scripts/kaggle_upload.py --upload` |
| **Hugging Face** | HF Hub dataset | `python scripts/huggingface_upload.py --upload` |
| **Redis Caching** | API response cache | Docker profile |
| **PostgreSQL** | Production database | Docker profile |

### 📧 Export & Reports

| Tool | Description | Command |
|------|-------------|---------|
| **Excel Export** | XLSX with filtering | `python scripts/toxlsx.py --all` |
| **RSS Feeds** | Generate RSS | `python scripts/rss_feed.py --generate` |
| **Performance Monitor** | Scraping metrics | `python scripts/performance_monitor.py` |

### 🏗️ Deployment

| Tool | Description | Command |
|------|-------------|---------|
| **Docker** | Container image | `docker build -t bdnews .` |
| **Docker Compose** | Full stack | `docker-compose up -d` |
| **Kubernetes** | K8s deployment | `kubectl apply -f kubernetes.yml` |
| **GitHub Pages** | Demo site | Auto-deployed |
| **CI/CD** | Auto test & deploy | On push to main |

### 🔧 Developer Tools

| Tool | Description | Location |
|------|-------------|----------|
| **Chrome Extension** | Clip articles | `chrome_extension/` |
| **CLI Tool** | Command-line | `python -m BDNewsPaper.cli` |
| **Batch Runner** | Run all spiders | `python run_spiders_optimized.py` |

---

## � Complete Scripts Reference (31 Scripts)

All scripts are in the `scripts/` directory. Run with `uv run python scripts/<script>.py`.

### 📊 Analytics & ML

| Script | Description | Usage |
|--------|-------------|-------|
| `analytics.py` | Sentiment analysis, entity extraction, trends | `--report`, `--sentiment`, `--entities`, `--trends` |
| `topic_clustering.py` | K-Means article clustering | `--cluster`, `--n-clusters 15`, `--similar "query"` |
| `bias_detection.py` | Political bias scoring | `--compare`, `--paper "Prothom Alo"` |
| `content_similarity.py` | Duplicate detection | `--duplicates`, `--threshold 0.85` |
| `breaking_news.py` | Spike detection & trending | `--monitor`, `--breaking`, `--trending` |

### 📈 Dashboards & Visualization

| Script | Description | Usage |
|--------|-------------|-------|
| `dashboard.py` | Basic Streamlit dashboard | `streamlit run scripts/dashboard.py` |
| `dashboard_enhanced.py` | Enhanced dark mode dashboard | `streamlit run scripts/dashboard_enhanced.py` |
| `status_page.py` | Spider health monitoring | `--serve`, `--port 8080` |
| `geo_mapping.py` | Leaflet.js Bangladesh maps | `--generate`, `--output map.html` |
| `news_timeline.py` | Interactive timeline | `--generate`, `--days 30` |
| `performance_monitor.py` | Scraping metrics | `--watch`, `--interval 60` |

### 📡 Notifications & Bots

| Script | Description | Usage |
|--------|-------------|-------|
| `telegram_bot.py` | Telegram notifications | `--send`, `--summary`, `--breaking` |
| `slack_bot.py` | Slack notifications | `--send`, `--channel "#news"` |
| `discord_bot.py` | Discord embeds | `--send`, `--webhook-url "..."` |
| `email_reports.py` | HTML email summaries | `--send`, `--recipients "a@b.com"` |
| `webhooks.py` | Custom webhook alerts | `--monitor`, `--url "..."` |
| `alerts.py` | Multi-channel alerts | `--send`, `--channels "telegram,slack"` |

### 🔍 Search & API

| Script | Description | Usage |
|--------|-------------|-------|
| `graphql_api.py` | GraphQL API server | `--serve`, `--port 8000` |
| `elasticsearch_search.py` | Elasticsearch indexing | `--index`, `--search "query"` |
| `redis_cache.py` | Redis caching layer | `--flush`, `--stats` |

### ☁️ Cloud & Storage

| Script | Description | Usage |
|--------|-------------|-------|
| `s3_storage.py` | AWS S3/DO Spaces backup | `--backup`, `--bucket "name"` |
| `archive_org.py` | Archive.org/Wayback | `--archive-recent`, `--url "..."` |
| `kaggle_upload.py` | Kaggle dataset upload | `--upload`, `--dataset "name"` |
| `huggingface_upload.py` | Hugging Face Hub | `--upload`, `--repo "user/repo"` |

### 📧 Export & Reports

| Script | Description | Usage |
|--------|-------------|-------|
| `toxlsx.py` | Excel export | `--all`, `--paper "name"`, `--limit 1000` |
| `rss_feed.py` | RSS feed generation | `--generate`, `--output feed.xml` |

### 🛠️ Maintenance & Testing

| Script | Description | Usage |
|--------|-------------|-------|
| `test_all_spiders.py` | Parallel spider testing | `--timeout 120`, `--max-items 2`, `--workers 10` |
| `canary_check.py` | Health monitoring | `--check`, `--alert-on-failure` |
| `fix_all_spiders.py` | Batch spider fixer | Adds fallback methods to spiders |
| `fix_article_extraction.py` | Fix parse_article methods | Adds extract_article_fallback |
| `update_spiders_fallback.py` | Update spider fallbacks | Batch update utility |

### Usage Examples

```bash
# Analytics report
uv run python scripts/analytics.py --report

# Topic clustering with 10 clusters
uv run python scripts/topic_clustering.py --cluster --n-clusters 10

# Find duplicate articles
uv run python scripts/content_similarity.py --duplicates --threshold 0.9

# Export to Excel
uv run python scripts/toxlsx.py --all --output all_news.xlsx

# Generate RSS feed
uv run python scripts/rss_feed.py --generate --output feed.xml

# Test all spiders (longer timeout)
uv run python scripts/test_all_spiders.py --timeout 120 --max-items 3

# Send Telegram notification
uv run python scripts/telegram_bot.py --send --summary

# Backup to S3
uv run python scripts/s3_storage.py --backup --bucket my-news-backup

# Run enhanced dashboard
uv run streamlit run scripts/dashboard_enhanced.py
```

### 🏠 Root-Level Scripts & Utilities

These scripts are in the project root directory:

| File | Description | Usage |
|------|-------------|-------|
| `app.py` | **Streamlit Web GUI** | `uv run streamlit run app.py` |
| `run_spiders_optimized.py` | **Batch spider runner** | `python run_spiders_optimized.py prothomalo dailysun` |
| `run_spiders_optimized.sh` | Batch runner (Linux/Mac) | `./run_spiders_optimized.sh --monitor` |
| `run_spiders_optimized.bat` | Batch runner (Windows) | `run_spiders_optimized.bat` |
| `setup.sh` | **Full project setup** | `./setup.sh` |
| `test_spiders.sh` | Quick spider tests | `./test_spiders.sh prothomalo` |
| `init.sql` | PostgreSQL schema | Used by Docker |
| `scrapy.cfg` | Scrapy configuration | Auto-loaded by Scrapy |

### 📦 BDNewsPaper Module Components

Key Python modules in `BDNewsPaper/`:

| Module | Description |
|--------|-------------|
| `api.py` | **FastAPI REST API** with rate limiting |
| `cli.py` | **CLI interface** (`python -m BDNewsPaper.cli`) |
| `search.py` | **Full-text search** (`python -m BDNewsPaper.search`) |
| `items.py` | Scrapy item definitions |
| `settings.py` | All configuration options |
| `pipelines.py` | 6 data processing pipelines |
| `middlewares.py` | 11 downloader middlewares |
| `extractors.py` | Content extraction utilities |
| `link_discovery.py` | Pattern-based URL discovery |
| `base_spider.py` | Base class with fallback methods |
| `auto_spider.py` | Universal self-healing spider |
| `proxy.py` | Multi-type proxy rotation |
| `cloudflare_bypass.py` | 7-level CF bypass |
| `stealth_headers.py` | Anti-bot headers |
| `hybrid_request.py` | Auto HTTP→Playwright switching |
| `honeypot.py` | Trap link detection |
| `antibot.py` | Browser fingerprint randomization |
| `geo_mimicry.py` | Bangladesh geo-location mimicry |

### 🧪 Test Suite

Tests are in `tests/` directory:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=BDNewsPaper --cov-report=html

# Run specific test file
uv run pytest tests/test_spider.py -v

# Run smoke tests only
uv run pytest tests/test_smoke.py -v
```

---

## �🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **UV Package Manager** — [Install UV](https://docs.astral.sh/uv/getting-started/installation/)

### Installation

```bash
# Clone repository
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper

# Option 1: Quick setup (recommended) - Works on Windows/Mac/Linux
python quickstart.py              # Basic setup
python quickstart.py dashboard    # With dashboard
python quickstart.py all          # All features

# Option 2: Bash script (Mac/Linux only)
./quickstart.sh

# Option 3: Manual setup
uv sync                           # Install dependencies
uv run playwright install chromium # Install browser

# Verify installation
uv run scrapy list
```

### Run Your First Scrape

```bash
# Quick test (10 articles)
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10

# Disable caching for fresh results
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10 -s HTTPCACHE_ENABLED=False

# Full scrape with monitoring
./run_spiders_optimized.sh prothomalo --monitor        # Linux/macOS
python run_spiders_optimized.py prothomalo --monitor   # Windows/All platforms

# Check results
python scripts/toxlsx.py --list
```

### 🖥️ Launch Web GUI

```bash
# Install GUI dependencies
uv sync --extra gui

# Launch Streamlit interface
uv run streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 📰 Available Spiders

### English Newspapers (22)

| Spider | Source | Method | Speed |
|--------|--------|--------|-------|
| `prothomalo` | [ProthomAlo](https://en.prothomalo.com/) | API | ⚡ Fast |
| `thedailystar` | [The Daily Star](https://www.thedailystar.net/) | API | ⚡ Fast |
| `dailysun` | [Daily Sun](https://www.daily-sun.com/) | AJAX | ⚡ Fast |
| `tbsnews` | [TBS News](https://www.tbsnews.net/) | Drupal AJAX | ⚡ Fast |
| `unb` | [UNB](https://unb.com.bd/) | API | ⚡ Fast |
| `ittefaq` | [Daily Ittefaq](https://en.ittefaq.com.bd/) | AJAX | ⚡ Fast |
| `bssnews` | [BSS News](https://www.bssnews.net/) | HTML | 🔄 Medium |
| `ntvbd` | [NTV BD](https://en.ntvbd.com/) | HTML | 🔄 Medium |
| `dhakatribune` | [Dhaka Tribune](https://www.dhakatribune.com/) | HTML | 🔄 Medium |
| `financialexpress` | [Financial Express](https://thefinancialexpress.com.bd/) | HTML | 🔄 Medium |
| `newage` | [New Age](https://www.newagebd.net/) | HTML | 🔄 Medium |
| `bdnews24` | [bdnews24](https://bdnews24.com/) | HTML | 🔄 Medium |
| `BDpratidin` | [BD Pratidin](https://en.bd-pratidin.com/) | HTML | 🔄 Medium |
| `bangladesh_today` | [Bangladesh Today](https://thebangladeshtoday.com/) | HTML | 🔄 Medium |
| `theindependent` | [The Independent](https://theindependentbd.com/) | RSS | 🔄 Medium |
| `observerbd` | [Observer BD](https://observerbd.com/) | HTML | 🔄 Medium |
| `bangladeshpost` | [Bangladesh Post](https://bangladeshpost.net/) | HTML | 🔄 Medium |
| `dailyasianage` | [Asian Age](https://dailyasianage.com/) | HTML | 🔄 Medium |
| `dhakacourier` | [Dhaka Courier](https://dhakacourier.com.bd/) | HTML | 🔄 Medium |
| `bd24live` | [BD24Live](https://bd24live.com/) | HTML | 🔄 Medium |
| `sylhetmirror` | [Sylhet Mirror](https://sylhetmirror.com/) | HTML | 🔄 Medium |
| `thedhakatimes` | [The Dhaka Times](https://thedhakatimes.com/) | WP API | ⚡ Fast |

### Bangla Newspapers (52)

<details>
<summary>Click to expand full list</summary>

| Spider | Source | Type |
|--------|--------|------|
| `jugantor` | [Jugantor](https://www.jugantor.com/) | JSON API ⚡ |
| `banglatribune` | [Bangla Tribune](https://www.banglatribune.com/) | HTML |
| `samakal` | [Samakal](https://samakal.com/) | HTML |
| `jagonews24` | [Jago News 24](https://www.jagonews24.com/) | HTML |
| `risingbd` | [Rising BD](https://www.risingbd.com/) | HTML |
| `bdnews24_bangla` | [bdnews24 Bangla](https://bangla.bdnews24.com/) | HTML |
| `nayadiganta` | [Naya Diganta](https://dailynayadiganta.com/) | HTML |
| `bdpratidin_bangla` | [BD Pratidin](https://www.bd-pratidin.com/) | HTML |
| `manabzamin` | [Manab Zamin](https://www.mzamin.com/) | HTML |
| `bonikbarta` | [Bonik Barta](https://www.bonikbarta.net/) | HTML |
| `deshrupantor` | [Desh Rupantor](https://www.deshrupantor.com/) | HTML |
| `janakantha` | [Janakantha](https://www.dailyjanakantha.com/) | HTML |
| `bhorerkagoj` | [Bhorer Kagoj](https://bhorerkagoj.com/) | HTML |
| `dailyinqilab` | [Daily Inqilab](https://dailyinqilab.com/) | HTML |
| `sangbad` | [Sangbad](https://sangbad.net.bd/) | HTML |
| `ntvbd_bangla` | [NTV Bangla](https://www.ntvbd.com/) | HTML |
| `alokitobangladesh` | [Alokito Bangladesh](https://alokitobangladesh.com/) | HTML |
| `dainikbangla` | [Dainik Bangla](https://dainikbangla.com.bd/) | HTML |
| `dhakapost` | [Dhaka Post](https://dhakapost.com/) | HTML |
| `sarabangla` | [Sara Bangla](https://sarabangla.net/) | HTML |
| `maasranga` | [Maasranga TV](https://maasranga.tv/) | WP API ⚡ |
| `dbcnews` | [DBC News](https://dbcnews.tv/) | HTML |
| `itvbd` | [ITV BD](https://itvbd.com/) | HTML |
| `ajkerpatrika` | [Ajker Patrika](https://ajkerpatrika.com/) | API ⚡ |
| `dailysangram` | [Daily Sangram](https://dailysangram.com/) | HTML |
| `amadershomoy` | [Amader Shomoy](https://dainikamadershomoy.com/) | HTML |
| `rtvonline` | [RTV Online](https://rtvonline.com/) | HTML |
| `channeli` | [Channel I](https://channelionline.com/) | HTML |
| `ekattor` | [Ekattor TV](https://ekattor.tv/) | HTML |
| `banglavision` | [Bangla Vision](https://banglavision.tv/) | HTML |
| `news24bd` | [News 24](https://news24bd.tv/) | HTML |
| `unbbangla` | [UNB Bangla](https://unb.com.bd/bangla) | API ⚡ |
| `bssbangla` | [BSS Bangla](https://bssnews.net/bangla) | HTML |
| `bbcbangla` | [BBC Bangla](https://bbc.com/bengali) | JSON ⚡ |
| `dwbangla` | [DW Bangla](https://dw.com/bn) | JSON ⚡ |
| `voabangla` | [VOA Bangla](https://voabangla.com/) | RSS ⚡ |
| `barta24` | [Barta24](https://barta24.com/) | API ⚡ |
| `coxsbazarnews` | [Coxsbazar News](https://coxsbazarnews.com/) | HTML |
| `dailysylhet` | [Daily Sylhet](https://dailysylhet.com/) | WP API ⚡ |
| `sylhetexpress` | [Sylhet Express](https://sylhetexpress.net/) | HTML |
| `khulnagazette` | [Khulna Gazette](https://khulnagazette.com/) | WP API ⚡ |
| `barishaltimes` | [Barishal Times](https://barishaltimes.com/) | HTML |
| `narayanganjtimes` | [Narayanganj Times](https://narayanganjtimes.com/) | HTML |
| `techshohor` | [Tech Shohor](https://techshohor.com/) | HTML |
| `ekusheytv` | [Ekushey TV](https://ekushey-tv.com/) | HTML |
| `arthosuchak` | [Artho Suchak](https://arthosuchak.com/) | HTML |
| `sharebiz` | [Share Biz](https://sharebiz.net/) | HTML |
| `dhakatimes24` | [Dhaka Times 24](https://dhakatimes24.com/) | HTML |
| `ctgtimes` | [CTG Times](https://ctgtimes.com/) | HTML |
| `gramerkagoj` | [Gramer Kagoj](https://gramerkagoj.com/) | HTML |
| `comillarkagoj` | [Comillar Kagoj](https://comillarkagoj.com/) | HTML |
| `netrokona24` | [Netrokona 24](https://netrokona24.com/) | HTML |

</details>

> ⚠️ **Note**: Kaler Kantho is Cloudflare protected. Use the Playwright spider for browser automation (see below).

### Playwright Spider (Cloudflare Bypass)

For Cloudflare-protected or JavaScript-heavy sites, use the Playwright spider with browser automation.

#### Setup

```bash
# Install Playwright dependencies
pip install scrapy-playwright playwright

# Install browser (Chromium)
playwright install chromium
```

#### Usage

```bash
# Run Kaler Kantho spider with Playwright
uv run scrapy crawl kalerkantho_playwright

# Generic Playwright spider for any URL
uv run scrapy crawl generic_playwright -a url="https://example.com" -a selector="article"

# With custom content selector
uv run scrapy crawl generic_playwright -a url="https://kalerkantho.com/online/national" -a selector=".news-item"
```

#### Available Playwright Spiders

| Spider | Description | Usage |
|--------|-------------|-------|
| `kalerkantho_playwright` | Kaler Kantho (all categories) | `scrapy crawl kalerkantho_playwright` |
| `generic_playwright` | Any Cloudflare-protected site | `scrapy crawl generic_playwright -a url=... -a selector=...` |

#### Configuration Options

```bash
# Headless mode (default: true)
uv run scrapy crawl kalerkantho_playwright -s PLAYWRIGHT_LAUNCH_OPTIONS='{"headless": true}'

# With visible browser for debugging
uv run scrapy crawl kalerkantho_playwright -s PLAYWRIGHT_LAUNCH_OPTIONS='{"headless": false}'

# Increase timeout for slow pages (default: 60 seconds)
uv run scrapy crawl kalerkantho_playwright -s PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT=120000

# Reduce concurrent requests (recommended for Playwright)
uv run scrapy crawl kalerkantho_playwright -s CONCURRENT_REQUESTS=4 -s DOWNLOAD_DELAY=3
```

#### How It Works

1. **Browser Automation**: Uses headless Chromium to render JavaScript
2. **Cloudflare Bypass**: Waits for Cloudflare challenge to complete (~5 seconds)
3. **Dynamic Content**: Scrolls page and waits for AJAX content to load
4. **Anti-Detection**: Disables automation flags to avoid bot detection

#### Troubleshooting Playwright

| Issue | Solution |
|-------|----------|
| `playwright not installed` | Run `pip install scrapy-playwright playwright && playwright install chromium` |
| `Browser launch failed` | Ensure Chromium dependencies are installed: `playwright install-deps chromium` |
| `Timeout waiting for selector` | Increase timeout or check if selector is correct |
| `Cloudflare still blocking` | Try adding more delay with `-s DOWNLOAD_DELAY=5` |
| `Memory issues` | Reduce `CONCURRENT_REQUESTS` to 2-4 |

### 🔧 Universal Self-Healing Spider (NEW)

The `autonews` spider works on **ANY news website** without custom configuration. It uses pattern-based link discovery and multi-layer extraction fallbacks.

#### Quick Start

```bash
# Scrape ANY news site automatically
uv run scrapy crawl autonews -a url="https://www.risingbd.com/"

# Multiple start URLs
uv run scrapy crawl autonews -a urls="https://samakal.com/,https://risingbd.com/"

# With item limit
uv run scrapy crawl autonews -a url="https://www.bhorerkagoj.com/" -s CLOSESPIDER_ITEMCOUNT=10
```

#### How It Works

1. **Pattern-based Link Discovery** - Finds article URLs using URL patterns (no CSS selectors needed)
2. **JSON-LD Extraction** - Extracts structured data first (most reliable)
3. **Generic CSS Selectors** - Falls back to 22 common CSS patterns
4. **Self-Healing** - If one method fails, automatically tries the next

#### Features

| Feature | Description |
|---------|-------------|
| 🔄 **Self-healing** | Automatically adapts when website layouts change |
| 🌐 **Works on any site** | No custom selectors needed |
| 🚀 **Fast discovery** | Pattern-based URL detection |
| 📊 **Full extraction** | Headlines, body, dates, authors, images |

---

## 🛡️ Middleware & Robustness Features

This scraper includes **11 downloader middlewares** and **6 pipelines** for maximum reliability.

### Downloader Middlewares (Request/Response Processing)

| Middleware | Priority | Purpose | Toggle |
|------------|----------|---------|--------|
| `StealthHeadersMiddleware` | 350 | Anti-bot headers | `STEALTH_HEADERS_ENABLED` |
| `UserAgentMiddleware` | 400 | UA rotation | Always on |
| `ProxyMiddleware` | 410 | Proxy rotation | `PROXY_ENABLED` |
| `CloudflareBypassMiddleware` | 430 | CF bypass (7 levels) | `CF_BYPASS_ENABLED` |
| `CircuitBreakerMiddleware` | 451 | Prevents hammering failed sites | `CIRCUIT_BREAKER_*` |
| `StatisticsMiddleware` | 460 | Request/response tracking | Always on |
| `AdaptiveThrottlingMiddleware` | 470 | Dynamic delay adjustment | `ADAPTIVE_THROTTLE_ENABLED` |
| `RateLimitMiddleware` | 500 | Request rate limiting | `RATELIMIT_*` |
| `HybridRequestMiddleware` | 540 | Auto HTTP→Playwright switch | `HYBRID_REQUEST_ENABLED` |
| `SmartRetryMiddleware` | 550 | Exponential backoff retry | `RETRY_*` |
| `ArchiveFallbackMiddleware` | 650 | Wayback Machine fallback | `ARCHIVE_FALLBACK_ENABLED` |

### Item Pipelines (Data Processing)

| Pipeline | Priority | Purpose |
|----------|----------|---------|
| `FallbackExtractionPipeline` | 50 | Re-extract content if spider fails |
| `ValidationPipeline` | 100 | Validate required fields |
| `CleanArticlePipeline` | 200 | Clean HTML, normalize text |
| `LanguageDetectionPipeline` | 210 | Detect article language |
| `ContentQualityPipeline` | 220 | Check word count, special chars |
| `SharedSQLitePipeline` | 300 | Save to database |

### Usage Examples

#### Enable Proxy Rotation
```bash
# Single proxy
uv run scrapy crawl prothomalo -s PROXY_ENABLED=true -s PROXY_URL="http://user:pass@host:port"

# Rotating proxies from file
uv run scrapy crawl prothomalo -s PROXY_ENABLED=true -s PROXY_TYPE=rotating -s PROXY_LIST=proxies.txt

# Residential proxies (Brightdata, Oxylabs, etc.)
uv run scrapy crawl prothomalo -s PROXY_ENABLED=true -s PROXY_TYPE=residential -s RESIDENTIAL_PROVIDER=brightdata
```

#### Configure Retry Behavior
```bash
# Custom retry settings
uv run scrapy crawl prothomalo \
  -s RETRY_TIMES=5 \
  -s RETRY_HTTP_CODES="500,502,503,504,429" \
  -s RETRY_BACKOFF_FACTOR=2.0
```

#### Cloudflare Bypass (7 Levels)
```bash
# Auto-escalating CF bypass (enabled by default)
uv run scrapy crawl dailysun -s CF_BYPASS_ENABLED=true

# With Flaresolverr (Docker)
docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr
uv run scrapy crawl dailysun -s FLARESOLVERR_URL="http://localhost:8191/v1"
```

#### Adaptive Throttling
```bash
# Configure throttling thresholds
uv run scrapy crawl prothomalo \
  -s ADAPTIVE_THROTTLE_ENABLED=true \
  -s ADAPTIVE_THROTTLE_THRESHOLD_MS=500 \
  -s ADAPTIVE_THROTTLE_MIN_DELAY=0.5 \
  -s ADAPTIVE_THROTTLE_MAX_DELAY=10.0
```

#### Circuit Breaker
```bash
# Prevent hammering failed sites
uv run scrapy crawl prothomalo \
  -s CIRCUIT_BREAKER_THRESHOLD=5 \
  -s CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

#### Content Quality Filters
```bash
# Strict content validation
uv run scrapy crawl prothomalo \
  -s MIN_ARTICLE_WORDS=50 \
  -s MAX_ARTICLE_WORDS=10000 \
  -s MAX_SPECIAL_CHAR_RATIO=0.3
```

#### Language Detection
```bash
# Only keep English articles
uv run scrapy crawl prothomalo \
  -s LANGUAGE_DETECTION_ENABLED=true \
  -s LANGUAGE_DETECTION_STRICT=true \
  -s EXPECTED_LANGUAGES="en"
```

#### Archive Fallback (Wayback Machine)
```bash
# Fetch from Wayback when sites return 404/403
uv run scrapy crawl prothomalo \
  -s ARCHIVE_FALLBACK_ENABLED=true \
  -s ARCHIVE_FALLBACK_CODES="404,403,410"
```

#### Hybrid Request (Auto Playwright)
```bash
# Auto-switch to Playwright for JS sites
uv run scrapy crawl dailysun -s HYBRID_REQUEST_ENABLED=true
```

### Performance Tuning

```bash
# High-speed aggressive scraping
uv run scrapy crawl prothomalo \
  -s CONCURRENT_REQUESTS=64 \
  -s CONCURRENT_REQUESTS_PER_DOMAIN=16 \
  -s DOWNLOAD_DELAY=0.25 \
  -s AUTOTHROTTLE_ENABLED=false

# Conservative/polite scraping
uv run scrapy crawl prothomalo \
  -s CONCURRENT_REQUESTS=4 \
  -s DOWNLOAD_DELAY=3 \
  -s AUTOTHROTTLE_ENABLED=true

# Memory-limited (2GB)
uv run scrapy crawl prothomalo \
  -s MEMUSAGE_ENABLED=true \
  -s MEMUSAGE_LIMIT_MB=2048
```

### All Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `DOWNLOAD_TIMEOUT` | 120 | Request timeout (seconds) |
| `CONCURRENT_REQUESTS` | 64 | Max concurrent requests |
| `DOWNLOAD_DELAY` | 0.5 | Delay between requests |
| `PROXY_ENABLED` | false | Enable proxy rotation |
| `CF_BYPASS_ENABLED` | true | Enable Cloudflare bypass |
| `HYBRID_REQUEST_ENABLED` | true | Auto HTTP→Playwright |
| `STEALTH_HEADERS_ENABLED` | true | Anti-bot headers |
| `ADAPTIVE_THROTTLE_ENABLED` | true | Dynamic delay adjustment |
| `ARCHIVE_FALLBACK_ENABLED` | true | Wayback Machine fallback |
| `FALLBACK_EXTRACTION_ENABLED` | true | Re-extract failed content |
| `LANGUAGE_DETECTION_ENABLED` | true | Detect article language |
| `HONEYPOT_DETECTION_ENABLED` | false | Avoid trap links |
| `VALIDATION_STRICT_MODE` | true | Drop invalid items |

## 🛠️ Usage

### Basic Commands

```bash
# List all available spiders
uv run scrapy list

# Run a specific spider
uv run scrapy crawl prothomalo

# Limit number of articles
uv run scrapy crawl dailysun -s CLOSESPIDER_ITEMCOUNT=100

# Enable debug logging
uv run scrapy crawl BDpratidin -L DEBUG
```

---

### Date Range Filtering

All spiders support date filtering using the `start_date` and `end_date` arguments in `YYYY-MM-DD` format.

```bash
# Scrape articles from a specific month
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31

# Scrape from a specific date to today
uv run scrapy crawl dailysun -a start_date=2024-08-01

# Scrape only end date (from default start to specific end)
uv run scrapy crawl thedailystar -a end_date=2024-06-30

# Combine with item limit
uv run scrapy crawl thedailystar -a start_date=2024-06-01 -a end_date=2024-06-30 -s CLOSESPIDER_ITEMCOUNT=500
```

**How Date Filtering Works:**
- **API-based spiders** (prothomalo, dailysun, jugantor): Dates are sent directly to the API for efficient server-side filtering
- **HTML-based spiders**: Client-side filtering; articles outside the date range are skipped during parsing
- **Default**: If no dates specified, scrapes from 30 days ago to today

---

### Category Filtering

Filter articles by category using the `-a categories=` argument. Categories are comma-separated.

#### ProthomAlo Categories
```bash
# Available: Bangladesh, Politics, Sports, Business, Opinion, Entertainment, Youth, World, Environment, Science & Tech, Corporate, Lifestyle, Photo, Video
uv run scrapy crawl prothomalo -a categories=Bangladesh,Sports
uv run scrapy crawl prothomalo -a categories=Politics,Business,Opinion
```

#### Daily Sun Categories
```bash
# Available: Bangladesh, Business, World, Entertainment, Sports, Lifestyle, Tech, Opinion
uv run scrapy crawl dailysun -a categories=Bangladesh,Sports
uv run scrapy crawl dailysun -a categories=Business,Tech
```

#### The Daily Star Categories
```bash
# Available: Bangladesh, Politics, World, Business, Sports, Opinion, Entertainment, Tech
uv run scrapy crawl thedailystar -a categories=Bangladesh,Sports,Politics
```

#### Ittefaq Categories
```bash
# Available: Bangladesh, International, Sports, Business, Entertainment, Opinion
uv run scrapy crawl ittefaq -a categories=Bangladesh,Sports
```

#### BD Pratidin Categories
```bash
# Available: national, international, sports, showbiz, economy, shuvosangho
uv run scrapy crawl BDpratidin -a categories=national,sports
```

#### Bangladesh Today Categories
```bash
# Available: Bangladesh, Nationwide, Entertainment, International, Sports
uv run scrapy crawl bangladesh_today -a categories=Bangladesh,Sports
```

**Combine with date filtering:**
```bash
uv run scrapy crawl prothomalo -a categories=Sports,Politics -a start_date=2024-12-01 -a end_date=2024-12-25
```

---

### Keyword Search

Search for articles containing specific keywords. Supported by API-based spiders.

```bash
# Search in ProthomAlo (API-level search)
uv run scrapy crawl prothomalo -a search_query="Sheikh Hasina"
uv run scrapy crawl prothomalo -a search_query="Bangladesh election"

# Search in Daily Sun
uv run scrapy crawl dailysun -a search_query="cricket"
uv run scrapy crawl dailysun -a search_query="economy budget"

# Search in Ittefaq
uv run scrapy crawl ittefaq -a search_query="politics"

# Combine search with date range
uv run scrapy crawl prothomalo -a search_query="BNP" -a start_date=2024-01-01 -a end_date=2024-06-30

# Multiple keywords (OR logic for some spiders)
uv run scrapy crawl prothomalo -a search_query="election,politics,vote"
```

**Search Support by Spider:**

| Spider | API Search | Notes |
|--------|------------|-------|
| `prothomalo` | ✅ Yes | Full API search with date/category filters |
| `dailysun` | ✅ Yes | Search via `/search?q=` endpoint |
| `ittefaq` | ✅ Yes | AJAX search |
| `jugantor` | ✅ Yes | JSON API search |
| Others | ⚠️ Client-side | Keywords matched during HTML parsing |

---

### Pagination Control

Control how many pages of articles to scrape.

```bash
# Limit maximum pages per category (default: 50)
uv run scrapy crawl prothomalo -a max_pages=10

# Items per page (for supported spiders)
uv run scrapy crawl dailysun -a items_per_page=50

# Page limit for API spiders
uv run scrapy crawl prothomalo -a page_limit=100

# Sort order (for prothomalo)
uv run scrapy crawl prothomalo -a sort=latest-published    # default
uv run scrapy crawl prothomalo -a sort=oldest-published
uv run scrapy crawl prothomalo -a sort=relevance           # for search

# Story type filter (for prothomalo)
uv run scrapy crawl prothomalo -a story_type=text          # text, photo, video, live-blog
```

---

### Performance Settings

Control request speed and concurrency via Scrapy settings.

```bash
# Add delay between requests (seconds)
uv run scrapy crawl ittefaq -s DOWNLOAD_DELAY=2

# Limit concurrent requests
uv run scrapy crawl dhakatribune -s CONCURRENT_REQUESTS=4

# Concurrent requests per domain
uv run scrapy crawl prothomalo -s CONCURRENT_REQUESTS_PER_DOMAIN=8

# Enable autothrottle (adaptive delay)
uv run scrapy crawl dailysun -s AUTOTHROTTLE_ENABLED=true

# High-speed aggressive scraping (use with caution)
uv run scrapy crawl prothomalo -s CONCURRENT_REQUESTS=32 -s DOWNLOAD_DELAY=0.25

# Conservative/polite scraping
uv run scrapy crawl dailysun -s CONCURRENT_REQUESTS=2 -s DOWNLOAD_DELAY=3

# Retry settings
uv run scrapy crawl bdnews24 -s RETRY_TIMES=5 -s RETRY_HTTP_CODES=403,429,500,502,503
```

---

### CLI Interface

Use the built-in CLI for easier scraping:

```bash
# List available spiders with capabilities
uv run python -m BDNewsPaper.cli list
uv run python -m BDNewsPaper.cli list --verbose

# Scrape specific newspapers
uv run python -m BDNewsPaper.cli scrape --newspapers prothomalo dailysun

# Scrape with date range
uv run python -m BDNewsPaper.cli scrape --from 2024-12-01 --to 2024-12-25

# Scrape with category filter
uv run python -m BDNewsPaper.cli scrape --newspapers prothomalo --categories Bangladesh Sports

# Search for keywords
uv run python -m BDNewsPaper.cli scrape --newspapers prothomalo --search "Sheikh Hasina"

# Combine all options
uv run python -m BDNewsPaper.cli scrape \
  --newspapers prothomalo dailysun \
  --from 2024-12-01 \
  --to 2024-12-25 \
  --categories Bangladesh Politics \
  --search "election" \
  --max-pages 20 \
  --output articles.json

# Output to file (JSON or CSV based on extension)
uv run python -m BDNewsPaper.cli scrape --newspapers prothomalo --output news.json
uv run python -m BDNewsPaper.cli scrape --newspapers prothomalo --output news.csv
```

**CLI Help:**
```bash
uv run python -m BDNewsPaper.cli --help
uv run python -m BDNewsPaper.cli scrape --help
```

---

### Batch Running

Run multiple spiders efficiently:

```bash
# Linux/macOS
./run_spiders_optimized.sh                              # Run all spiders
./run_spiders_optimized.sh prothomalo dailysun          # Run specific spiders
./run_spiders_optimized.sh --monitor                    # With performance monitoring
./run_spiders_optimized.sh --start-date 2024-01-01 --end-date 2024-01-31

# Windows / Cross-platform
python run_spiders_optimized.py
python run_spiders_optimized.py prothomalo dailysun --monitor
python run_spiders_optimized.py --start-date 2024-01-01 --end-date 2024-01-31
```

---

## 💾 Data Export

### View Database Summary

```bash
python toxlsx.py --list
```

**Output:**
```
Shared News Articles Database
========================================
Database file: news_articles.db
Total articles: 15,432

Articles by newspaper:
------------------------------
  Prothom Alo: 3,421 articles
  Daily Sun: 2,156 articles
  ...
```

### Export to Excel

```bash
# Export all articles to Excel
python toxlsx.py --output all_news.xlsx

# Export specific newspaper
python toxlsx.py --paper "Prothom Alo" --output prothomalo.xlsx

# Export with limit (most recent first)
python toxlsx.py --limit 500 --output recent.xlsx

# Combine filters
python toxlsx.py --paper "Daily Sun" --limit 100 --output dailysun_100.xlsx
```

### Export to CSV

```bash
# Export all to CSV
python toxlsx.py --format csv --output news_data.csv

# Export specific newspaper to CSV
python toxlsx.py --paper "Prothom Alo" --format csv --output prothomalo.csv
```

### Direct Database Queries

```bash
# Count articles by newspaper
sqlite3 news_articles.db "SELECT paper_name, COUNT(*) FROM articles GROUP BY paper_name ORDER BY COUNT(*) DESC;"

# View recent headlines
sqlite3 news_articles.db "SELECT headline, paper_name, publication_date FROM articles ORDER BY scraped_at DESC LIMIT 10;"

# Search articles
sqlite3 news_articles.db "SELECT headline, url FROM articles WHERE headline LIKE '%cricket%' LIMIT 20;"

# Export specific columns to CSV
sqlite3 -header -csv news_articles.db "SELECT url, headline, paper_name, publication_date FROM articles LIMIT 1000;" > export.csv

# Get date range
sqlite3 news_articles.db "SELECT MIN(publication_date), MAX(publication_date) FROM articles;"
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,        -- Article URL (unique identifier)
    paper_name TEXT NOT NULL,        -- Newspaper name
    headline TEXT NOT NULL,          -- Article title
    article TEXT NOT NULL,           -- Full article content
    publication_date TEXT,           -- Publication date
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster queries
CREATE INDEX idx_paper_name ON articles(paper_name);
CREATE INDEX idx_publication_date ON articles(publication_date);
CREATE INDEX idx_scraped_at ON articles(scraped_at);

-- Full-text search index (if enabled)
CREATE VIRTUAL TABLE articles_fts USING fts5(
    headline, article, content='articles'
);
```

---

## 📊 Dashboard & Analytics

### Web Dashboard

```bash
# Install dashboard dependencies
uv sync --extra dashboard

# Launch basic dashboard
uv run streamlit run dashboard.py

# Launch enhanced dashboard with more features
uv run streamlit run dashboard_enhanced.py
```

**Features:**
- 📊 Article statistics and charts
- 📈 Daily trend analysis
- ☁️ Word cloud from headlines
- 🔥 Trending keywords
- 🔍 Advanced search
- 📰 Latest headlines viewer

### Analytics Tools

```bash
# Install analytics dependencies
uv sync --extra analytics

# Generate full analytics report
python analytics.py --report

# Sentiment analysis only
python analytics.py --sentiment

# Extract entities (people, organizations)
python analytics.py --entities

# Trending keywords
python analytics.py --trends

# Find duplicate articles
python analytics.py --duplicates
```

### Topic Clustering

```bash
# ML-based article clustering
python topic_clustering.py --cluster

# Cluster with custom number of clusters
python topic_clustering.py --cluster --n-clusters 15

# Cluster articles from specific days
python topic_clustering.py --cluster --days 14

# Find articles similar to a query
python topic_clustering.py --similar "Bangladesh election"

# Get trending topics
python topic_clustering.py --trending

# Save clusters to JSON
python topic_clustering.py --cluster --output clusters.json
```

**Dependencies:** `pip install scikit-learn numpy`

### Breaking News Detection

```bash
# Real-time spike detection (continuous monitoring)
python breaking_news.py --monitor

# Get current breaking news
python breaking_news.py --breaking

# Get trending topics
python breaking_news.py --trending

# Save breaking news report
python breaking_news.py --report

# Set custom monitoring interval (seconds)
python breaking_news.py --monitor --interval 300
```

**Features:**
- Spike detection (keyword velocity tracking)
- Multi-source correlation
- Configurable thresholds (2x baseline = breaking)

### Content Similarity & Duplicates

Find duplicate and similar articles using TF-IDF similarity.

```bash
# Find duplicate articles (default threshold: 85%)
python content_similarity.py --duplicates

# Find duplicates with custom threshold
python content_similarity.py --duplicates --threshold 0.9

# Find articles similar to a query
python content_similarity.py --similar "Bangladesh election"

# Generate duplicate analysis report
python content_similarity.py --report

# Analyze duplicates from last N days
python content_similarity.py --duplicates --days 7
```

**Dependencies:** `pip install scikit-learn numpy`

### Bias Detection

Analyze political bias and sentiment in news reporting.

```bash
# Compare bias across all sources
python bias_detection.py --compare

# Analyze specific newspaper
python bias_detection.py --source "Prothom Alo"

# Analyze topic coverage across sources
python bias_detection.py --topic "election"

# Generate full bias report
python bias_detection.py --report

# Analyze articles from last N days
python bias_detection.py --compare --days 30
```

**Metrics:**
- Left/right lean scoring (lexicon-based)
- Positive/negative sentiment ratio
- Neutral content percentage

### News Timeline

```bash
# Generate interactive timeline visualization
python news_timeline.py --generate

# Generate timeline for specific days
python news_timeline.py --generate --days 7

# Filter by topic
python news_timeline.py --generate --topic "politics"

# Serve timeline via HTTP
python news_timeline.py --serve --port 8080

# Generate JSON for API
python news_timeline.py --json
```

### Geographical Mapping

Plot news articles on a Bangladesh map based on location mentions.

```bash
# Generate interactive map (last 30 days)
python geo_mapping.py --generate

# Generate map for specific days
python geo_mapping.py --generate --days 7

# Generate heatmap visualization
python geo_mapping.py --generate --heatmap

# Generate JSON for API consumption
python geo_mapping.py --json

# Show location statistics
python geo_mapping.py --stats
```

**Output Files:**
- `maps/news_map.html` - Interactive Leaflet.js map
- `maps/news_heatmap.html` - Heatmap visualization
- `maps/locations.json` - JSON data for API

### Status Page & Health Monitor

Monitor the health and status of all spiders.

```bash
# Generate status page
python status_page.py --generate

# Test all spiders and generate status
python status_page.py --test

# Test specific number of spiders
python status_page.py --test --limit 10

# Serve status page
python status_page.py --serve --port 8081
```

**Output Files:**
- `status/index.html` - Spider status dashboard
- Shows: Last run time, article counts, success rate

### Performance Monitor

Track scraping performance and generate reports.

```bash
# Start real-time monitoring (updates every 30 seconds)
python performance_monitor.py

# Generate performance report (JSON)
python performance_monitor.py report

# Show quick stats
python performance_monitor.py stats
```

**Report Includes:**
- Articles per hour
- Articles by newspaper
- Average article length
- Last 24 hours / 1 hour stats

### Testing Spiders

Quick test all spiders with minimal items.

```bash
# Test all spiders (2 items each, ~2 min timeout)
python test_all_spiders.py
```

**Features:**
- Tests each spider with 2 item limit
- 2 minute timeout per spider
- Skips Playwright spiders (require special setup)
- Summary of successful/failed spiders

---

## 📡 API & Integrations

### REST API

```bash
# Install API dependencies
uv sync --extra api

# Start API server
uvicorn BDNewsPaper.api:app --reload

# Custom host/port
uvicorn BDNewsPaper.api:app --host 0.0.0.0 --port 8000
```

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/articles` | List articles with pagination (`?limit=20&offset=0`) |
| `GET` | `/articles/{id}` | Get article by ID |
| `GET` | `/articles/search?q=keyword` | Full-text search |
| `GET` | `/newspapers` | List all newspapers with counts |
| `GET` | `/stats` | Database statistics |
| `GET` | `/health` | Health check |

**Example Requests:**
```bash
# Get latest 10 articles
curl http://localhost:8000/articles?limit=10

# Search articles
curl "http://localhost:8000/articles/search?q=cricket"

# Get stats
curl http://localhost:8000/stats
```

### GraphQL API

```bash
# Install GraphQL dependencies
uv sync --extra graphql

# Start GraphQL server
uvicorn BDNewsPaper.graphql_api:app --reload
```

**GraphQL Playground:** http://localhost:8000/graphql

### Full-Text Search

```bash
# Search articles via CLI
python -m BDNewsPaper.search --query "Bangladesh economy"
python -m BDNewsPaper.search --query "cricket" --limit 50
```

### Elasticsearch Search

For advanced search capabilities with relevance scoring, fuzzy matching, and faceted search.

#### Setup

```bash
# Start Elasticsearch (via Docker)
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0

# Install Python client
pip install elasticsearch
```

#### Usage

```bash
# Create index and import articles
python elasticsearch_search.py --index

# Search articles
python elasticsearch_search.py --search "Bangladesh election"

# Search with filters
python elasticsearch_search.py --search "cricket" --paper "Prothom Alo"

# Get autocomplete suggestions
python elasticsearch_search.py --suggest "bangla"

# Show facets (newspapers, categories)
python elasticsearch_search.py --facets

# Get index statistics
python elasticsearch_search.py --stats
```

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_HOST` | `http://localhost:9200` | Elasticsearch server URL |
| `ES_INDEX` | `bdnews_articles` | Index name |

### Redis Caching

Add caching layer to API for faster response times.

#### Setup

```bash
# Start Redis (via Docker)
docker run -d --name redis -p 6379:6379 redis:alpine

# Install Python client
pip install redis
```

#### Usage

Redis caching is integrated with the FastAPI application. Set the environment variable to enable:

```bash
# Set Redis URL
export REDIS_URL="redis://localhost:6379/0"

# Start API with caching enabled
uvicorn BDNewsPaper.api:app --reload
```

#### Cache Configuration

| Cache Type | TTL | Description |
|------------|-----|-------------|
| `articles_list` | 5 min | Article list endpoints |
| `article_detail` | 1 hour | Individual article pages |
| `stats` | 10 min | Database statistics |
| `search` | 5 min | Search results |
| `papers` | 1 hour | Newspaper list |

### RSS Feed Generator

```bash
# Generate all feeds
python rss_feed.py --all

# Generate for specific newspaper
python rss_feed.py --paper "Prothom Alo"

# Generate for last 7 days only
python rss_feed.py --days 7

# Serve feeds via HTTP server
python rss_feed.py --serve --port 8080
```

**Feed URLs (after generation):**
- `feeds/all.xml` - All newspapers combined
- `feeds/prothom_alo.xml` - Prothom Alo only
- `feeds/index.html` - Feed directory

---

## 🤖 Bot Integrations

### Telegram Bot

```bash
# Setup environment variables
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Send today's summary
python telegram_bot.py

# Send last 7 days summary
python telegram_bot.py --days 7

# Send specific newspaper summary
python telegram_bot.py --paper "Prothom Alo"

# Run as scheduled service (every 24 hours)
python telegram_bot.py --schedule --interval 24

# Test without sending
python telegram_bot.py --test
```

### Slack Bot

```bash
# Setup
export SLACK_WEBHOOK_URL="your-webhook-url"

# Send alerts
python slack_bot.py --send

# Send daily digest
python slack_bot.py --digest
```

### Discord Bot

```bash
# Setup
export DISCORD_WEBHOOK_URL="your-webhook-url"

# Send news embeds
python discord_bot.py --send
```

### Webhook Alerts

```bash
# Interactive setup
python alerts.py --setup

# Set alert keywords
python alerts.py --keywords "politics,cricket,breaking,election"

# Start monitoring for breaking news
python alerts.py --monitor

# Test alert
python alerts.py --test

# Check alert status
python alerts.py --status
```

### Webhooks for New Articles

Push notifications when new articles are scraped.

```bash
# Add a webhook endpoint
python webhooks.py --add-webhook "https://discord.com/api/webhooks/..." --type discord

# Add a Slack webhook
python webhooks.py --add-webhook "https://hooks.slack.com/..." --type slack

# Add keyword filter
python webhooks.py --add-keyword "breaking"

# Monitor for new articles and push to webhooks
python webhooks.py --monitor

# Set monitoring interval (seconds)
python webhooks.py --monitor --interval 60

# Test webhook with sample data
python webhooks.py --test

# Show current webhook configuration
python webhooks.py --status
```

**Webhook Types:**
- `discord` - Discord embed formatting
- `slack` - Slack block formatting
- `generic` - JSON payload to any endpoint

### Email Reports

```bash
# Send daily email report
python email_reports.py --send

# Generate HTML report
python email_reports.py --generate --output report.html
```

---

## ☁️ Cloud & Storage

### AWS S3 / DigitalOcean Spaces

```bash
# Setup environment
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export S3_BUCKET="your-bucket-name"
export S3_ENDPOINT="https://nyc3.digitaloceanspaces.com"  # For DO Spaces

# Backup database
python s3_storage.py --backup

# Sync data
python s3_storage.py --sync

# Download backup
python s3_storage.py --download
```

### Kaggle Dataset

```bash
# Setup: Place kaggle.json in ~/.kaggle/

# Upload to Kaggle
python kaggle_upload.py --upload

# Update existing dataset
python kaggle_upload.py --update
```

### Hugging Face Hub

```bash
# Setup
export HF_TOKEN="your-huggingface-token"

# Upload dataset
python huggingface_upload.py --upload

# Upload with custom repo name
python huggingface_upload.py --upload --repo "username/bd-news-dataset"
```

### Archive.org (Wayback Machine)

Archive news articles to Wayback Machine for permanent preservation.

```bash
# Archive recent articles (last 24 hours, max 50)
python archive_org.py --archive-recent

# Archive articles from last N days
python archive_org.py --archive-recent --days 7

# Archive more articles per run
python archive_org.py --archive-recent --limit 100

# Check if URLs are already archived
python archive_org.py --check

# Verify archived URLs are accessible
python archive_org.py --verify

# Show archive statistics
python archive_org.py --stats
```

**Rate Limits:**
- 5 seconds between requests (Wayback Machine limit)
- ~50 URLs per run recommended
- Archived URLs logged to `archive_log.json`

---

## 🏗️ Deployment

### Docker

```bash
# Build image
docker build -t bdnewspaper-scraper .

# Run single spider
docker run -d --name scraper \
  -v $(pwd)/news_articles.db:/app/news_articles.db \
  bdnewspaper-scraper scrapy crawl prothomalo

# Docker Compose (full stack with PostgreSQL, Redis, Prometheus)
docker-compose up -d

# View logs
docker-compose logs -f scraper
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -f kubernetes.yml

# Or use k8s directory
kubectl apply -f k8s/

# Check pods
kubectl get pods -l app=bdnewspaper-scraper
```

### GitHub Actions

Pre-configured workflows included:

- **CI Pipeline** (`ci.yml`): Runs on push/PR with linting and tests
- **Daily Scraper** (`daily-scrape.yml`): Runs daily at 6 AM UTC, scrapes top spiders

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `news_articles.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `scrapy.log` | Log file path |
| `MAX_PAGES` | `100` | Maximum pages per spider |
| `DOWNLOAD_DELAY` | `0.5` | Delay between requests (seconds) |
| `CONCURRENT_REQUESTS` | `64` | Maximum concurrent requests |
| `DATE_FILTER_ENABLED` | `false` | Enable date filtering by default |
| `FILTER_START_DATE` | - | Default start date (YYYY-MM-DD) |
| `FILTER_END_DATE` | - | Default end date (YYYY-MM-DD) |
| `LANGUAGE_DETECTION_ENABLED` | `true` | Enable language detection |
| `MIN_ARTICLE_WORDS` | `20` | Minimum words for valid article |
| `MAX_ARTICLE_WORDS` | `50000` | Maximum words per article |
| `CHECKPOINT_ENABLED` | `false` | Enable checkpointing for resume |
| `CHECKPOINT_INTERVAL` | `100` | Articles between checkpoints |
| `RETRY_TIMES` | `3` | Number of retries for failed requests |

### Scrapy Settings

Edit `BDNewsPaper/settings.py` or pass via command line:

| Setting | Default | Description |
|---------|---------|-------------|
| `CONCURRENT_REQUESTS` | 16 | Maximum concurrent requests |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | 8 | Max requests per domain |
| `DOWNLOAD_DELAY` | 0 | Delay between requests (seconds) |
| `CLOSESPIDER_ITEMCOUNT` | None | Stop after N items |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `AUTOTHROTTLE_ENABLED` | True | Enable adaptive throttling |
| `AUTOTHROTTLE_START_DELAY` | 0.5 | Initial download delay |
| `AUTOTHROTTLE_MAX_DELAY` | 10 | Maximum download delay |
| `RETRY_TIMES` | 3 | Number of retries |
| `RETRY_HTTP_CODES` | [500,502,503,504,408] | HTTP codes to retry |

### Proxy Support

```bash
# Enable proxy via command line
uv run scrapy crawl prothomalo -s PROXY_ENABLED=true

# Use proxy list file
cp proxies.txt.sample proxies.txt
# Edit proxies.txt with your proxies (one per line)
# Format: http://user:pass@host:port or http://host:port
```

---

## 📁 Project Structure

```
BDNewsPaperScraper/
├── BDNewsPaper/                     # Core Scrapy project
│   ├── spiders/                     # 74 spider implementations
│   │   ├── base_spider.py           # Base class with shared functionality
│   │   ├── prothomalo.py            # ProthomAlo (API-based)
│   │   ├── dailysun.py              # Daily Sun (AJAX API)
│   │   ├── thedailystar.py          # The Daily Star
│   │   ├── playwright_spider.py     # Cloudflare bypass (browser)
│   │   └── ...                      # 70+ more spiders
│   ├── api.py                       # REST API (FastAPI)
│   ├── graphql_api.py               # GraphQL API
│   ├── cli.py                       # CLI interface
│   ├── search.py                    # Full-text search (FTS5)
│   ├── config.py                    # Configuration management
│   ├── items.py                     # Data models
│   ├── pipelines.py                 # Data pipelines
│   ├── middlewares.py               # Custom middlewares
│   ├── proxy.py                     # Proxy rotation
│   └── settings.py                  # Scrapy settings
│
├── chrome_extension/                # Browser extension for clipping
├── k8s/                             # Kubernetes manifests
├── tests/                           # Test suite
├── data/                            # Scraped data exports
│
├── app.py                           # Main Streamlit GUI
├── dashboard.py                     # Basic dashboard
├── dashboard_enhanced.py            # Enhanced dashboard
├── analytics.py                     # Sentiment & trend analysis
├── topic_clustering.py              # ML topic clustering
├── breaking_news.py                 # Breaking news detection
├── news_timeline.py                 # Timeline visualization
│
├── telegram_bot.py                  # Telegram notifications
├── slack_bot.py                     # Slack notifications
├── discord_bot.py                   # Discord notifications
├── alerts.py                        # Webhook alerts
├── email_reports.py                 # Email report generator
├── rss_feed.py                      # RSS feed generator
│
├── s3_storage.py                    # AWS S3 backup
├── kaggle_upload.py                 # Kaggle dataset upload
├── huggingface_upload.py            # Hugging Face upload
│
├── toxlsx.py                        # Excel/CSV export tool
├── status_page.py                   # Spider health monitoring
├── performance_monitor.py           # Performance metrics
├── run_spiders_optimized.py         # Batch runner (cross-platform)
├── run_spiders_optimized.sh         # Batch runner (Linux/macOS)
│
├── docker-compose.yml               # Docker Compose config
├── Dockerfile                       # Docker image
├── kubernetes.yml                   # Kubernetes deployment
├── prometheus.yml                   # Prometheus config
│
├── pyproject.toml                   # Project configuration
├── .env.example                     # Environment template
├── DOCS.md                          # Additional documentation
└── news_articles.db                 # SQLite database (generated)
```

---

## 🔄 Automation

### Cron (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Run all spiders daily at 2 AM
0 2 * * * cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh --monitor >> /var/log/scraper.log 2>&1

# Run specific spider every 6 hours
0 */6 * * * cd /path/to/BDNewsPaperScraper && uv run scrapy crawl prothomalo -a start_date=$(date -d "yesterday" +\%Y-\%m-\%d) >> /var/log/prothomalo.log 2>&1

# Daily export at 6 AM
0 6 * * * cd /path/to/BDNewsPaperScraper && python toxlsx.py --output /path/to/exports/news_$(date +\%Y\%m\%d).xlsx
```

### Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, hourly, etc.)
4. Action: Start a program
   - Program: `python`
   - Arguments: `run_spiders_optimized.py --monitor`
   - Start in: `C:\path\to\BDNewsPaperScraper`

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: uv` | Install UV: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ModuleNotFoundError` | Run `uv sync` to install dependencies |
| `No articles scraped` | Check internet; try `-L DEBUG` for details |
| `Database locked` | Stop running spiders; wait a few seconds |
| `Spider not found` | Run `uv run scrapy list` to see available spiders |
| `Cloudflare blocked (403)` | Use `playwright_spider.py` or add delays |
| `Too many requests (429)` | Increase `DOWNLOAD_DELAY`, reduce `CONCURRENT_REQUESTS` |
| `Connection timeout` | Check internet; increase `RETRY_TIMES` |
| `Invalid date format` | Use `YYYY-MM-DD` format (e.g., `2024-12-25`) |

### Debug Commands

```bash
# Check installation
uv --version
uv run scrapy version

# List available spiders
uv run scrapy list

# Test single article with debug
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=1 -L DEBUG

# Check spider settings
uv run scrapy settings --get CONCURRENT_REQUESTS

# View logs
tail -f scrapy.log

# Check database
sqlite3 news_articles.db ".tables"
sqlite3 news_articles.db "SELECT COUNT(*) FROM articles;"
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Install dev dependencies: `uv sync --extra dev`
4. Make changes following existing patterns
5. Run tests: `uv run pytest`
6. Format code: `uv run black . && uv run isort .`
7. Lint: `uv run flake8`
8. Submit a pull request

### Adding a New Spider

1. Create spider file in `BDNewsPaper/spiders/`
2. Extend `BaseNewsSpider` from `base_spider.py`
3. Define `name`, `paper_name`, `allowed_domains`
4. Implement `start_requests()` and parsing methods
5. Use `create_article_item()` for consistent output
6. Add spider details to `config.py`
7. Test: `uv run scrapy crawl yourspider -s CLOSESPIDER_ITEMCOUNT=5`
8. Update this README and `todo.md`

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ for Bangladeshi news data collection**

[⬆ Back to Top](#️-bd-newspaper-scraper)

</div>
## 📁 Project Structure

```bash
BDNewsPaperScraper/
├── BDNewsPaper/           # Scrapy project core
│   ├── spiders/          # Spider definitions
│   ├── pipelines.py      # Data pipelines
│   └── settings.py       # Scrapy settings
├── config/               # Configuration files
├── docs/                 # Documentation
├── scripts/              # Helper scripts and bots
│   ├── analytics.py
│   ├── dashboard.py
│   └── performance_monitor.py
├── news_articles.db      # SQLite database (auto-generated)
├── run_spiders_optimized.py # Main entry point
├── app.py                # Streamlit Dashboard
└── requirements.txt      # Dependencies
```
