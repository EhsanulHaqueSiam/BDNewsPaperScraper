# Scrapy settings for BDNewsPaper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "BDNewsPaper"

SPIDER_MODULES = ["BDNewsPaper.spiders"]
NEWSPIDER_MODULE = "BDNewsPaper.spiders"

# =============================================================================
# PLAYWRIGHT CONFIGURATION
# =============================================================================
# Enable Playwright for JavaScript rendering and Cloudflare bypass
# 
# IMPORTANT: Do NOT set global DOWNLOAD_HANDLERS for Playwright!
# This would route ALL requests through Playwright and break HTTP spiders
# (causes "Response content isn't text" error).
#
# Instead, Playwright is activated per-request when spider sets:
#   meta={'playwright': True}
#
# The scrapy-playwright handler is automatically available when installed.
# See: https://github.com/scrapy-plugins/scrapy-playwright

# Playwright launch options (used when playwright=True in request meta)
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ],
}

# Playwright context options
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "locale": "en-US",
        "timezone_id": "Asia/Dhaka",
        "ignore_https_errors": True,
    },
}

# Twisted reactor for async Playwright
# NOTE: Only uncomment when running Playwright spiders specifically.
# Having this enabled globally can interfere with normal HTTP spiders.
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"



# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 64

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 0.5  # Reduced delay for faster scraping
RANDOMIZE_DOWNLOAD_DELAY = True
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16  # Disabled: incompatible with Scrapy 2.14's DownloaderAwarePriorityQueue

# Download timeout (seconds) - increased for slow Bangladesh news sites
DOWNLOAD_TIMEOUT = 180  # 3 minutes for slow Bangladesh news sites

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    "BDNewsPaper.middlewares.BdnewspaperSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # Disable default middlewares we're replacing
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    
    # === ROBUSTNESS LAYER 1: Request Preparation (300-450) ===
    "BDNewsPaper.stealth_headers.StealthHeadersMiddleware": 350,       # Anti-bot headers
    "BDNewsPaper.middlewares.UserAgentMiddleware": 400,                # UA rotation backup
    "BDNewsPaper.proxy.ProxyMiddleware": 410,                          # Proxy rotation
    "BDNewsPaper.cloudflare_bypass.CloudflareBypassMiddleware": 430,   # CF bypass (all levels)
    
    # === ROBUSTNESS LAYER 2: Traffic Control (450-550) ===
    "BDNewsPaper.middlewares.CircuitBreakerMiddleware": 451,           # Circuit breaker
    "BDNewsPaper.middlewares.StatisticsMiddleware": 460,               # Statistics tracking
    "BDNewsPaper.middlewares.AdaptiveThrottlingMiddleware": 470,       # Dynamic throttling
    "BDNewsPaper.middlewares.RateLimitMiddleware": 500,                # Rate limiting
    
    # === ROBUSTNESS LAYER 3: Request Processing (550-650) ===
    "BDNewsPaper.hybrid_request.HybridRequestMiddleware": 540,         # Auto HTTP/Playwright
    "BDNewsPaper.middlewares.BdnewspaperDownloaderMiddleware": 543,    # Enhanced downloader
    "BDNewsPaper.middlewares.SmartRetryMiddleware": 550,               # Smart retry
    "BDNewsPaper.honeypot.HoneypotDetectionMiddleware": 560,           # Honeypot detection
    
    # === ROBUSTNESS LAYER 4: Response Fallbacks (650+) ===
    "BDNewsPaper.middlewares.ArchiveFallbackMiddleware": 650,          # Wayback fallback
}

# =============================================================================
# Proxy Configuration (Optional)
# =============================================================================
# Enable to use proxies. Set PROXY_ENABLED=true via env or command line.
# See BDNewsPaper/proxy.py for full documentation.

# Enable proxy middleware
PROXY_ENABLED = False  # Set True to enable, or via -s PROXY_ENABLED=true

# Proxy type: single, rotating, residential, socks5
PROXY_TYPE = 'single'

# Single proxy URL (format: http://user:pass@host:port)
PROXY_URL = ''

# Proxy list file (one per line for rotating)
PROXY_LIST = ''

