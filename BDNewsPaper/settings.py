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
    "BDNewsPaper.middlewares.StatisticsMiddleware": 450,  # Statistics tracking
    "BDNewsPaper.middlewares.RateLimitMiddleware": 500,  # Rate limiting
    "BDNewsPaper.middlewares.BdnewspaperDownloaderMiddleware": 543,  # Enhanced downloader
    "BDNewsPaper.middlewares.SmartRetryMiddleware": 550,  # Smart retry with backoff
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,  # Disable default retry
}

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
    "BDNewsPaper.pipelines.SharedSQLitePipeline": 300,
}

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

# Rate Limiting Configuration
RATELIMIT_DELAY = 1.0
RATELIMIT_RANDOMIZE = True
