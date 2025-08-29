# 🕷️ BDNewsPaper Scraper

**✅ Project Status: CLEANED & OPTIMIZED**

> **🧹 Recently Cleaned**: Removed unnecessary files, optimized project structure, and enhanced documentation for better performance and maintainability.

> **📰 August 2024 Update**: Kaler Kantho English version discontinued. Spider disabled (now `.disabled`). Only Bangla content remains at kalerkantho.com.

## 🚀 Quick Start (TL;DR)

### 🐧 Linux/macOS
```bash
# 1. Clone and setup
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper
chmod +x setup.sh && ./setup.sh --all

# 2. Test with fastest spider
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10

# 3. Run optimized batch (RECOMMENDED)
chmod +x run_spiders_optimized.sh
./run_spiders_optimized.sh prothomalo --monitor

# 4. Check results
./toxlsx.py --list

# 5. Export data
./toxlsx.py --output news_data.xlsx
```

### 🪟 Windows
```cmd
# 1. Clone and setup (Command Prompt or PowerShell)
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper
uv sync

# 2. Test with fastest spider
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10

# 3. Run optimized batch (RECOMMENDED) - Use Python script
python run_spiders_optimized.py prothomalo --monitor

# 4. Check results
python toxlsx.py --list

# 5. Export data
python toxlsx.py --output news_data.xlsx
```

### 🗓️ Date Filtering (All Platforms)
```bash
# All spiders support date filtering!
uv run scrapy crawl prothomalo -a start_date=2024-08-01 -a end_date=2024-08-31
python run_spiders_optimized.py --start-date 2024-08-01 --end-date 2024-08-31
```

## ✅ Prerequisites

- **Python 3.9+** - Modern Python support
- **UV Package Manager** - Ultra-fast dependency management
- **Git** - For cloning the repository

## ⚡ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper
```

### 2. Install UV (if not already installed)
```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell or restart terminal
source ~/.bashrc  # or ~/.zshrc for zsh
```

### 3. Setup Project

#### 🐧 Linux/macOS
```bash
# Automatic setup (recommended)
chmod +x setup.sh
./setup.sh --all

# OR Manual setup
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

#### 🪟 Windows (Command Prompt or PowerShell)
```cmd
# Install UV if not already installed (PowerShell - run as administrator)
# Option 1: Using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Option 2: Using Python pip
pip install uv

# Manual setup (recommended for Windows)
uv venv --python 3.11
.venv\Scripts\activate
uv sync

# OR if you have WSL (Windows Subsystem for Linux)
# Follow the Linux/macOS instructions in WSL
```

### 4. Verify Installation
```bash
# Check if spiders are available
uv run scrapy list

# Should show:
# BDpratidin
# bangladesh_today  
# dailysun
# ittefaq
# prothomalo
# thedailystar

# Test run a single spider to verify everything works
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=5
```

## 📋 Complete Summary: All Possible Ways to Run the Project

The BDNewsPaper scraper provides **16 different methods** to run the project, covering every possible use case:

### 🎯 **Quick Reference Table**

| Method | Use Case | Complexity | Best For |
|--------|----------|------------|----------|
| **Method 1**: Individual Commands | Development, Testing | ⭐ | Learning, debugging |
| **Method 2**: Enhanced Batch Runner | Production | ⭐⭐ | **RECOMMENDED** |
| **Method 3**: Selective Running | Targeted scraping | ⭐⭐ | Specific needs |
| **Method 4**: Development & Testing | Debug, development | ⭐⭐ | Development workflow |
| **Method 5**: Scheduled/Cron | Automation | ⭐⭐⭐ | Production automation |
| **Method 6**: Python Scripts | Custom automation | ⭐⭐⭐ | Custom workflows |
| **Method 7**: Container/Docker | Containerized | ⭐⭐⭐⭐ | Cloud deployment |
| **Method 8**: Virtual Environment | Direct execution | ⭐⭐ | Speed optimization |
| **Method 9**: IDE Integration | Development | ⭐⭐ | IDE users |
| **Method 10**: System Service | Background service | ⭐⭐⭐⭐ | Server deployment |
| **Method 11**: Environment-Specific | Multi-environment | ⭐⭐⭐ | Dev/staging/prod |
| **Method 12**: Multi-Instance Parallel | High performance | ⭐⭐⭐⭐⭐ | Maximum speed |
| **Method 13**: Makefile | Build automation | ⭐⭐⭐ | Build systems |
| **Method 14**: CI/CD Pipeline | Automated deployment | ⭐⭐⭐⭐⭐ | DevOps |
| **Method 15**: Remote/Cloud | Cloud execution | ⭐⭐⭐⭐ | Cloud platforms |
| **Method 16**: API/Webhook | Event-driven | ⭐⭐⭐⭐⭐ | Microservices |

### 🚀 **Most Popular Methods**

1. **🥇 Enhanced Batch Runner** (`./run_spiders_optimized.sh`)
   - Best performance, monitoring, logging
   - Recommended for 95% of users

2. **🥈 Individual Commands** (`uv run scrapy crawl spider`)
   - Perfect for development and testing
   - Most flexible for custom settings

3. **🥉 Scheduled Cron Jobs** (cron + optimized runner)
   - Ideal for automated daily/hourly runs
   - Production automation

### 🎯 **Choose Your Method Based On:**

**👨‍💻 For Developers:**
- Development: Method 1 (Individual Commands)
- Testing: Method 4 (Development & Testing)
- IDE Integration: Method 9

**🏭 For Production:**
- Standard: Method 2 (Enhanced Batch Runner)
- Automation: Method 5 (Scheduled/Cron)
- High Performance: Method 12 (Multi-Instance)

**☁️ For Cloud/Enterprise:**
- Containers: Method 7 (Docker)
- CI/CD: Method 14 (Pipeline)
- Microservices: Method 16 (API/Webhook)

**🛠️ For System Administrators:**
- Background Service: Method 10 (System Service)
- Remote Execution: Method 15 (Remote/Cloud)
- Build Systems: Method 13 (Makefile)

### ✨ **Special Combinations**

```bash
# ULTIMATE PERFORMANCE: Multi-instance + Monitoring + Cron
# Terminal 1-3 (parallel execution)
./run_spiders_optimized.sh prothomalo --monitor &
./run_spiders_optimized.sh dailysun --monitor &
./run_spiders_optimized.sh ittefaq --monitor &

# ULTIMATE AUTOMATION: Docker + CI/CD + Webhook
# Containerized, automated, event-driven execution

# ULTIMATE RELIABILITY: System Service + Monitoring
# Background service with performance tracking
```

## 🪟 Windows Support

This project now provides **full Windows support** with a cross-platform Python runner script (`run_spiders_optimized.py`) that provides all the same features as the Linux/macOS bash script.

### Windows Quick Start

