# 📚 BD Newspaper Scraper - Documentation

Complete documentation for all tools and features.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Spider Usage](#spider-usage)
3. [API Reference](#api-reference)
4. [Dashboard](#dashboard)
5. [RSS Feeds](#rss-feeds)
6. [Telegram Bot](#telegram-bot)
7. [Analytics](#analytics)
8. [Webhook Alerts](#webhook-alerts)
9. [Status Page](#status-page)

---

## Quick Start

```bash
# Install
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper
pip install -e .

# Run a spider
scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10

# Launch dashboard
pip install -e ".[dashboard]"
streamlit run dashboard.py
```

---

## Spider Usage

### Basic Commands

```bash
# Run specific spider
scrapy crawl prothomalo

# Limit articles
scrapy crawl dailysun -s CLOSESPIDER_ITEMCOUNT=100

# Date range
scrapy crawl thedailystar -a start_date=2024-01-01 -a end_date=2024-01-31

# Category filter
scrapy crawl bdnews24 -a categories=bangladesh,politics

# Search
scrapy crawl prothomalo -a search_query="cricket"
```

### Available Spiders (74)

| Type | Count | Examples |
|------|-------|----------|
| English | 22 | prothomalo, thedailystar, bdnews24, dhakatribune |
| Bangla | 52 | jugantor, samakal, dhakapost, risingbd |
| API-based | 15 | prothomalo, dailysun, jugantor, tbsnews |
| HTML-based | 59 | dhakatribune, banglatribune, jagonews24 |

---

## API Reference

### REST API

```bash
# Start API server
pip install -e ".[api]"
uvicorn BDNewsPaper.api:app --reload

# Endpoints
GET /articles                    # List articles
GET /articles/{id}               # Get article
GET /articles/search?q=keyword   # Search
GET /newspapers                  # List newspapers
GET /stats                       # Statistics
```

### GraphQL API

```bash
# Start GraphQL server
pip install -e ".[graphql]"
uvicorn BDNewsPaper.graphql_api:app --reload

# GraphQL Playground: http://localhost:8000/graphql
```

---

## Dashboard

Interactive Streamlit dashboard for visualizing news data.

```bash
# Install
pip install -e ".[dashboard]"

# Run
streamlit run dashboard.py
```

### Features
- 📊 Article statistics and charts
- 📈 Daily trend analysis
- ☁️ Word cloud from headlines
- 🔥 Trending keywords
- 🔍 Search functionality
- 📰 Latest headlines viewer

---

## RSS Feeds

Generate RSS feeds from scraped articles.

```bash
# Generate all feeds
python rss_feed.py --all

# Specific newspaper
python rss_feed.py --paper "Prothom Alo"

# Last 7 days only
python rss_feed.py --days 7

# Serve feeds via HTTP
python rss_feed.py --serve --port 8080
```

### Feed URLs
- `feeds/all.xml` - All newspapers combined
- `feeds/prothom_alo.xml` - Prothom Alo only
- `feeds/index.html` - Feed directory

---

## Telegram Bot

Send daily news summaries to Telegram.

### Setup

```bash
# 1. Create bot via @BotFather
# 2. Get chat ID via @userinfobot
# 3. Set environment variables
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### Usage

```bash
# Send today's summary
python telegram_bot.py

# Last 7 days
python telegram_bot.py --days 7

# Specific paper
python telegram_bot.py --paper "Prothom Alo"

# Run as scheduled service
python telegram_bot.py --schedule --interval 24

# Test without sending
python telegram_bot.py --test
```

---

## Analytics

Sentiment analysis, entity extraction, and trend analysis.

```bash
# Install dependencies
pip install -e ".[analytics]"

# Generate full report
python analytics.py --report

# Sentiment analysis
python analytics.py --sentiment

# Extract entities
python analytics.py --entities

# Trending keywords
python analytics.py --trends

# Find duplicates
python analytics.py --duplicates
```

### Features
- 😊 Sentiment analysis (positive/negative/neutral)
- 👤 Entity extraction (people, organizations)
- 🔥 Trending keyword analysis
- 🔄 Duplicate article detection
- 📊 Automated report generation

---

## Webhook Alerts

Get notified about breaking news via Discord/Slack.

### Setup

```bash
# Interactive setup
python alerts.py --setup

# Or set keywords directly
python alerts.py --keywords "politics,cricket,breaking"
```

### Usage

```bash
# Start monitoring
python alerts.py --monitor

# Test alert
python alerts.py --test

# Check status
python alerts.py --status
```

### Supported Webhooks
- Discord
- Slack
- Generic HTTP

---

## Status Page

Monitor spider health and generate status reports.

```bash
# Generate status page
python status_page.py

# Test all spiders
python status_page.py --test

# Export as JSON
python status_page.py --json

# Serve status page
python status_page.py --serve --port 8081
```

### Status Page URL
- `status/index.html` - HTML status page
- `status/status.json` - JSON API

---

## GitHub Actions

### CI Pipeline (`ci.yml`)
- Runs on push/PR
- Linting and tests
- Docker build

### Daily Scraper (`daily-scrape.yml`)
- Runs daily at 6 AM UTC
- Scrapes top 20 spiders
- Commits data to repo
- Exports JSON + PostgreSQL SQL

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | For bot |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | For bot |
| `DATABASE_URL` | PostgreSQL URL | For postgres |
| `LOG_LEVEL` | Logging level | No (default: INFO) |

---

## Project Structure

```
BDNewsPaperScraper/
├── BDNewsPaper/           # Core Scrapy project
│   ├── spiders/           # 75+ spider implementations
│   ├── api.py             # REST API
│   ├── graphql_api.py     # GraphQL API
│   └── pipelines.py       # Data pipelines
├── dashboard.py           # Streamlit dashboard
├── rss_feed.py           # RSS feed generator
├── telegram_bot.py       # Telegram notifications
├── analytics.py          # Sentiment & trends
├── alerts.py             # Webhook alerts
├── status_page.py        # Health monitoring
├── data/                 # Scraped data (daily)
├── feeds/                # RSS feeds
├── status/               # Status page
└── reports/              # Analytics reports
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