# Rotation strategy: round_robin, random, smart
PROXY_ROTATION = 'round_robin'

# Authentication (if not in URL)
PROXY_USER = ''
PROXY_PASS = ''

# Residential proxy provider: brightdata, oxylabs, smartproxy, webshare
RESIDENTIAL_PROVIDER = ''
RESIDENTIAL_COUNTRY = 'bd'

# SOCKS5 / VPN configuration
SOCKS5_HOST = '127.0.0.1'
SOCKS5_PORT = '1080'

# Proxy retry settings
PROXY_MAX_RETRIES = 3
PROXY_BAN_THRESHOLD = 5

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    # === ROBUSTNESS: Content Extraction Fallback ===
    "BDNewsPaper.pipelines.FallbackExtractionPipeline": 50,  # Try rescue before validation
    
    # === Standard Processing Pipeline ===
    "BDNewsPaper.pipelines.ValidationPipeline": 100,
    "BDNewsPaper.pipelines.CleanArticlePipeline": 200,
    "BDNewsPaper.pipelines.LanguageDetectionPipeline": 210,  # Language detection
    "BDNewsPaper.pipelines.ContentQualityPipeline": 220,  # Content quality check
    "BDNewsPaper.pipelines.DateFilterPipeline": 250,  # Optional date filtering
    "BDNewsPaper.pipelines.SharedSQLitePipeline": 300,
    
    # === PostgreSQL Pipeline (enable for production) ===
    # "BDNewsPaper.postgres_pipeline.PostgreSQLPipeline": 310,  # Uncomment for PostgreSQL
}

# =============================================================================
# PostgreSQL Database Configuration (for production scale)
# =============================================================================
import os

# Database Selection: 'sqlite' or 'postgresql'
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'sqlite')

# PostgreSQL Configuration (via environment variables)
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', '5432'))
POSTGRES_DATABASE = os.environ.get('POSTGRES_DATABASE', 'bdnews')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'bdnews')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'bdnews_password')

# Connection pool settings
POSTGRES_POOL_MIN = int(os.environ.get('POSTGRES_POOL_MIN', '2'))
POSTGRES_POOL_MAX = int(os.environ.get('POSTGRES_POOL_MAX', '10'))

# SQLite Configuration (default for development)
SQLITE_DATABASE = os.environ.get('SQLITE_DATABASE', 'news_articles.db')

# Date filter settings (disabled by default, enabled per-spider)
DATE_FILTER_ENABLED = False
# FILTER_START_DATE = '2024-01-01'
# FILTER_END_DATE = '2024-12-31'

# Language Detection settings
LANGUAGE_DETECTION_ENABLED = True
LANGUAGE_DETECTION_STRICT = False  # Set True to drop non-English articles
EXPECTED_LANGUAGES = ['en']  # Expected article languages

# Content Quality settings
MIN_ARTICLE_WORDS = 20
MAX_ARTICLE_WORDS = 50000
MAX_SPECIAL_CHAR_RATIO = 0.3

# Checkpoint settings
CHECKPOINT_ENABLED = False  # Enable to save progress periodically
CHECKPOINT_INTERVAL = 100  # Items between checkpoints
CHECKPOINT_DIR = '.checkpoints'

# Database settings
DATABASE_PATH = 'news_articles.db'

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.1  # Very fast initial delay  
AUTOTHROTTLE_MAX_DELAY = 3.0    # Reduced max delay
AUTOTHROTTLE_TARGET_CONCURRENCY = 16.0  # Higher concurrency for speed
AUTOTHROTTLE_DEBUG = False  # Disable debug for production

# Configure concurrent requests settings (optimized for speed)
CONCURRENT_REQUESTS = 64
CONCURRENT_REQUESTS_PER_DOMAIN = 16

# Disable cookies (to avoid tracking)
COOKIES_ENABLED = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Enable HTTP caching to minimize duplicate requests
# HTTPCACHE_ENABLED = True
HTTPCACHE_ENABLED = False
# HTTPCACHE_EXPIRATION_SECS = 3600  # Cache for 1 hour (reduced from 24h)
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 429]
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# DNS resolver optimization
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000

