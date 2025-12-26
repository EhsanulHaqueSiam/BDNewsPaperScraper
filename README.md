# 🗞️ BD Newspaper Scraper

A high-performance web scraper for Bangladeshi newspapers built with [Scrapy](https://scrapy.org/). Collects English news articles from major Bangladeshi news sources and stores them in a SQLite database.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![Scrapy](https://img.shields.io/badge/Scrapy-2.12+-green?logo=scrapy&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-GUI-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

## ✨ Features

- **65 Active Spiders** — Scrape from 21 English + 44 Bangla newspapers with API-based scrapers for optimal speed
- **Web GUI** — User-friendly Streamlit interface for controlling scrapers and browsing articles
- **Date Range Filtering** — Scrape articles from specific time periods
- **Unified Database** — All articles stored in a single SQLite database with duplicate prevention
- **High Performance** — Optimized concurrent requests with smart throttling
- **Cross-Platform** — Full support for Linux, macOS, and Windows
- **Export Tools** — Export to Excel/CSV with filtering options

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **UV Package Manager** — [Install UV](https://docs.astral.sh/uv/getting-started/installation/)

### Installation

```bash
# Clone repository
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper

# Install dependencies
uv sync

# Verify installation
uv run scrapy list
```

### Run Your First Scrape

```bash
# Quick test (10 articles)
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10

# Full scrape with monitoring
./run_spiders_optimized.sh prothomalo --monitor        # Linux/macOS
python run_spiders_optimized.py prothomalo --monitor   # Windows/All platforms

# Check results
python toxlsx.py --list
```

### 🖥️ Launch Web GUI (Optional)

```bash
# Install GUI dependencies
uv sync --extra gui

# Launch Streamlit interface
uv run streamlit run app.py
```

Open http://localhost:8501 in your browser to access the GUI.

---

## 📰 Available Spiders

### English Newspapers (20)

| Spider | Command | Source | Method | Speed |
|--------|---------|--------|--------|-------|
| `prothomalo` | `scrapy crawl prothomalo` | [ProthomAlo](https://en.prothomalo.com/) | API-based | ⚡ Fast |
| `thedailystar` | `scrapy crawl thedailystar` | [The Daily Star](https://www.thedailystar.net/) | API | ⚡ Fast |
| `dailysun` | `scrapy crawl dailysun` | [Daily Sun](https://www.daily-sun.com/) | API | ⚡ Fast |
| `tbsnews` | `scrapy crawl tbsnews` | [TBS News](https://www.tbsnews.net/) | Drupal AJAX | ⚡ Fast |
| `unb` | `scrapy crawl unb` | [UNB](https://unb.com.bd/) | API | ⚡ Fast |
| `bssnews` | `scrapy crawl bssnews` | [BSS News](https://www.bssnews.net/) | HTML | 🔄 Medium |
| `ittefaq` | `scrapy crawl ittefaq` | [Daily Ittefaq](https://en.ittefaq.com.bd/) | API | 🔄 Medium |
| `dhakatribune` | `scrapy crawl dhakatribune` | [Dhaka Tribune](https://www.dhakatribune.com/) | HTML | 🔄 Medium |
| `financialexpress` | `scrapy crawl financialexpress` | [Financial Express](https://thefinancialexpress.com.bd/) | HTML | 🔄 Medium |
| `newage` | `scrapy crawl newage` | [New Age](https://www.newagebd.net/) | HTML | 🔄 Medium |
| `bdnews24` | `scrapy crawl bdnews24` | [bdnews24](https://bdnews24.com/) | HTML | 🔄 Medium |
| `BDpratidin` | `scrapy crawl BDpratidin` | [BD Pratidin](https://en.bd-pratidin.com/) | HTML | 🔄 Medium |
| `bangladesh_today` | `scrapy crawl bangladesh_today` | [Bangladesh Today](https://thebangladeshtoday.com/) | HTML | 🔄 Medium |
| `theindependent` | `scrapy crawl theindependent` | [The Independent](https://theindependentbd.com/) | RSS | 🔄 Medium |
| `observerbd` | `scrapy crawl observerbd` | [Observer BD](https://observerbd.com/) | HTML | 🔄 Medium |
| `bangladeshpost` | `scrapy crawl bangladeshpost` | [Bangladesh Post](https://bangladeshpost.net/) | HTML | 🔄 Medium |
| `dailyasianage` | `scrapy crawl dailyasianage` | [Asian Age](https://dailyasianage.com/) | HTML | 🔄 Medium |
| `dhakacourier` | `scrapy crawl dhakacourier` | [Dhaka Courier](https://dhakacourier.com.bd/) | HTML | 🔄 Medium |
| `bd24live` | `scrapy crawl bd24live` | [BD24Live](https://bd24live.com/) | HTML | 🔄 Medium |
| `ntvbd` | `scrapy crawl ntvbd` | [NTV BD](https://en.ntvbd.com/) | HTML | 🔄 Medium |

### Bangla Newspapers (34)

| Spider | Command | Source | Method | Speed |
|--------|---------|--------|--------|-------|
| `jugantor` | `scrapy crawl jugantor` | [Jugantor](https://www.jugantor.com/) | **JSON API** | ⚡ Fast |
| `banglatribune` | `scrapy crawl banglatribune` | [Bangla Tribune](https://www.banglatribune.com/) | HTML | 🔄 Medium |
| `samakal` | `scrapy crawl samakal` | [Samakal](https://samakal.com/) | HTML | 🔄 Medium |
| `jagonews24` | `scrapy crawl jagonews24` | [Jago News 24](https://www.jagonews24.com/) | HTML | 🔄 Medium |
| `risingbd` | `scrapy crawl risingbd` | [Rising BD](https://www.risingbd.com/) | HTML | 🔄 Medium |
| `bdnews24_bangla` | `scrapy crawl bdnews24_bangla` | [bdnews24 Bangla](https://bangla.bdnews24.com/) | HTML | 🔄 Medium |
| `nayadiganta` | `scrapy crawl nayadiganta` | [Naya Diganta](https://dailynayadiganta.com/) | HTML | 🔄 Medium |
| `bdpratidin_bangla` | `scrapy crawl bdpratidin_bangla` | [BD Pratidin](https://www.bd-pratidin.com/) | HTML | 🔄 Medium |
| `manabzamin` | `scrapy crawl manabzamin` | [Manab Zamin](https://www.mzamin.com/) | HTML | 🔄 Medium |
| `bonikbarta` | `scrapy crawl bonikbarta` | [Bonik Barta](https://www.bonikbarta.net/) | HTML | 🔄 Medium |
| `deshrupantor` | `scrapy crawl deshrupantor` | [Desh Rupantor](https://www.deshrupantor.com/) | HTML | 🔄 Medium |
| `janakantha` | `scrapy crawl janakantha` | [Janakantha](https://www.dailyjanakantha.com/) | HTML | 🔄 Medium |
| `bhorerkagoj` | `scrapy crawl bhorerkagoj` | [Bhorer Kagoj](https://bhorerkagoj.com/) | HTML | 🔄 Medium |
| `dailyinqilab` | `scrapy crawl dailyinqilab` | [Daily Inqilab](https://dailyinqilab.com/) | HTML | 🔄 Medium |
| `sangbad` | `scrapy crawl sangbad` | [Sangbad](https://sangbad.net.bd/) | HTML | 🔄 Medium |
| `ntvbd_bangla` | `scrapy crawl ntvbd_bangla` | [NTV Bangla](https://www.ntvbd.com/) | HTML | 🔄 Medium |
| `alokitobangladesh` | `scrapy crawl alokitobangladesh` | [Alokito Bangladesh](https://alokitobangladesh.com/) | HTML | 🔄 Medium |
| `dainikbangla` | `scrapy crawl dainikbangla` | [Dainik Bangla](https://dainikbangla.com.bd/) | HTML | 🔄 Medium |
| `dhakapost` | `scrapy crawl dhakapost` | [Dhaka Post](https://dhakapost.com/) | HTML | 🔄 Medium |
| `sarabangla` | `scrapy crawl sarabangla` | [Sara Bangla](https://sarabangla.net/) | HTML | 🔄 Medium |
| `rtvonline` | `scrapy crawl rtvonline` | [RTV Online](https://rtvonline.com/) | HTML | 🔄 Medium |
| `ekattor` | `scrapy crawl ekattor` | [Ekattor TV](https://ekattor.tv/) | HTML | 🔄 Medium |
| `news24bd` | `scrapy crawl news24bd` | [News24 BD](https://news24bd.tv/) | HTML | 🔄 Medium |
| `channeli` | `scrapy crawl channeli` | [Channel I](https://channelionline.com/) | HTML | 🔄 Medium |
| `banglavision` | `scrapy crawl banglavision` | [Bangla Vision](https://banglavision.tv/) | HTML | 🔄 Medium |
| `maasranga` | `scrapy crawl maasranga` | [Maasranga TV](https://maasranga.tv/) | **WP API** | ⚡ Fast |
| `dbcnews` | `scrapy crawl dbcnews` | [DBC News](https://dbcnews.tv/) | HTML | 🔄 Medium |
| `itvbd` | `scrapy crawl itvbd` | [ITV BD](https://itvbd.com/) | HTML | 🔄 Medium |

> ⚠️ **Note**: Kaler Kantho is Cloudflare protected. Spider file is disabled (`kalerkantho.py.disabled`).

---

## 🛠️ Usage

### Basic Commands

```bash
# Run a specific spider
uv run scrapy crawl prothomalo

# Limit number of articles
uv run scrapy crawl dailysun -s CLOSESPIDER_ITEMCOUNT=100

# Add delay between requests
uv run scrapy crawl ittefaq -s DOWNLOAD_DELAY=2

# Increase verbosity
uv run scrapy crawl BDpratidin -L DEBUG
```

### Date Range Filtering

All spiders support date filtering in `YYYY-MM-DD` format:

```bash
# Scrape January 2024
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31

# From specific date to today
uv run scrapy crawl dailysun -a start_date=2024-08-01

# Combine with item limit
uv run scrapy crawl thedailystar -a start_date=2024-06-01 -a end_date=2024-06-30 -s CLOSESPIDER_ITEMCOUNT=500
```

### Category Filtering

All spiders support category filtering. Available categories per spider:

```bash
# ProthomAlo: Bangladesh, Politics, Sports, Business, Opinion, Entertainment, Youth, World, Environment, Science & Tech
uv run scrapy crawl prothomalo -a categories=Bangladesh,Sports

# Daily Sun: Bangladesh, Business, World, Entertainment, Sports, Lifestyle, Tech, Opinion
uv run scrapy crawl dailysun -a categories=Bangladesh,Sports

# Ittefaq: Bangladesh, International, Sports, Business, Entertainment, Opinion
uv run scrapy crawl ittefaq -a categories=Bangladesh,Sports

# BD Pratidin: national, international, sports, showbiz, economy, shuvosangho
uv run scrapy crawl BDpratidin -a categories=national,sports

# Bangladesh Today: Bangladesh (1), Nationwide (93), Entertainment (94), International (97), Sports (95)
uv run scrapy crawl bangladesh_today -a categories=Bangladesh,Sports

# The Daily Star: Bangladesh, Politics, World, Business, Sports, Opinion, Entertainment, Tech
uv run scrapy crawl thedailystar -a categories=Bangladesh,Sports
```

### Keyword Search

Some spiders support keyword search:

```bash
# Search in ProthomAlo
uv run scrapy crawl prothomalo -a search_query="Bangladesh politics"

# Search in Daily Sun
uv run scrapy crawl dailysun -a search_query="cricket"

# Search in Ittefaq
uv run scrapy crawl ittefaq -a search_query="economy"
```

### Batch Running (Recommended for Production)

```bash
# Linux/macOS
./run_spiders_optimized.sh                # Run all spiders
./run_spiders_optimized.sh prothomalo     # Run specific spider
./run_spiders_optimized.sh --monitor      # Run with performance monitoring
./run_spiders_optimized.sh --start-date 2024-01-01 --end-date 2024-01-31

# Windows / Cross-platform
python run_spiders_optimized.py
python run_spiders_optimized.py prothomalo --monitor
python run_spiders_optimized.py --start-date 2024-01-01 --end-date 2024-01-31
```

---

## 💾 Data Export

### View Database Summary

```bash
python toxlsx.py --list
```

### Export to Excel/CSV

```bash
# Export all articles to Excel
python toxlsx.py --output all_news.xlsx

# Export specific newspaper
python toxlsx.py --paper "ProthomAlo" --output prothomalo.xlsx

# Export as CSV
python toxlsx.py --format csv --output news_data.csv

# Export with limit
python toxlsx.py --limit 100 --output recent_news.xlsx
```

### Direct Database Queries

```bash
# Count articles by newspaper
sqlite3 news_articles.db "SELECT paper_name, COUNT(*) FROM articles GROUP BY paper_name;"

# View recent headlines
sqlite3 news_articles.db "SELECT headline, paper_name FROM articles ORDER BY scraped_at DESC LIMIT 10;"

# Export to CSV
sqlite3 -header -csv news_articles.db "SELECT * FROM articles LIMIT 100;" > export.csv
```

---

## 🗄️ Database Schema

All articles are stored in a single `news_articles.db` SQLite database:

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
```

---

## 📁 Project Structure

```
BDNewsPaperScraper/
├── BDNewsPaper/                     # Main Scrapy project
│   ├── spiders/                     # Spider implementations
│   │   ├── base_spider.py          # Base class with shared functionality
│   │   ├── prothomalo.py           # ProthomAlo (API-based)
│   │   ├── dailysun.py             # Daily Sun (AJAX API)
│   │   ├── ittefaq.py              # Daily Ittefaq (AJAX API)
│   │   ├── bdpratidin.py           # BD Pratidin (HTML)
│   │   ├── thebangladeshtoday.py   # Bangladesh Today (HTML + Bengali dates)
│   │   ├── thedailystar.py         # The Daily Star (HTML + RSS)
│   │   └── kalerkantho.py.disabled # Discontinued
│   ├── items.py                    # Data models
│   ├── pipelines.py                # Storage pipelines
│   ├── middlewares.py              # Custom middlewares
│   ├── config.py                   # Configuration
│   ├── cli.py                      # CLI interface
│   ├── bengalidate_to_englishdate.py  # Bengali date converter
│   └── settings.py                 # Scrapy settings
├── run_spiders_optimized.sh        # Batch runner (Linux/macOS)
├── run_spiders_optimized.py        # Batch runner (Cross-platform)
├── run_spiders_optimized.bat       # Batch runner (Windows wrapper)
├── toxlsx.py                       # Export tool
├── performance_monitor.py          # Performance monitoring
├── setup.sh                        # Setup script
├── pyproject.toml                  # Project configuration
└── news_articles.db                # SQLite database (generated)
```

---

## ⚙️ Configuration

### Performance Tuning

```bash
# High-speed scraping (be respectful to servers)
uv run scrapy crawl prothomalo -s CONCURRENT_REQUESTS=32 -s DOWNLOAD_DELAY=0.5

# Conservative scraping
uv run scrapy crawl dailysun -s CONCURRENT_REQUESTS=4 -s DOWNLOAD_DELAY=2
```

### Key Settings

Edit `BDNewsPaper/settings.py` or pass via command line:

| Setting | Default | Description |
|---------|---------|-------------|
| `CONCURRENT_REQUESTS` | 16 | Maximum concurrent requests |
| `DOWNLOAD_DELAY` | 0 | Delay between requests (seconds) |
| `CLOSESPIDER_ITEMCOUNT` | None | Stop after N items |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

---

## 🔄 Automation

### Cron (Linux/macOS)

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh --monitor >> /var/log/scraper.log 2>&1

# Run specific spider every 6 hours
0 */6 * * * cd /path/to/BDNewsPaperScraper && uv run scrapy crawl prothomalo >> /var/log/prothomalo.log 2>&1
```

### Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, hourly, etc.)
4. Action: `python run_spiders_optimized.py --monitor`
5. Set working directory to project folder

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: uv` | Install UV: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ModuleNotFoundError` | Run `uv sync` to install dependencies |
| `No articles scraped` | Check internet connection; try with `-L DEBUG` |
| `Database locked` | Stop running spiders; wait a few seconds |
| `Spider not found` | Run `uv run scrapy list` to see available spiders |
| `Windows: No output` | Use `-L INFO` flag or `python run_spiders_optimized.py --monitor` |

### Debug Commands

```bash
# Check installation
uv --version
uv run scrapy version

# List available spiders
uv run scrapy list

# Test single article
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=1 -L DEBUG

# View logs
tail -f scrapy.log
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Install dependencies: `uv sync`
4. Make changes following existing patterns
5. Test: `uv run scrapy crawl <spider> -s CLOSESPIDER_ITEMCOUNT=5`
6. Format code: `uv run black . && uv run isort .`
7. Submit a pull request

### Adding a New Spider

1. Create spider file in `BDNewsPaper/spiders/`
2. Extend `BaseNewsSpider` from `base_spider.py`
3. Implement `start_requests()` and parsing methods
4. Use `create_article_item()` for consistent output
5. Test with small item counts
6. Update this README

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>Made with ❤️ for Bangladeshi news data collection</strong>
</div>