1. **Install Prerequisites**
   ```cmd
   # Install Python 3.9+ from python.org
   # Install Git from git-scm.com
   # Install UV package manager (PowerShell as administrator):
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Clone and Setup**
   ```cmd
   git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
   cd BDNewsPaperScraper
   uv sync
   ```

3. **Test Run**
   ```cmd
   # Basic test (minimal output with UV)
   uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10
   
   # Better visibility (shows scraping progress)
   uv run scrapy crawl prothomalo -L INFO -s CLOSESPIDER_ITEMCOUNT=10
   ```

4. **Production Run** 
   ```cmd
   # Best option for Windows (full visibility)
   python run_spiders_optimized.py prothomalo --monitor
   ```

> **💡 Windows Tip**: If `uv run` shows only "Bytecode compiled" and no scraping info, use `-L INFO` flag or switch to the Python runner for better visibility!

### Windows-Specific Features

#### Enhanced Python Runner (`run_spiders_optimized.py`)
The Python script provides **identical functionality** to the bash script but works on Windows:

```cmd
# Cross-platform runner that works on Windows, macOS, and Linux
python run_spiders_optimized.py [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
```

#### Windows Usage Examples

```cmd
# Cross-platform runner that works on Windows, macOS, and Linux
python run_spiders_optimized.py [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

# OR use the Windows batch file for easier access
run_spiders_optimized.bat [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
```

**Python Script Examples:**
```cmd
# Run all spiders with optimized settings
python run_spiders_optimized.py

# Run specific spider
python run_spiders_optimized.py prothomalo
python run_spiders_optimized.py dailysun

# Run with performance monitoring
python run_spiders_optimized.py --monitor
python run_spiders_optimized.py prothomalo --monitor

# Date range filtering
python run_spiders_optimized.py --start-date 2024-01-01 --end-date 2024-01-31
python run_spiders_optimized.py prothomalo --start-date 2024-08-01 --end-date 2024-08-31

# Combined options
python run_spiders_optimized.py dailysun --monitor --start-date 2024-08-01

# Get help
python run_spiders_optimized.py --help
```

**Windows Batch File Examples:**
```cmd
# Easier syntax using the .bat wrapper
run_spiders_optimized.bat
run_spiders_optimized.bat prothomalo --monitor
run_spiders_optimized.bat --start-date 2024-08-01 --end-date 2024-08-31
```

#### Individual Spider Commands (Windows)
```cmd
# Run specific spiders directly
uv run scrapy crawl prothomalo
uv run scrapy crawl dailysun
uv run scrapy crawl ittefaq
uv run scrapy crawl bdpratidin
uv run scrapy crawl thebangladeshtoday
uv run scrapy crawl thedailystar

# 🪟 WINDOWS TIP: Add -L INFO to see scraping progress (UV can be quiet)
uv run scrapy crawl prothomalo -L INFO
uv run scrapy crawl dailysun -L INFO -s CLOSESPIDER_ITEMCOUNT=10

# With date filtering
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31 -L INFO
uv run scrapy crawl dailysun -a start_date=2024-08-01 -L INFO

# With custom settings (always include -L INFO for visibility)
uv run scrapy crawl ittefaq -L INFO -s CLOSESPIDER_ITEMCOUNT=100 -s DOWNLOAD_DELAY=2
```

#### Data Export (Windows)
```cmd
# Check scraped data
python toxlsx.py --list

# Export to Excel
python toxlsx.py --output news_data.xlsx

# Export specific newspaper
python toxlsx.py --paper "ProthomAlo" --output prothomalo.xlsx

# Export to CSV
python toxlsx.py --format csv --output news_data.csv

# Export with limits
python toxlsx.py --limit 100 --output recent_news.xlsx
```

### Windows Installation Options

#### Option 1: PowerShell (Recommended)
```powershell
# Run PowerShell as Administrator
# Install UV
irm https://astral.sh/uv/install.ps1 | iex

# Clone and setup project
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper
uv sync

# Test run
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=5
```

#### Option 2: Command Prompt
```cmd
# Install UV via pip (if PowerShell not available)
pip install uv

# Clone and setup project
git clone https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper.git
cd BDNewsPaperScraper
uv sync

# Test run
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=5
```

#### Option 3: WSL (Windows Subsystem for Linux)
```bash
# Install WSL first, then follow Linux instructions
wsl --install Ubuntu
# Restart computer
wsl
# Follow Linux/macOS instructions inside WSL
```

### Windows Automation

#### Task Scheduler (Windows equivalent of cron)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, weekly, etc.)
4. Set action to run: `python run_spiders_optimized.py`
5. Set working directory to project folder

#### PowerShell Script for Automation
```powershell
# Save as daily_scrape.ps1
Set-Location "C:\path\to\BDNewsPaperScraper"

# Run fast spiders
& python run_spiders_optimized.py prothomalo --monitor
& python run_spiders_optimized.py dailysun --monitor

# Export data
& python toxlsx.py --output "daily_news_$(Get-Date -Format 'yyyyMMdd').xlsx"

Write-Output "Daily scraping completed: $(Get-Date)"
```

### Windows Performance Tips

#### Optimize for Windows
```cmd
# Use Windows Defender exclusions for better performance
# Add project folder to Windows Defender exclusions

# Set high priority for scraping process (CMD as administrator)
wmic process where name="python.exe" call setpriority "high priority"

# Use SSD storage for better database performance
# Ensure adequate RAM (8GB+ recommended for all spiders)
```

#### Windows-Specific Settings
```cmd
# Adjust concurrent requests for Windows
uv run scrapy crawl prothomalo -s CONCURRENT_REQUESTS=32 -s DOWNLOAD_DELAY=0.5

# Use Windows-friendly log levels
uv run scrapy crawl dailysun -L INFO

# Windows path-safe output files
python toxlsx.py --output "news_data_%date:~10,4%%date:~4,2%%date:~7,2%.xlsx"
```

### Windows Logging & Output Issues

#### 🪟 Windows UV Minimal Output Problem

**Issue**: On Windows, `uv run` often shows only "Bytecode compiled" and minimal output, making it hard to see scraping progress.

**Solutions**:

1. **Use Explicit Log Levels** (Recommended)
   ```cmd
   # Force INFO level logging to see scraping progress
   uv run scrapy crawl prothomalo -L INFO
   uv run scrapy crawl dailysun -L INFO -s CLOSESPIDER_ITEMCOUNT=10
   
   # For detailed debugging output
   uv run scrapy crawl prothomalo -L DEBUG -s CLOSESPIDER_ITEMCOUNT=5
   
   # For minimal output (only warnings/errors)
   uv run scrapy crawl prothomalo -L WARNING
   ```

2. **Use the Python Runner** (Best for Windows)
   ```cmd
   # Python script shows full output by default
   python run_spiders_optimized.py prothomalo
   python run_spiders_optimized.py --monitor  # Shows real-time progress
   
   # Even better - shows live statistics and progress bars
   python run_spiders_optimized.py prothomalo --monitor
   ```

3. **Direct Scrapy Commands** (Without UV)
   ```cmd
   # Activate virtual environment first
   .venv\Scripts\activate
   
   # Run scrapy directly (shows full output)
   scrapy crawl prothomalo -L INFO
   scrapy crawl dailysun -L INFO -s CLOSESPIDER_ITEMCOUNT=10
   
   # Deactivate when done
   deactivate
   ```

4. **Force Verbose Output with UV**
   ```cmd
   # Use verbose flags to force output
   uv run --verbose scrapy crawl prothomalo -L INFO
   
   # Combine with log level and item count for testing
   uv run scrapy crawl prothomalo -L INFO -s CLOSESPIDER_ITEMCOUNT=20
   ```

5. **Monitor Log Files in Real-Time**
   ```cmd
   # Windows equivalent of tail -f (PowerShell)
   # Terminal 1: Start spider
   uv run scrapy crawl prothomalo -L INFO
   
   # Terminal 2: Monitor logs (PowerShell)
   Get-Content logs\prothomalo_*.log -Wait -Tail 20
   
   # OR using Command Prompt with tail equivalent
   powershell "Get-Content logs\prothomalo_*.log -Wait -Tail 20"
   ```

#### 📊 Windows Visibility Best Practices

**For Development/Testing:**
```cmd
# Always use explicit log levels and limits for testing
uv run scrapy crawl prothomalo -L INFO -s CLOSESPIDER_ITEMCOUNT=10

# Use Python runner for better Windows experience
python run_spiders_optimized.py prothomalo --monitor

# Monitor in real-time (separate terminal)
powershell "Get-Content logs\*.log -Wait -Tail 50"
```

**For Production:**
```cmd
# Use Python runner with monitoring (recommended)
python run_spiders_optimized.py --monitor

# Or use UV with explicit logging to file
uv run scrapy crawl prothomalo -L INFO > scraping.log 2>&1

# Monitor progress
powershell "Get-Content scraping.log -Wait -Tail 30"
```

**Quick Progress Check:**
```cmd
# Check how many articles have been scraped so far
python toxlsx.py --list

# Check database directly
sqlite3 news_articles.db "SELECT COUNT(*) FROM articles;"
sqlite3 news_articles.db "SELECT COUNT(*) FROM articles WHERE paper_name = 'ProthomAlo';"
```

#### 🔧 Windows UV Workarounds

If UV continues to show minimal output, use these alternatives:

1. **Virtual Environment Method** (Most reliable)
   ```cmd
   # One-time setup per session
   .venv\Scripts\activate
   
   # Run commands directly (full output)
   scrapy crawl prothomalo -L INFO
   scrapy crawl dailysun -L INFO -s CLOSESPIDER_ITEMCOUNT=50
   python performance_monitor.py
   
   # When done
   deactivate
   ```

2. **Python Runner Method** (Recommended)
   ```cmd
   # Always shows full output and progress
   python run_spiders_optimized.py prothomalo
   python run_spiders_optimized.py --monitor  # Best visibility
   python run_spiders_optimized.py --help     # See all options
   ```

3. **Batch File Method** (Easiest)
   ```cmd
   # Use the included .bat file
   run_spiders_optimized.bat prothomalo
   run_spiders_optimized.bat --monitor
   ```

### Windows Troubleshooting

#### Common Windows Issues

| Issue | Solution |
|-------|----------|
| `UV shows only "Bytecode compiled"` | Use `-L INFO` flag or switch to Python runner |
| `Can't see scraping progress` | Use `python run_spiders_optimized.py --monitor` |
| `'uv' is not recognized` | Add UV to PATH or reinstall UV |
| `Permission denied` | Run Command Prompt/PowerShell as Administrator |
| `SSL certificate verify failed` | Update certificates: `pip install --upgrade certifi` |
| `ModuleNotFoundError` | Run `uv sync` in project directory |
| `Access denied to file` | Close Excel/other programs using the file |
| `No output visible` | Use explicit log levels: `-L INFO` or `-L DEBUG` |

#### Windows-Specific Commands
```cmd
# Check UV installation
uv --version

# Check Python installation
python --version

# Check if Scrapy is available
uv run scrapy version

# Reset virtual environment (if issues)
rmdir /s .venv
uv venv --python 3.11
.venv\Scripts\activate
uv sync

# View logs (Windows)
type logs\prothomalo_*.log
type scrapy.log

# Monitor running processes
tasklist | findstr python
```

### Windows vs Linux/macOS Comparison

| Feature | Windows | Linux/macOS | Notes |
|---------|---------|-------------|-------|
| **Runner Script** | `python run_spiders_optimized.py` | `./run_spiders_optimized.sh` | Same functionality |
| **Performance** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Slightly slower on Windows |
| **Automation** | Task Scheduler | Cron jobs | Both work well |
| **Setup** | UV + Python | UV + bash | UV works on all platforms |
| **Monitoring** | ✅ Full support | ✅ Full support | Identical features |
| **Date Filtering** | ✅ Full support | ✅ Full support | Identical syntax |
| **Export Tools** | ✅ Full support | ✅ Full support | Same output formats |

### Why Use the Python Runner?

The `run_spiders_optimized.py` script provides:

✅ **Cross-platform compatibility** - Works on Windows, macOS, Linux  
✅ **All bash script features** - Monitoring, logging, progress tracking  
✅ **Same performance optimizations** - 64 concurrent requests, smart throttling  
✅ **Windows-native experience** - No need for WSL or bash emulation  
✅ **Identical command-line interface** - Same arguments and options  
✅ **Real-time output** - Live progress and logging  
✅ **Error handling** - Robust error detection and reporting  

Windows users get the **exact same experience** as Linux/macOS users!

### Method 1: Individual Spider Commands (Best for Development)
```bash
# Run specific newspapers one by one
uv run scrapy crawl prothomalo      # Fastest (API-based)
uv run scrapy crawl dailysun        # Enhanced extraction
uv run scrapy crawl ittefaq         # Robust pagination  
uv run scrapy crawl BDpratidin      # Bengali date handling
uv run scrapy crawl bangladesh_today # Multi-format support
uv run scrapy crawl thedailystar    # Legacy archive support

# With custom limits and settings
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=100  # Limit to 100 articles
uv run scrapy crawl dailysun -s DOWNLOAD_DELAY=2            # Add 2s delay
uv run scrapy crawl ittefaq -s CONCURRENT_REQUESTS=32       # More concurrent requests

# 🗓️ DATE RANGE FILTERING (All Spiders Support This!)
# Scrape articles from specific date ranges
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31  # January 2024
uv run scrapy crawl dailysun -a start_date=2024-06-01 -a end_date=2024-06-30    # June 2024
uv run scrapy crawl ittefaq -a start_date=2024-08-01        # From Aug 1 to today
uv run scrapy crawl BDpratidin -a start_date=2024-01-01 -a end_date=2024-12-31  # Entire 2024
uv run scrapy crawl bangladesh_today -a start_date=2024-03-01 -a end_date=2024-03-31  # March 2024
uv run scrapy crawl thedailystar -a start_date=2024-07-01 -a end_date=2024-07-31      # July 2024

# 📅 DATE FORMAT: YYYY-MM-DD (ISO format)
# ⏰ If only start_date is provided, end_date defaults to today
# ⏰ If only end_date is provided, start_date uses spider default (usually 6 months back)

# 🎯 COMBINE DATE FILTERING WITH OTHER OPTIONS
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31 -s CLOSESPIDER_ITEMCOUNT=50
uv run scrapy crawl dailysun -a start_date=2024-06-01 -a categories="national,sports" -s DOWNLOAD_DELAY=1
```

### Method 2: Enhanced Batch Runner (RECOMMENDED for Production)

#### 🐧 Linux/macOS
```bash
# Make executable first
chmod +x run_spiders_optimized.sh

# Run all spiders with optimized settings
./run_spiders_optimized.sh

# Run specific spider only
./run_spiders_optimized.sh prothomalo
./run_spiders_optimized.sh dailysun
./run_spiders_optimized.sh ittefaq

# Run with performance monitoring
./run_spiders_optimized.sh --monitor
./run_spiders_optimized.sh prothomalo --monitor

# 🗓️ DATE RANGE FILTERING with Enhanced Runner
# Run all spiders for specific date range
./run_spiders_optimized.sh --start-date 2024-01-01 --end-date 2024-01-31

# Run specific spider with date filtering
./run_spiders_optimized.sh prothomalo --start-date 2024-06-01 --end-date 2024-06-30

# Run with both monitoring and date filtering
./run_spiders_optimized.sh --monitor --start-date 2024-08-01 --end-date 2024-08-31
./run_spiders_optimized.sh prothomalo --monitor --start-date 2024-08-01

# Get help and see all options
./run_spiders_optimized.sh --help
```

#### 🪟 Windows
```cmd
# Run all spiders with optimized settings
python run_spiders_optimized.py

# Run specific spider only  
python run_spiders_optimized.py prothomalo
python run_spiders_optimized.py dailysun
python run_spiders_optimized.py ittefaq

# Run with performance monitoring
python run_spiders_optimized.py --monitor
python run_spiders_optimized.py prothomalo --monitor

# 🗓️ DATE RANGE FILTERING with Enhanced Runner
# Run all spiders for specific date range
python run_spiders_optimized.py --start-date 2024-01-01 --end-date 2024-01-31

# Run specific spider with date filtering
python run_spiders_optimized.py prothomalo --start-date 2024-06-01 --end-date 2024-06-30

# Run with both monitoring and date filtering
python run_spiders_optimized.py --monitor --start-date 2024-08-01 --end-date 2024-08-31
python run_spiders_optimized.py prothomalo --monitor --start-date 2024-08-01

# Get help and see all options
python run_spiders_optimized.py --help
```

#### Available Spiders
Both Linux/macOS and Windows versions support the same spiders:
- `prothomalo` - ProthomAlo (API-based, fastest)
- `bdpratidin` - BD Pratidin (Bengali handling)
- `dailysun` - Daily Sun (enhanced extraction)
- `ittefaq` - Daily Ittefaq (robust pagination)
- `thebangladeshtoday` - Bangladesh Today (multi-format)
- `thedailystar` - The Daily Star (legacy support)



### Method 3: Selective Running
```bash
# Run only fast spiders (API-based)
uv run scrapy crawl prothomalo

# Run only specific categories
uv run scrapy crawl ittefaq
uv run scrapy crawl dailysun
uv run scrapy crawl BDpratidin

# Run with specific parameters and date ranges
uv run scrapy crawl bangladesh_today -a start_date=2024-01-01 -a end_date=2024-01-31 -s CLOSESPIDER_ITEMCOUNT=50

# 📅 DATE-SPECIFIC SCRAPING EXAMPLES
# Last week's news
uv run scrapy crawl prothomalo -a start_date=2024-08-22 -a end_date=2024-08-29

# Monthly archives
uv run scrapy crawl dailysun -a start_date=2024-01-01 -a end_date=2024-01-31    # January
uv run scrapy crawl ittefaq -a start_date=2024-02-01 -a end_date=2024-02-29     # February
uv run scrapy crawl thedailystar -a start_date=2024-03-01 -a end_date=2024-03-31 # March

# Quarterly reports
uv run scrapy crawl BDpratidin -a start_date=2024-01-01 -a end_date=2024-03-31  # Q1 2024
uv run scrapy crawl bangladesh_today -a start_date=2024-04-01 -a end_date=2024-06-30 # Q2 2024
```

### Method 4: Development & Testing
```bash
# Test run with minimal data
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=5 -L DEBUG

# Monitor performance during run
uv run python performance_monitor.py &
uv run scrapy crawl dailysun

# Run with custom log levels
uv run scrapy crawl ittefaq -L INFO     # Less verbose
uv run scrapy crawl BDpratidin -L ERROR # Only errors
```

## 🚀 Enhanced Spider Runner (`run_spiders_optimized.sh`)

The optimized runner script provides the most comprehensive way to run spiders with performance monitoring, logging, and advanced options.

### Basic Usage
```bash
# Make executable (one time only)
chmod +x run_spiders_optimized.sh

# Run all spiders with optimized settings
./run_spiders_optimized.sh

# Run specific spider
./run_spiders_optimized.sh prothomalo
./run_spiders_optimized.sh dailysun
./run_spiders_optimized.sh ittefaq
```

### All Available Parameters

#### 1. Run Specific Spiders
```bash
# Individual spider execution
./run_spiders_optimized.sh prothomalo        # ProthomAlo (API-based, fastest)
./run_spiders_optimized.sh bdpratidin        # BD Pratidin (Bengali handling)
./run_spiders_optimized.sh dailysun          # Daily Sun (enhanced extraction)
./run_spiders_optimized.sh ittefaq           # Daily Ittefaq (robust pagination)
./run_spiders_optimized.sh bangladesh_today  # Bangladesh Today (multi-format)
./run_spiders_optimized.sh thedailystar      # The Daily Star (legacy support)
```

#### 2. Performance Monitoring
```bash
# Run all spiders with real-time monitoring
./run_spiders_optimized.sh --monitor

# Run specific spider with monitoring
./run_spiders_optimized.sh prothomalo --monitor
./run_spiders_optimized.sh dailysun --monitor

# Monitor provides:
# - Real-time performance metrics
# - Memory and CPU usage tracking
# - Scraping speed statistics
# - Automatic performance report generation
```

#### 3. Date Range Filtering
```bash
# Filter articles by date range (all spiders support this)
./run_spiders_optimized.sh --start-date 2024-01-01 --end-date 2024-01-31  # All spiders for January 2024
./run_spiders_optimized.sh prothomalo --start-date 2024-06-01 --end-date 2024-06-30  # ProthomAlo for June 2024

# From specific date to today
./run_spiders_optimized.sh dailysun --start-date 2024-08-01

# Up to specific date (from default start)
./run_spiders_optimized.sh ittefaq --end-date 2024-12-31

# Combine with monitoring
./run_spiders_optimized.sh --monitor --start-date 2024-08-01 --end-date 2024-08-31
./run_spiders_optimized.sh prothomalo --monitor --start-date 2024-01-01 --end-date 2024-01-31
```

#### 4. Help and Information
```bash
# Show all available options and spiders
./run_spiders_optimized.sh --help
./run_spiders_optimized.sh -h

# Output shows:
# - Available spider names
# - Date filtering options
# - Usage examples
# - Parameter explanations
```

### Advanced Features

#### Optimized Settings (Built-in)
The script automatically applies these performance optimizations:
```bash
# Settings applied by the optimized runner:
-s CONCURRENT_REQUESTS=64              # High concurrency
-s DOWNLOAD_DELAY=0.25                 # Minimal but respectful delay
-s AUTOTHROTTLE_TARGET_CONCURRENCY=8.0 # Smart throttling
-L INFO                                # Informative logging level
```

#### Automatic Logging
```bash
# Logs are automatically created in logs/ directory
logs/prothomalo_20240829_143022.log    # Timestamped logs
logs/dailysun_20240829_143545.log      # Per-spider logs
logs/ittefaq_20240829_144012.log       # Individual tracking

# View logs in real-time
tail -f logs/prothomalo_*.log
```

#### Smart Environment Detection
```bash
# Script automatically detects and uses:
# - UV package manager (preferred)
# - Fallback to direct scrapy commands
# - Performance monitor integration
# - Error handling and recovery
```

### Complete Usage Examples

#### Example 1: Quick Test Run
```bash
# Run fastest spider for testing
./run_spiders_optimized.sh prothomalo
# ✅ Uses API, completes in ~2-5 minutes
```

#### Example 2: Full Production Run
```bash
# Run all spiders with monitoring
./run_spiders_optimized.sh --monitor
# ✅ Comprehensive scraping with performance tracking
# ✅ Automatic report generation
# ✅ Individual logs per spider
```

#### Example 3: Selective High-Performance Run
```bash
# Run only fast/reliable spiders
./run_spiders_optimized.sh prothomalo --monitor
./run_spiders_optimized.sh dailysun --monitor
./run_spiders_optimized.sh ittefaq --monitor
```

#### Example 4: Development Workflow
```bash
# Test individual spiders during development
./run_spiders_optimized.sh prothomalo     # Fast API test
./run_spiders_optimized.sh --help         # Check available options
./run_spiders_optimized.sh bangladesh_today --monitor  # Full test with monitoring
```

### Output and Feedback

#### Success Messages
```bash
# Console output includes:
🚀 Starting all spiders with optimized settings...
📰 Running spider: prothomalo
Progress: 1/7
✅ Spider prothomalo completed successfully
🏁 All spiders completed!
Success: 7/7
Total time: 1234s (20m 34s)
📊 Generating performance report...
```

#### Error Handling
```bash
# Automatic error detection and reporting:
❌ Spider dailysun failed with exit code 1
⚠️  UV not found, using direct commands
⚠️  Performance monitor not found
```

### Performance Benefits

| Feature | Benefit |
|---------|---------|
| **High Concurrency** | 64 concurrent requests for faster scraping |
| **Smart Throttling** | Automatic speed adjustment to avoid blocking |
| **UV Integration** | Ultra-fast dependency resolution |
| **Individual Logs** | Detailed per-spider tracking |
| **Progress Tracking** | Real-time completion status |
| **Error Recovery** | Continues with remaining spiders on failure |
| **Performance Reports** | Automatic analytics generation |

### Comparison with Other Methods

| Method | Speed | Monitoring | Logs | Error Handling | Best For |
|--------|-------|------------|------|----------------|----------|
| `run_spiders_optimized.sh` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Production |
| Individual commands | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | Development |
| Custom scripts | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Custom needs |

## 🚀 How to Run the Project

### Method 5: Scheduled & Automated Runs
```bash
# Add to crontab for automatic daily runs
crontab -e

# Example cron entries:

# Run all spiders daily at 2 AM using optimized runner
0 2 * * * cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh >> /var/log/scraper.log 2>&1

# Run all spiders with monitoring daily at 3 AM
0 3 * * * cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh --monitor >> /var/log/scraper_monitored.log 2>&1

# Run fast spider every 6 hours using optimized runner
0 */6 * * * cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh prothomalo >> /var/log/prothomalo.log 2>&1

# Run specific spiders on weekdays only
0 9 * * 1-5 cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh dailysun --monitor
0 14 * * 1-5 cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh ittefaq --monitor

# Alternative: traditional individual commands
0 */6 * * * cd /path/to/BDNewsPaperScraper && uv run scrapy crawl prothomalo >> /var/log/prothomalo_direct.log 2>&1
```

### Method 7: Container/Docker Approach
```bash
# Create a Dockerfile for containerized runs
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app
COPY . .

# Install UV and dependencies
RUN pip install uv
RUN uv sync

# Default command
CMD ["./run_spiders_optimized.sh", "--monitor"]
EOF

# Build and run in container
docker build -t bdnewspaper-scraper .
docker run -v $(pwd)/data:/app/data bdnewspaper-scraper

# Or with specific spider
docker run bdnewspaper-scraper ./run_spiders_optimized.sh prothomalo
```

### Method 8: Virtual Environment Direct Activation
```bash
# Activate virtual environment and run directly
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run without uv prefix (faster for multiple commands)
scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=100
scrapy crawl dailysun -s DOWNLOAD_DELAY=2
python performance_monitor.py

# Deactivate when done
deactivate
```

### Method 9: IDE Integration (VS Code/PyCharm)
```bash
# VS Code launch.json configuration
cat > .vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Prothomalo Spider",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/.venv/bin/scrapy",
            "args": ["crawl", "prothomalo", "-s", "CLOSESPIDER_ITEMCOUNT=10"],
            "console": "integratedTerminal"
        }
    ]
}
EOF

# PyCharm run configuration:
# Script path: .venv/bin/scrapy
# Parameters: crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10
# Working directory: /path/to/BDNewsPaperScraper
```

### Method 10: System Service (Linux/macOS)
```bash
# Create systemd service for automatic runs
sudo cat > /etc/systemd/system/bdnewspaper.service << 'EOF'
[Unit]
Description=BD Newspaper Scraper
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/BDNewsPaperScraper
ExecStart=/path/to/BDNewsPaperScraper/run_spiders_optimized.sh --monitor
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable bdnewspaper.service
sudo systemctl start bdnewspaper.service

# Create timer for periodic runs
sudo cat > /etc/systemd/system/bdnewspaper.timer << 'EOF'
[Unit]
Description=Run BD Newspaper Scraper daily
Requires=bdnewspaper.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl enable bdnewspaper.timer
```

### Method 11: Environment-Specific Runs
```bash
# Development environment
export SCRAPY_SETTINGS_MODULE=BDNewsPaper.settings_dev
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=5 -L DEBUG

# Staging environment
export SCRAPY_SETTINGS_MODULE=BDNewsPaper.settings_staging
./run_spiders_optimized.sh prothomalo --monitor

# Production environment
export SCRAPY_SETTINGS_MODULE=BDNewsPaper.settings_prod
./run_spiders_optimized.sh --monitor

# Testing environment with mock data
export SCRAPY_SETTINGS_MODULE=BDNewsPaper.settings_test
uv run scrapy crawl prothomalo -s DOWNLOAD_DELAY=0 -s ROBOTSTXT_OBEY=False
```

### Method 12: Multi-Instance Parallel Runs
```bash
# Run multiple spiders in parallel (advanced users)
# Terminal 1
./run_spiders_optimized.sh prothomalo --monitor &

# Terminal 2  
./run_spiders_optimized.sh dailysun --monitor &

# Terminal 3
./run_spiders_optimized.sh ittefaq --monitor &

# Wait for all to complete
wait

# Or using GNU parallel
parallel -j 3 './run_spiders_optimized.sh {} --monitor' ::: prothomalo dailysun ittefaq
```

### Method 13: Makefile Approach
```bash
# Create Makefile for easy commands
cat > Makefile << 'EOF'
.PHONY: install test run-all run-fast clean

install:
	uv sync

test:
	./run_spiders_optimized.sh prothomalo --monitor

run-all:
	./run_spiders_optimized.sh --monitor

run-fast:
	./run_spiders_optimized.sh prothomalo

export:
	./toxlsx.py --output "export_$(date +%Y%m%d).xlsx"

clean:
	rm -rf logs/* *.log
	rm -rf .scrapy/

stats:
	./toxlsx.py --list
EOF

# Use with make commands
make install
make test
make run-all
make export
```

### Method 14: CI/CD Pipeline Integration
```bash
# GitHub Actions workflow (.github/workflows/scraper.yml)
cat > .github/workflows/scraper.yml << 'EOF'
name: News Scraper
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Install UV
      run: curl -LsSf https://astral.sh/uv/install.sh | sh
    - name: Setup project
      run: |
        source ~/.bashrc
        uv sync
    - name: Run scraper
      run: ./run_spiders_optimized.sh --monitor
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: scraped-data
        path: news_articles.db
EOF

# GitLab CI (.gitlab-ci.yml)
cat > .gitlab-ci.yml << 'EOF'
stages:
  - scrape

scrape_news:
  stage: scrape
  image: python:3.11
  script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - source ~/.bashrc
    - uv sync
    - ./run_spiders_optimized.sh --monitor
  artifacts:
    paths:
      - news_articles.db
    expire_in: 1 week
  only:
    - schedules
EOF
```
```bash
# Custom Python script approach
cat > custom_runner.py << 'EOF'
#!/usr/bin/env python3
import subprocess
import sys

spiders = ['prothomalo', 'dailysun', 'ittefaq', 'BDpratidin']

for spider in spiders:
    print(f"Running {spider}...")
    result = subprocess.run([
        'uv', 'run', 'scrapy', 'crawl', spider,
        '-s', 'CLOSESPIDER_ITEMCOUNT=100'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {spider} completed successfully")
    else:
        print(f"❌ {spider} failed: {result.stderr}")
EOF

chmod +x custom_runner.py
python custom_runner.py
```

### Option 1: Run Individual Spiders (Recommended)
```bash
# Run specific newspaper spiders
uv run scrapy crawl prothomalo      # ProthomAlo (fastest, API-based)
uv run scrapy crawl dailysun        # Daily Sun
uv run scrapy crawl ittefaq         # Daily Ittefaq  
uv run scrapy crawl kalerKantho     # Kaler Kantho
uv run scrapy crawl BDpratidin      # BD Pratidin
uv run scrapy crawl bangladesh_today # Bangladesh Today
uv run scrapy crawl thedailystar    # The Daily Star

# Run with custom settings
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=100  # Limit to 100 articles
uv run scrapy crawl dailysun -s DOWNLOAD_DELAY=2            # Add 2s delay between requests
```

### Option 2: Run All Spiders (RECOMMENDED)
```bash
# Enhanced runner with optimizations (recommended)
chmod +x run_spiders_optimized.sh
./run_spiders_optimized.sh
```

### Option 3: Run with Custom Parameters
```bash
# Run specific spider with monitoring
uv run scrapy crawl prothomalo \
  -s CLOSESPIDER_ITEMCOUNT=500 \
  -s DOWNLOAD_DELAY=1 \
  -s CONCURRENT_REQUESTS=16 \
  -L INFO

# Run spider for specific date range (if supported)
uv run scrapy crawl ittefaq -a start_date=2024-01-01 -a end_date=2024-01-31
```

## 💾 Data Management & Export Options

### Quick Data Overview
```bash
# Check scraped data immediately
./toxlsx.py --list

# Example output:
# Shared News Articles Database
# ========================================
# Database file: news_articles.db
# Total articles: 1,234
# Date range: 2024-01-01 to 2024-12-31
# 
# Articles by newspaper:
# ------------------------------
#   ProthomAlo: 456 articles
#   The Daily Ittefaq: 321 articles
#   Daily Sun: 234 articles
#   Kaler Kantho: 123 articles
```

### Export Everything
```bash
# Install pandas for export functionality (one time only)
uv add pandas openpyxl  # For Excel export
# OR
uv add pandas          # For CSV export only

# Export all articles to Excel
./toxlsx.py --output all_news.xlsx

# Export all articles to CSV  
./toxlsx.py --format csv --output all_news.csv
```

### Export by Newspaper
```bash
# Export specific newspaper articles
./toxlsx.py --paper "ProthomAlo" --output prothomalo.xlsx
./toxlsx.py --paper "Daily Sun" --output dailysun.xlsx  
./toxlsx.py --paper "The Daily Ittefaq" --output ittefaq.xlsx
./toxlsx.py --paper "Kaler Kantho" --output kalerkantho.xlsx
./toxlsx.py --paper "BD Pratidin" --output bdpratidin.xlsx
./toxlsx.py --paper "Bangladesh Today" --output bangladesh_today.xlsx
./toxlsx.py --paper "The Daily Star" --output thedailystar.xlsx

# Export as CSV instead of Excel
./toxlsx.py --paper "ProthomAlo" --format csv --output prothomalo.csv
```

### Export with Limits
```bash
# Latest articles from all newspapers
./toxlsx.py --limit 100 --output recent_news.xlsx
./toxlsx.py --limit 500 --format csv --output recent_500.csv

# Latest from specific newspaper
./toxlsx.py --paper "ProthomAlo" --limit 50 --output latest_prothomalo.xlsx
./toxlsx.py --paper "Daily Sun" --limit 25 --format csv --output latest_dailysun.csv
```

### Advanced Database Queries
```bash
# Count articles by newspaper
sqlite3 news_articles.db "SELECT paper_name, COUNT(*) as count FROM articles GROUP BY paper_name ORDER BY count DESC;"

# Recent headlines from all newspapers
sqlite3 news_articles.db "SELECT headline, paper_name, publication_date FROM articles ORDER BY scraped_at DESC LIMIT 20;"

# Search for specific topics
sqlite3 news_articles.db "SELECT headline, paper_name FROM articles WHERE headline LIKE '%politics%' LIMIT 10;"

# Articles from today
sqlite3 news_articles.db "SELECT COUNT(*) FROM articles WHERE date(scraped_at) = date('now');"

# Export query results to CSV
sqlite3 -header -csv news_articles.db "SELECT * FROM articles WHERE paper_name = 'ProthomAlo' LIMIT 100;" > prothomalo_latest.csv
```

## 📊 Monitor Progress & Results

### Check Running Progress
```bash
# View real-time logs (in another terminal)
tail -f scrapy.log

# Monitor with performance tool
uv run python performance_monitor.py
```

### View Scraped Data
```bash
# Show database information and statistics
./toxlsx.py --list

# Check article counts by newspaper
sqlite3 news_articles.db "SELECT paper_name, COUNT(*) FROM articles GROUP BY paper_name;"

# View recent headlines
sqlite3 news_articles.db "SELECT headline, paper_name FROM articles ORDER BY scraped_at DESC LIMIT 10;"
```

## 📈 Export & Analyze Data

### View Database Information
```bash
# Show database stats and newspaper breakdown
./toxlsx.py --list

# Output example:
# Shared News Articles Database
# ========================================
# Database file: news_articles.db
# Total articles: 1,234
# Date range: 2024-01-01 to 2024-12-31
# 
# Articles by newspaper:
# ------------------------------
#   ProthomAlo: 456 articles
#   The Daily Ittefaq: 321 articles
#   Daily Sun: 234 articles
#   ...
```

### Export All Articles  
```bash
# Install pandas for export functionality (one time only)
uv add pandas openpyxl  # For Excel export
# OR
uv add pandas          # For CSV export only

# Export all articles to Excel
./toxlsx.py --output all_news.xlsx

# Export all articles to CSV  
./toxlsx.py --format csv --output all_news.csv
```

### Export Filtered Articles
```bash
# Export only ProthomAlo articles
./toxlsx.py --paper "ProthomAlo" --output prothomalo.xlsx

# Export latest 100 articles from all newspapers
./toxlsx.py --limit 100 --output recent_news.xlsx

# Export latest 50 Daily Sun articles as CSV
./toxlsx.py --paper "Daily Sun" --limit 50 --format csv

# Export latest Ittefaq articles
./toxlsx.py --paper "The Daily Ittefaq" --limit 25 --output ittefaq_latest.xlsx
```

### Advanced Export Options
```bash
# See all available options
./toxlsx.py --help

# Available filters:
# --paper "newspaper_name"  # Filter by specific newspaper
# --limit N                 # Limit to N most recent articles  
# --format excel|csv        # Output format
# --output filename         # Custom output filename
```

### Raw Database Access
```bash
# Direct SQLite queries for advanced analysis
sqlite3 news_articles.db "SELECT paper_name, COUNT(*) FROM articles GROUP BY paper_name;"

sqlite3 news_articles.db "SELECT headline, article FROM articles WHERE paper_name = 'ProthomAlo' LIMIT 5;"

sqlite3 news_articles.db "SELECT COUNT(*) FROM articles WHERE publication_date LIKE '2024%';"
```

## 📈 Export & Analyze Data

### Export to Excel/CSV
```bash
# Export specific spider data
./toxlsx.py --spider prothomalo                    # Excel format
./toxlsx.py --spider dailysun --format csv        # CSV format
./toxlsx.py --spider ittefaq --output custom.xlsx # Custom filename

# Export all available data
./toxlsx.py --spider legacy --output all_news.xlsx
```

### Advanced Export Options
```bash
# See all export options
./toxlsx.py --help

# Export with custom table
./toxlsx.py --db custom.db --table my_articles --output data.xlsx
```

## 📊 Available Spiders

| Spider Name | Command | Website | Features |
|-------------|---------|---------|----------|
| `prothomalo` | `uv run scrapy crawl prothomalo` | ProthomAlo | ✅ API-based, Fast, JSON responses, **Date filtering** |
| `dailysun` | `uv run scrapy crawl dailysun` | Daily Sun | ✅ Enhanced extraction, Bengali support, **Date filtering** |
| `ittefaq` | `uv run scrapy crawl ittefaq` | Daily Ittefaq | ✅ Robust pagination, **Date filtering** |
| `BDpratidin` | `uv run scrapy crawl BDpratidin` | BD Pratidin | ✅ Bengali date handling, Categories, **Date filtering** |
| `bangladesh_today` | `uv run scrapy crawl bangladesh_today` | Bangladesh Today | ✅ Multi-format support, English content, **Date filtering** |
| `thedailystar` | `uv run scrapy crawl thedailystar` | The Daily Star | ✅ Legacy support, Large archive, **Date filtering** |
| ~~`kalerKantho`~~ | ❌ **DISCONTINUED** | ~~Kaler Kantho~~ | ❌ English version discontinued Aug 2024, now Bangla-only |

## 🗓️ Date Range Filtering (All Spiders)

**All spiders now support date range filtering!** You can scrape articles from specific time periods using the `start_date` and `end_date` parameters.

### Basic Date Filtering
```bash
# Scrape articles from January 2024
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31

# Scrape from specific date to today
uv run scrapy crawl dailysun -a start_date=2024-06-01

# Scrape up to specific date (from default start)
uv run scrapy crawl ittefaq -a end_date=2024-12-31
```

### Advanced Date Examples
```bash
# 📅 MONTHLY ARCHIVES
uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31    # January 2024
uv run scrapy crawl dailysun -a start_date=2024-02-01 -a end_date=2024-02-29      # February 2024
uv run scrapy crawl ittefaq -a start_date=2024-03-01 -a end_date=2024-03-31       # March 2024

# 📊 QUARTERLY REPORTS
uv run scrapy crawl BDpratidin -a start_date=2024-01-01 -a end_date=2024-03-31   # Q1 2024
uv run scrapy crawl bangladesh_today -a start_date=2024-04-01 -a end_date=2024-06-30   # Q2 2024
uv run scrapy crawl thedailystar -a start_date=2024-07-01 -a end_date=2024-09-30  # Q3 2024

# 📰 RECENT NEWS
uv run scrapy crawl thedailystar -a start_date=2024-08-22 -a end_date=2024-08-29  # Last week
uv run scrapy crawl prothomalo -a start_date=2024-08-01                           # This month

# 🎯 COMBINED WITH OTHER FILTERS
uv run scrapy crawl dailysun -a start_date=2024-01-01 -a end_date=2024-01-31 -s CLOSESPIDER_ITEMCOUNT=100
uv run scrapy crawl prothomalo -a start_date=2024-06-01 -a categories="Bangladesh,Sports" -s DOWNLOAD_DELAY=1
```

### Date Format Rules
- **Format**: `YYYY-MM-DD` (ISO 8601 standard)
- **Timezone**: All dates are interpreted in Dhaka timezone (Asia/Dhaka)
- **Default start_date**: Usually 6 months back (varies by spider)
- **Default end_date**: Today's date
- **Range**: Only articles published within the specified range are scraped

### Pro Tips for Date Filtering
```bash
# ✅ RECOMMENDED: Use specific date ranges for faster scraping
uv run scrapy crawl prothomalo -a start_date=2024-08-01 -a end_date=2024-08-31

# ✅ PERFORMANCE: Shorter date ranges = faster completion
uv run scrapy crawl dailysun -a start_date=2024-08-25 -a end_date=2024-08-29

# ✅ ARCHIVAL: For historical data, use longer ranges
uv run scrapy crawl thedailystar -a start_date=2024-01-01 -a end_date=2024-12-31

# ❌ AVOID: Very large date ranges without limits (may take hours)
# uv run scrapy crawl ittefaq -a start_date=2020-01-01 -a end_date=2024-12-31

# ✅ BETTER: Use limits with large ranges
uv run scrapy crawl ittefaq -a start_date=2023-01-01 -a end_date=2024-12-31 -s CLOSESPIDER_ITEMCOUNT=1000
```

## 🗂️ Database Structure

All spiders now write to a **single shared database** (`news_articles.db`) with only the essential fields you requested:

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    paper_name TEXT NOT NULL,
    headline TEXT NOT NULL,
    article TEXT NOT NULL,
    publication_date TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Essential Fields Only:
- **`url`** - Article URL (unique identifier)
- **`paper_name`** - Newspaper name (e.g., "ProthomAlo", "The Daily Ittefaq")
- **`headline`** - Article title/headline
- **`article`** - Full article content (cleaned text)
- **`publication_date`** - When the article was published
- **`scraped_at`** - When we scraped it (automatic timestamp)

### Benefits:
- ✅ **Single database file** for all newspapers
- ✅ **Essential fields only** - no unnecessary data
- ✅ **Fast queries** with proper indexing
- ✅ **Automatic duplicate prevention** by URL
- ✅ **Clean, normalized content**

## 🔧 Development & Customization

### Adding Custom Settings
```bash
# Create custom settings file
cp BDNewsPaper/settings.py BDNewsPaper/settings_custom.py

# Run with custom settings
uv run scrapy crawl prothomalo -s SETTINGS_MODULE=BDNewsPaper.settings_custom
```

### Code Quality Tools
```bash
# Format code
uv run black BDNewsPaper/

# Sort imports  
uv run isort BDNewsPaper/

# Lint code
uv run flake8 BDNewsPaper/

# Run all quality checks
uv run black . && uv run isort . && uv run flake8 .
```

### Performance Monitoring
```bash
# Monitor spider performance in real-time
uv run python performance_monitor.py

# View statistics
uv run python performance_monitor.py stats

# Generate detailed report
uv run python performance_monitor.py report
```

## 🔧 Performance Tips & Best Practices

### Optimal Spider Selection
```bash
# Fastest spiders (API-based, recommended for frequent runs)
uv run scrapy crawl prothomalo      # Uses API, very fast

# Medium speed spiders (good balance)
uv run scrapy crawl dailysun        # Enhanced extraction
uv run scrapy crawl ittefaq         # Robust pagination

# Comprehensive spiders (slower but thorough)
uv run scrapy crawl BDpratidin      # Bengali date handling
uv run scrapy crawl bangladesh_today # Multi-format support
uv run scrapy crawl thedailystar    # Large archive
```

### Performance Optimization
```bash
# Limit articles for faster testing
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=50

# Increase concurrent requests for faster scraping
uv run scrapy crawl dailysun -s CONCURRENT_REQUESTS=32

# Add delays to be respectful to servers
uv run scrapy crawl ittefaq -s DOWNLOAD_DELAY=1

# Disable unnecessary features for speed
uv run scrapy crawl ittefaq -s COOKIES_ENABLED=False -s RETRY_ENABLED=False
```

### Monitoring Commands
```bash
# Real-time monitoring
tail -f scrapy.log | grep -E "(Spider opened|items|Spider closed)"

# Database size monitoring
ls -lh news_articles.db*

# Performance monitoring
uv run python performance_monitor.py
```

### Error Handling & Recovery
```bash
# Resume interrupted scraping (spiders handle duplicates automatically)
uv run scrapy crawl prothomalo  # Will skip existing URLs

# Clear specific spider data if needed
sqlite3 news_articles.db "DELETE FROM articles WHERE paper_name = 'ProthomAlo';"

# Backup database before major runs
cp news_articles.db news_articles_backup_$(date +%Y%m%d).db
```

## ⚙️ Configuration & Customization

### Spider Settings
```bash
# Limit articles per spider
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=100

# Add delays between requests
uv run scrapy crawl dailysun -s DOWNLOAD_DELAY=2

# Increase concurrent requests
uv run scrapy crawl ittefaq -s CONCURRENT_REQUESTS=32

# Set log level
uv run scrapy crawl BDpratidin -L DEBUG
```

### Database Settings
```bash
# All spiders now write to a single shared database:
# news_articles.db (contains all newspaper articles)

# Check database content:
sqlite3 news_articles.db "SELECT paper_name, COUNT(*) FROM articles GROUP BY paper_name;"

# View recent articles:
sqlite3 news_articles.db "SELECT headline, paper_name FROM articles ORDER BY scraped_at DESC LIMIT 10;"
```

### Key Features
- **Enhanced error handling** with comprehensive try-catch blocks
- **Single shared database** for all newspapers with essential fields only
- **Duplicate URL prevention** with automatic checking
- **Smart content extraction** with multiple fallback methods
- **Bengali date conversion** with optimized processing
- **Automatic data cleaning** and text normalization
- **Simplified data structure** focusing on core content
- **Fast export tools** supporting Excel and CSV formats

## 📁 Project Structure

```
BDNewsPaperScraper/
├── BDNewsPaper/              # Main Scrapy project
│   ├── spiders/             # Enhanced spider implementations
│   │   ├── prothomalo.py    # ProthomAlo spider (API-based)
│   │   ├── dailysun.py      # Daily Sun spider  
│   │   ├── ittefaq.py       # Daily Ittefaq spider
│   │   ├── kalerkantho.py.disabled # Kaler Kantho spider (DISCONTINUED)
│   │   ├── bdpratidin.py    # BD Pratidin spider
│   │   ├── thebangladeshtoday.py # Bangladesh Today spider
│   │   └── thedailystar.py  # The Daily Star spider
│   ├── items.py            # Advanced data models with auto-processing
│   ├── pipelines.py        # Data processing and storage pipelines
│   ├── settings.py         # Scrapy configuration and optimizations
│   ├── middlewares.py      # Custom middlewares and error handling
│   └── bengalidate_to_englishdate.py  # Bengali date conversion utility
├── pyproject.toml          # UV project configuration  
├── uv.toml                 # UV workspace settings
├── setup.sh               # Automated setup script (Linux/macOS)
├── run_spiders_optimized.sh  # Enhanced multi-spider runner (Linux/macOS)
├── run_spiders_optimized.py  # Cross-platform Python runner (Windows/Linux/macOS) ⭐NEW⭐
├── run_spiders_optimized.bat # Windows batch file wrapper ⭐NEW⭐
├── performance_monitor.py  # Performance monitoring and analytics
├── toxlsx.py              # Enhanced data export tool (Excel/CSV)
├── news_articles.db       # Shared database for all newspapers
├── scrapy.cfg             # Scrapy deployment configuration
└── README.md              # This comprehensive documentation
```

### Cross-Platform Support

| File | Platform | Purpose |
|------|----------|---------|
| `run_spiders_optimized.sh` | Linux/macOS | Bash script with full features |
| `run_spiders_optimized.py` | **All Platforms** ⭐ | Python script with identical features |
| `run_spiders_optimized.bat` | Windows | Batch wrapper for easier Windows usage |
| `setup.sh` | Linux/macOS | Automated setup |
| `toxlsx.py` | **All Platforms** | Data export tool |
| `performance_monitor.py` | **All Platforms** | Performance monitoring |

## 🐛 Troubleshooting

### Installation Issues
```bash
# Check UV installation
uv --version

# Check Python version  
python --version  # Should be 3.9+

# Verify project setup
./setup.sh --check

# Clean installation
./setup.sh --clean && ./setup.sh --all
```

### Spider Issues
```bash
# Test spider imports
uv run python -c "from BDNewsPaper.spiders.prothomalo import *; print('OK')"

# Run spider with debug logging
uv run scrapy crawl prothomalo -L DEBUG

# Check database creation
ls -la *.db

# View recent articles
sqlite3 prothomalo_articles.db "SELECT headline, publication_date FROM articles ORDER BY id DESC LIMIT 5;"
```

### Common Solutions
1. **"UV not found"**: Install UV using `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **"Import errors"**: Run `uv sync` to install dependencies
3. **"No articles scraped"**: Check internet connection and website accessibility
4. **"Database locked"**: Stop all running spiders and wait a few seconds
5. **"Spider not found"**: Use `uv run scrapy list` to see available spiders

## 🐛 Troubleshooting

### Installation Issues
```bash
# Check UV installation
uv --version

# Check Python version  
python --version  # Should be 3.9+

# Verify project setup
./setup.sh --check

# Clean installation
rm -rf .venv uv.lock
./setup.sh --clean && ./setup.sh --all

# Manual environment setup
uv venv --python 3.11
source .venv/bin/activate
uv sync
```

### Spider Issues
```bash
# Test spider imports
uv run python -c "from BDNewsPaper.spiders.prothomalo import ProthomAloSpider; print('Import OK')"

# Run spider with debug logging
uv run scrapy crawl prothomalo -L DEBUG -s CLOSESPIDER_ITEMCOUNT=2

# Check scrapy configuration
uv run scrapy check

# List all available spiders
uv run scrapy list

# Test spider with minimal settings
uv run scrapy crawl prothomalo -s ROBOTSTXT_OBEY=False -s CLOSESPIDER_ITEMCOUNT=1
```

### Database Issues
```bash
# Check database creation and permissions
ls -la *.db
sqlite3 news_articles.db ".tables"
sqlite3 news_articles.db ".schema articles"

# Check recent articles
sqlite3 news_articles.db "SELECT COUNT(*) FROM articles;"
sqlite3 news_articles.db "SELECT headline, paper_name FROM articles ORDER BY id DESC LIMIT 5;"

# Fix database permissions
chmod 664 news_articles.db

# Repair database if corrupted
sqlite3 news_articles.db ".recover" | sqlite3 news_articles_recovered.db
```

### Network & Website Issues
```bash
# Test website connectivity
curl -I https://www.prothomalo.com/
curl -I https://www.dailysun.com/

# Test with different user agent
uv run scrapy crawl prothomalo -s USER_AGENT="Mozilla/5.0 (compatible; Bot)"

# Increase timeouts for slow networks
uv run scrapy crawl dailysun -s DOWNLOAD_TIMEOUT=30 -s DOWNLOAD_DELAY=3

# Disable SSL verification if needed (not recommended for production)
uv run scrapy crawl ittefaq -s DOWNLOAD_HANDLERS_BASE={"https": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler"}
```

### Performance Issues
```bash
# Reduce concurrent requests
uv run scrapy crawl kalerKantho -s CONCURRENT_REQUESTS=1 -s CONCURRENT_REQUESTS_PER_DOMAIN=1

# Monitor memory usage
uv run python performance_monitor.py &
uv run scrapy crawl BDpratidin

# Clear logs and cache
rm -rf logs/* .scrapy/
```

### Export Issues
```bash
# Install pandas for toxlsx.py
uv add pandas openpyxl

# Test export functionality
./toxlsx.py --list
./toxlsx.py --paper "ProthomAlo" --limit 5 --output test.xlsx

# Check export file permissions
ls -la *.xlsx *.csv

# Manual CSV export
sqlite3 -header -csv news_articles.db "SELECT * FROM articles LIMIT 10;" > test_export.csv
```

### Common Error Solutions

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'scrapy'` | Run `uv sync` to install dependencies |
| `command not found: uv` | Install UV: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ImportError: No module named 'BDNewsPaper'` | Run from project root directory |
| `DatabaseError: database is locked` | Stop all running spiders, wait 10 seconds |
| `SSL certificate verify failed` | Add `-s DOWNLOAD_HANDLERS_BASE={...}` flag |
| `No articles scraped` | Check internet connection, try with `-L DEBUG` |
| `Permission denied` | Check file permissions with `ls -la` |
| `[Errno 111] Connection refused` | Website may be down, try later |

### Getting Help
```bash
# Check scrapy version and configuration
uv run scrapy version
uv run scrapy settings

# Generate detailed logs
uv run scrapy crawl prothomalo -L DEBUG 2>&1 | tee debug.log

# Monitor system resources
top -p $(pgrep -f scrapy)
```

## 🚀 Production Deployment

### Using Scrapyd (Optional)
```bash
# Install scrapyd
uv add scrapyd

# Start scrapyd server
uv run scrapyd

# Deploy project
uv run scrapyd-deploy

# Schedule spider runs
curl http://localhost:6800/schedule.json -d project=BDNewsPaper -d spider=prothomalo
```

### Scheduling with Cron
```bash
# Add to crontab for daily runs
# crontab -e

# Run all spiders daily at 2 AM
0 2 * * * cd /path/to/BDNewsPaperScraper && ./run_spiders_optimized.sh

# Run specific spider every 6 hours  
0 */6 * * * cd /path/to/BDNewsPaperScraper && uv run scrapy crawl prothomalo
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Install dependencies: `uv sync`
4. Make your changes following existing patterns
5. Test your changes: `uv run scrapy crawl <spider_name> -s CLOSESPIDER_ITEMCOUNT=5`
6. Format code: `uv run black . && uv run isort .`
7. Submit a pull request

### Adding a New Spider
1. Create new spider file in `BDNewsPaper/spiders/`
2. Follow existing spider patterns and error handling
3. Add database configuration for the new spider
4. Update this README with the new spider information
5. Test thoroughly with small item counts

## 📄 License

MIT License - see LICENSE file for details.

---

## 📋 Frequently Asked Questions (FAQ)

### General Usage

**Q: Which spider should I run first?**
A: Start with `prothomalo` - it's the fastest (API-based) and most reliable for testing.

**Q: How long does it take to scrape all newspapers?**
A: Depends on limits set:
- With limits (100 articles each): ~10-15 minutes
- Without limits (full scrape): 1-3 hours depending on network

**Q: Can I run multiple spiders simultaneously?**
A: Yes, but be respectful. Run 2-3 at most to avoid overwhelming servers.

**Q: Do I need to delete old data before running again?**
A: No, spiders automatically handle duplicates by URL. Old data is preserved.

### Data & Export

**Q: Where is my scraped data stored?**
A: Everything goes into a single database: `news_articles.db`

**Q: What format can I export to?**
A: Excel (.xlsx) and CSV (.csv) using the `./toxlsx.py` tool

**Q: How do I view data without exporting?**
A: Use `./toxlsx.py --list` for quick overview or SQLite commands for detailed queries

**Q: Can I filter data by date?**
A: Yes! Two ways:
1. **During scraping**: Use date arguments: `uv run scrapy crawl prothomalo -a start_date=2024-01-01 -a end_date=2024-01-31`
2. **After scraping**: SQLite queries: `sqlite3 news_articles.db "SELECT * FROM articles WHERE publication_date LIKE '2024-01%';"`

**Q: How do I scrape articles from specific dates?**
A: All spiders support date filtering with these arguments:
- `start_date=YYYY-MM-DD` - Start from this date
- `end_date=YYYY-MM-DD` - End at this date
Example: `uv run scrapy crawl dailysun -a start_date=2024-08-01 -a end_date=2024-08-31`

### Technical

**Q: My spider isn't finding any articles, what's wrong?**
A: 
1. Check internet connection
2. Run with debug: `uv run scrapy crawl <spider> -L DEBUG -s CLOSESPIDER_ITEMCOUNT=2`
3. Verify the website is accessible: `curl -I <website-url>`

**Q: Can I modify the scraped fields?**
A: Yes, edit `BDNewsPaper/items.py` and corresponding spider files, but the current structure is optimized for essential data.

**Q: How do I speed up scraping?**
A: 
- Use `prothomalo` (fastest)
- Increase concurrent requests: `-s CONCURRENT_REQUESTS=32`
- Set limits: `-s CLOSESPIDER_ITEMCOUNT=100`

**Q: Is this legal?**
A: This scraper respects robots.txt and includes delays. Always check website terms of service.

### Troubleshooting

**Q: "ModuleNotFoundError" errors?**
A: Run `uv sync` to install all dependencies

**Q: "Database is locked" error?**
A: Stop all running spiders and wait 10 seconds before retrying

**Q: Spider runs but gets 0 articles?**
A: Website structure may have changed. Check with `-L DEBUG` flag and update selectors if needed.

## 💡 Pro Tips

### 🚀 Recommended: Use the Optimized Runner
```bash
# BEST PRACTICE: Use run_spiders_optimized.sh for all production runs
./run_spiders_optimized.sh                    # All spiders with optimizations
./run_spiders_optimized.sh prothomalo --monitor  # Single spider with monitoring

# Why it's better:
# ✅ 64 concurrent requests (vs 16 default)
# ✅ Smart auto-throttling
# ✅ Individual timestamped logs
# ✅ Real-time progress tracking
# ✅ Automatic performance reports
# ✅ Built-in error handling
# ✅ UV auto-detection
```

### Performance Optimization
```bash
# Fast test run (recommended for development)
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=10

# Production run with optimal settings
uv run scrapy crawl prothomalo -s CONCURRENT_REQUESTS=16 -s DOWNLOAD_DELAY=1

# Monitor while running
tail -f scrapy.log | grep -E "(scraped|items)"
```

### Automated Workflows
```bash
# Create a daily scraping script
cat > daily_scrape.sh << 'EOF'
#!/bin/bash
cd /path/to/BDNewsPaperScraper
source .venv/bin/activate

# Run fast spiders daily
uv run scrapy crawl prothomalo -s CLOSESPIDER_ITEMCOUNT=200
uv run scrapy crawl dailysun -s CLOSESPIDER_ITEMCOUNT=100

# Export latest data
./toxlsx.py --limit 500 --output "daily_news_$(date +%Y%m%d).xlsx"

echo "Daily scraping completed: $(date)"
EOF

chmod +x daily_scrape.sh
```

### Data Analysis Tips
```bash
# Quick statistics
sqlite3 news_articles.db "
SELECT 
    paper_name,
    COUNT(*) as total_articles,
    MIN(publication_date) as earliest,
    MAX(publication_date) as latest
FROM articles 
GROUP BY paper_name 
ORDER BY total_articles DESC;"

# Find trending topics
sqlite3 news_articles.db "
SELECT 
    substr(headline, 1, 50) as headline_preview,
    paper_name,
    publication_date
FROM articles 
WHERE headline LIKE '%economy%' 
   OR headline LIKE '%politics%'
ORDER BY publication_date DESC 
LIMIT 20;"
```

## 🆘 Need Help?

- **Documentation**: Check this README and inline code comments
- **Issues**: Check database files and log outputs  
- **Performance**: Use the performance monitor tool
- **Custom needs**: Modify spider settings and configurations