# Enable compression to reduce bandwidth
COMPRESSION_ENABLED = True

# Memory usage optimization
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048
MEMUSAGE_WARNING_MB = 1024

# Log level for better performance monitoring
LOG_LEVEL = 'INFO'
LOG_FILE = 'scrapy.log'

# Request fingerprinting for better deduplication
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Enhanced Middleware Settings
# Smart Retry Configuration
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_BACKOFF_FACTOR = 2.0
RETRY_MAX_DELAY = 60.0
RETRY_JITTER_FACTOR = 0.3  # Random jitter to prevent thundering herd

# Circuit Breaker Configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # Failures before opening circuit
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60.0  # Seconds before trying recovery
CIRCUIT_BREAKER_HALF_OPEN_CALLS = 3  # Successful calls to close circuit

# Rate Limiting Configuration
RATELIMIT_DELAY = 1.0
RATELIMIT_RANDOMIZE = True

# =============================================================================
# ROBUSTNESS FEATURES CONFIGURATION
# =============================================================================
# All features below are ENABLED by default for maximum robustness.
# Disable individual features by setting their *_ENABLED flag to False.

# -----------------------------------------------------------------------------
# 1. SMART FALLBACK EXTRACTION (extractors.py, pipelines.py)
# -----------------------------------------------------------------------------
# When spider selectors fail, try fallback extraction methods.
FALLBACK_EXTRACTION_ENABLED = True
FALLBACK_MIN_BODY_LENGTH = 50  # Trigger fallback if body shorter than this

# -----------------------------------------------------------------------------
# 2. HYBRID REQUEST ENGINE (hybrid_request.py)  
# -----------------------------------------------------------------------------
# Automatically switch from HTTP to Playwright when JS challenges detected.
HYBRID_REQUEST_ENABLED = True
HYBRID_MAX_RETRIES = 2  # Max Playwright retries per URL
HYBRID_PLAYWRIGHT_DOMAINS = [
    # Domains that always need Playwright (known CF-protected)
    'daily-sun.com',
]

# -----------------------------------------------------------------------------
# 4. ANTI-BOT EVASION (stealth_headers.py)
# -----------------------------------------------------------------------------
# Realistic browser headers to avoid bot detection.
STEALTH_HEADERS_ENABLED = True
STEALTH_BROWSER_TYPE = 'chrome'  # chrome, firefox, safari
STEALTH_ROTATE_UA = True  # Rotate User-Agent per request

# -----------------------------------------------------------------------------
# 9. CLOUDFLARE BYPASS - FULL IMPLEMENTATION (cloudflare_bypass.py)
# -----------------------------------------------------------------------------
# 7-Level Cloudflare countermeasures system.
# 
# LEVELS:
#   1. Stealth Headers (stealth_headers.py)
#   2. Stealth Playwright (comprehensive JS injection)
#   3. Cookie Management (cf_clearance caching)
#   4. Flaresolverr Integration (Docker solver)
#   5. TLS Fingerprinting (curl_cffi Chrome mimicry)
#   6. Challenge Detection (automatic identification)
#   7. Progressive Escalation (retry with stronger methods)

CF_BYPASS_ENABLED = True
CF_MAX_RETRIES = 3  # Max escalation attempts per URL

CF_PROTECTED_DOMAINS = [
    # Major English newspapers
    'thedailystar.net',
    'daily-sun.com',
    'bdnews24.com',
    'dhakatribune.com',
    'newagebd.net',
    'thefinancialexpress.com.bd',
    'observerbd.com',
    'tbsnews.net',
    'unb.com.bd',
    
    # Major Bangla newspapers
    'prothomalo.com',
    'jugantor.com',
    'ittefaq.com.bd',
    'kalerkantho.com',
    'samakal.com',
    'banglatribune.com',
    'jaijaidinbd.com',
    'mzamin.com',
    'jagonews24.com',
    'risingbd.com',
    'nayadiganta.com',
    'bd-pratidin.com',
    'dhakapost.com',
    'barta24.com',
    'bhorer-kagoj.com',
    'amaderbarta.com',
    
    # International Bangla services
    'bbc.com',
    'dw.com',
    'voabangla.com',
]

