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


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 64

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 0.5  # Reduced delay for faster scraping
RANDOMIZE_DOWNLOAD_DELAY = True
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_IP = 16

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
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,  # Disable default
    "BDNewsPaper.middlewares.UserAgentMiddleware": 400,  # Custom User-Agent rotation
    "BDNewsPaper.proxy.ProxyMiddleware": 410,  # Proxy rotation (optional - enable via PROXY_ENABLED)
    "BDNewsPaper.middlewares.CircuitBreakerMiddleware": 420,  # Circuit breaker (before stats)
    "BDNewsPaper.middlewares.StatisticsMiddleware": 450,  # Statistics tracking
    "BDNewsPaper.middlewares.RateLimitMiddleware": 500,  # Rate limiting
    "BDNewsPaper.middlewares.BdnewspaperDownloaderMiddleware": 543,  # Enhanced downloader
    "BDNewsPaper.middlewares.SmartRetryMiddleware": 550,  # Smart retry with backoff
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,  # Disable default retry
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
    "BDNewsPaper.pipelines.ValidationPipeline": 100,
    "BDNewsPaper.pipelines.CleanArticlePipeline": 200,
    "BDNewsPaper.pipelines.LanguageDetectionPipeline": 210,  # Language detection
    "BDNewsPaper.pipelines.ContentQualityPipeline": 220,  # Content quality check
    "BDNewsPaper.pipelines.DateFilterPipeline": 250,  # Optional date filtering
    "BDNewsPaper.pipelines.SharedSQLitePipeline": 300,
}

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
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600  # Cache for 1 hour (reduced from 24h)
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 429]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

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