# Cookie cache file for persistence across runs
CF_COOKIES_FILE = 'config/cf_cookies.json'

# Flaresolverr Docker endpoint (install: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr)
# Uncomment when Flaresolverr is running:
# FLARESOLVERR_URL = 'http://localhost:8191/v1'

# TLS fingerprinting with curl_cffi (install: pip install curl_cffi)
CF_TLS_CLIENT_ENABLED = True  # Uses curl_cffi if available

# -----------------------------------------------------------------------------
# 13. ADAPTIVE THROTTLING (middlewares.py)
# -----------------------------------------------------------------------------
# Dynamic delay adjustment based on server response times.
ADAPTIVE_THROTTLE_ENABLED = True
ADAPTIVE_THROTTLE_THRESHOLD_MS = 500  # Slow response threshold
ADAPTIVE_THROTTLE_INCREASE_FACTOR = 1.5  # Delay multiplier on slow
ADAPTIVE_THROTTLE_DECREASE_FACTOR = 0.9  # Delay multiplier on fast
ADAPTIVE_THROTTLE_MIN_DELAY = 0.5  # Minimum delay (seconds)
ADAPTIVE_THROTTLE_MAX_DELAY = 30.0  # Maximum delay (seconds)
ADAPTIVE_THROTTLE_WINDOW_SIZE = 10  # Rolling window for avg calculation

# -----------------------------------------------------------------------------
# ARCHIVE FALLBACK (middlewares.py)
# -----------------------------------------------------------------------------
# Query Wayback Machine for 404/403 pages.
ARCHIVE_FALLBACK_ENABLED = True
ARCHIVE_FALLBACK_CODES = [404, 403, 410]
ARCHIVE_FALLBACK_TIMEOUT = 10

# -----------------------------------------------------------------------------
# HONEYPOT DETECTION (honeypot.py)
# -----------------------------------------------------------------------------
# Avoid anti-bot trap links.
# DISABLED by default - news listing pages often have 200+ legitimate links
HONEYPOT_DETECTION_ENABLED = False

# -----------------------------------------------------------------------------
# VALIDATION PIPELINE (pipelines.py)
# -----------------------------------------------------------------------------
# Set to False for debugging (logs warnings instead of dropping items)
VALIDATION_STRICT_MODE = True

# -----------------------------------------------------------------------------
# 4. ANTI-BOT EVASION (antibot.py)
# -----------------------------------------------------------------------------
# Advanced browser fingerprint randomization.
ANTIBOT_ENABLED = True
ANTIBOT_CANVAS_NOISE = True      # Randomize canvas fingerprint
ANTIBOT_WEBGL_NOISE = True       # Randomize WebGL vendor/renderer
ANTIBOT_AUDIO_NOISE = True       # Audio context fingerprint protection
ANTIBOT_SCREEN_RANDOM = True     # Screen resolution randomization
ANTIBOT_LOCALE_CONSISTENCY = True  # Timezone/language consistency
ANTIBOT_HARDWARE_RANDOM = True   # CPU cores, RAM randomization
ANTIBOT_PLUGIN_SIMULATION = True # Plugin/MIME type simulation
ANTIBOT_WEBRTC_PROTECTION = True # WebRTC leak prevention

# -----------------------------------------------------------------------------
# 7. GEOGRAPHIC MIMICRY (geo_mimicry.py)
# -----------------------------------------------------------------------------
# Bangladesh-specific proxy and geo-location features.
GEO_MIMICRY_ENABLED = False  # Enable when you have proxy credentials

# Proxy provider: 'brightdata', 'oxylabs', 'smartproxy', or 'custom'
GEO_PROXY_PROVIDER = 'brightdata'

# Provider credentials (set via environment variables for security)
# GEO_PROXY_USER = ''
# GEO_PROXY_PASS = ''

# Custom proxy URL (if using 'custom' provider)
# GEO_PROXY_URL = 'http://user:pass@proxy.example.com:port'

# Domains that need Bangladesh IP
GEO_DOMAINS = [
    # Add domains that serve different content for BD IPs
]

# Retry with new IP on geo-block detection
GEO_RETRY_ON_BLOCK = True
