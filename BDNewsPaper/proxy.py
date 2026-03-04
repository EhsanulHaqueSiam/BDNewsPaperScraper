"""
Proxy Configuration & Middleware
=================================
Support for various proxy types including rotating, residential, and VPN proxies.

Supported Proxy Types:
    - Single static proxy
    - Rotating proxy lists
    - Residential proxy services (Bright Data, Oxylabs, etc.)
    - SOCKS5 proxies (for VPN)
    - Authenticated proxies

Configuration:
    Set via environment variables, .env file, or scrapy settings.

Environment Variables:
    PROXY_ENABLED=true
    PROXY_TYPE=rotating          # single, rotating, residential, socks5
    PROXY_URL=http://user:pass@proxy.example.com:8080
    PROXY_LIST=/path/to/proxies.txt
    PROXY_ROTATION=round_robin   # round_robin, random, smart
    
Usage in spider:
    scrapy crawl prothomalo -s PROXY_ENABLED=true -s PROXY_URL=http://proxy:8080
"""

import os
import random
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from scrapy import signals
from scrapy.http import Request
from scrapy.exceptions import NotConfigured


logger = logging.getLogger(__name__)


class ProxyConfig:
    """Proxy configuration manager."""
    
    def __init__(self, settings: Dict[str, Any] = None):
        self.settings = settings or {}
        self._load_config()
    
    def _load_config(self):
        """Load proxy configuration from settings/environment."""
        # Priority: settings > env > defaults
        self.enabled = self._get("PROXY_ENABLED", "false").lower() == "true"
        self.proxy_type = self._get("PROXY_TYPE", "single")  # single, rotating, residential, socks5
        self.proxy_url = self._get("PROXY_URL", "")
        self.proxy_list_file = self._get("PROXY_LIST", "")
        self.rotation_strategy = self._get("PROXY_ROTATION", "round_robin")  # round_robin, random, smart
        
        # Authentication
        self.proxy_user = self._get("PROXY_USER", "")
        self.proxy_pass = self._get("PROXY_PASS", "")
        
        # Residential proxy services
        self.residential_provider = self._get("RESIDENTIAL_PROVIDER", "")  # brightdata, oxylabs, smartproxy
        self.residential_country = self._get("RESIDENTIAL_COUNTRY", "bd")  # Bangladesh
        self.residential_session = self._get("RESIDENTIAL_SESSION", "")
        
        # SOCKS5 (VPN)
        self.socks5_host = self._get("SOCKS5_HOST", "")
        self.socks5_port = self._get("SOCKS5_PORT", "1080")
        
        # Retry settings
        self.max_retries = int(self._get("PROXY_MAX_RETRIES", "3"))
        self.ban_threshold = int(self._get("PROXY_BAN_THRESHOLD", "5"))
        
        # Load proxy list
        self.proxies = self._load_proxy_list()
    
    def _get(self, key: str, default: str) -> str:
        """Get value from settings or environment."""
        if self.settings and key in self.settings:
            return str(self.settings.get(key, default))
        return os.getenv(key, default)
    
    def _load_proxy_list(self) -> List[str]:
        """Load proxy list from file or single proxy."""
        proxies = []
        
        if self.proxy_list_file and Path(self.proxy_list_file).exists():
            with open(self.proxy_list_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        proxies.append(self._normalize_proxy(line))
            logger.info(f"Loaded {len(proxies)} proxies from {self.proxy_list_file}")
        
        elif self.proxy_url:
            proxies.append(self._normalize_proxy(self.proxy_url))
        
        return proxies
    
    def _normalize_proxy(self, proxy: str) -> str:
        """Normalize proxy URL format."""
        if not proxy.startswith(("http://", "https://", "socks5://")):
            proxy = f"http://{proxy}"
        return proxy
    
    def get_residential_proxy(self) -> str:
        """Build residential proxy URL for supported providers."""
        provider = self.residential_provider.lower()
        country = self.residential_country
        user = self.proxy_user
        password = self.proxy_pass
        session = self.residential_session or random.randint(100000, 999999)
        
        if provider == "brightdata":
            # Bright Data (Luminati) format
            return f"http://{user}-country-{country}-session-{session}:{password}@brd.superproxy.io:22225"
        
        elif provider == "oxylabs":
            # Oxylabs format
            return f"http://{user}:{password}@pr.oxylabs.io:7777"
        
        elif provider == "smartproxy":
            # Smartproxy format
            return f"http://{user}:{password}@gate.smartproxy.com:7000"
        
        elif provider == "webshare":
            # Webshare format
            return f"http://{user}:{password}@p.webshare.io:80"
        
        else:
            # Generic format
            return self.proxy_url
    
    def get_socks5_proxy(self) -> str:
        """Build SOCKS5 proxy URL (for VPN connections)."""
        host = self.socks5_host
        port = self.socks5_port
        
        if self.proxy_user and self.proxy_pass:
            return f"socks5://{self.proxy_user}:{self.proxy_pass}@{host}:{port}"
        return f"socks5://{host}:{port}"


class ProxyMiddleware:
    """
    Scrapy middleware for proxy support.
    
    Features:
    - Multiple proxy types (single, rotating, residential, SOCKS5)
    - Automatic rotation strategies
    - Failed proxy tracking
    - Ban detection
    """
    
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.proxies = list(config.proxies)
        self.current_index = 0
        self.failed_proxies: Dict[str, int] = {}
        self.banned_proxies: set = set()
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        settings = {
            key: crawler.settings.get(key)
            for key in crawler.settings.attributes.keys()
        }
        config = ProxyConfig(settings)
        
        if not config.enabled:
            raise NotConfigured("Proxy not enabled")
        
        middleware = cls(config)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware
    
    def spider_opened(self, spider):
        """Log proxy configuration when spider starts."""
        logger.info(f"Proxy middleware enabled: type={self.config.proxy_type}, "
                   f"strategy={self.config.rotation_strategy}, "
                   f"proxies={len(self.proxies)}")
    
    def process_request(self, request: Request, spider):
        """Add proxy to request."""
        # Skip if already has proxy
        if 'proxy' in request.meta:
            return
        
        proxy = self._get_proxy()
        
        if proxy:
            request.meta['proxy'] = proxy
            logger.debug(f"Using proxy: {self._mask_proxy(proxy)}")
    
    def process_response(self, request, response, spider):
        """Handle response and track proxy performance."""
        proxy = request.meta.get('proxy')
        
        if proxy:
            # Reset failure count on success
            if proxy in self.failed_proxies:
                self.failed_proxies[proxy] = max(0, self.failed_proxies[proxy] - 1)
            
            # Check for ban indicators
            if self._is_banned_response(response):
                self._mark_proxy_failed(proxy)
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Handle proxy connection failures."""
        proxy = request.meta.get('proxy')
        
        if proxy:
            self._mark_proxy_failed(proxy)
            logger.warning(f"Proxy failed: {self._mask_proxy(proxy)} - {exception}")
            
            # Retry with different proxy
            if request.meta.get('proxy_retry_count', 0) < self.config.max_retries:
                new_request = request.copy()
                new_request.meta['proxy_retry_count'] = request.meta.get('proxy_retry_count', 0) + 1
                new_request.meta.pop('proxy', None)  # Get new proxy
                new_request.dont_filter = True
                return new_request
    
    def _get_proxy(self) -> Optional[str]:
        """Get next proxy based on configuration."""
        proxy_type = self.config.proxy_type.lower()
        
        if proxy_type == "residential":
            return self.config.get_residential_proxy()
        
        elif proxy_type == "socks5":
            return self.config.get_socks5_proxy()
        
        elif proxy_type in ("rotating", "list"):
            return self._get_rotating_proxy()
        
        elif proxy_type == "single" and self.proxies:
            return self.proxies[0]
        
        return None
    
    def _get_rotating_proxy(self) -> Optional[str]:
        """Get next proxy using rotation strategy."""
        available = [p for p in self.proxies if p not in self.banned_proxies]
        
        if not available:
            logger.error("No available proxies!")
            # Reset banned proxies as last resort
            self.banned_proxies.clear()
            available = self.proxies
        
        if not available:
            return None
        
        strategy = self.config.rotation_strategy.lower()
        
        if strategy == "random":
            return random.choice(available)
        
        elif strategy == "smart":
            # Prefer proxies with fewer failures
            sorted_proxies = sorted(available, key=lambda p: self.failed_proxies.get(p, 0))
            return sorted_proxies[0]
        
        else:  # round_robin
            self.current_index = (self.current_index + 1) % len(available)
            return available[self.current_index]
    
    def _mark_proxy_failed(self, proxy: str):
        """Track proxy failure and ban if threshold exceeded."""
        self.failed_proxies[proxy] = self.failed_proxies.get(proxy, 0) + 1
        
        if self.failed_proxies[proxy] >= self.config.ban_threshold:
            self.banned_proxies.add(proxy)
            logger.warning(f"Proxy banned: {self._mask_proxy(proxy)}")
    
    def _is_banned_response(self, response) -> bool:
        """Check if response indicates proxy ban."""
        # Common ban indicators
        ban_status_codes = [403, 407, 429, 503]
        ban_texts = ['blocked', 'banned', 'captcha', 'access denied', 'too many requests']
        
        if response.status in ban_status_codes:
            return True
        
        body_lower = response.text[:1000].lower() if hasattr(response, 'text') else ''
        return any(text in body_lower for text in ban_texts)
    
    def _mask_proxy(self, proxy: str) -> str:
        """Mask proxy credentials for logging."""
        try:
            parsed = urlparse(proxy)
            if parsed.password:
                return proxy.replace(parsed.password, "***")
        except:
            pass
        return proxy


# =============================================================================
# Scrapy Settings Integration
# =============================================================================

PROXY_SETTINGS = {
    # Enable proxy middleware
    'PROXY_ENABLED': False,
    
    # Proxy type: single, rotating, residential, socks5
    'PROXY_TYPE': 'single',
    
    # Single proxy or list file
    'PROXY_URL': '',
    'PROXY_LIST': '',
    
    # Rotation strategy: round_robin, random, smart
    'PROXY_ROTATION': 'round_robin',
    
    # Authentication
    'PROXY_USER': '',
    'PROXY_PASS': '',
    
    # Residential proxy provider
    'RESIDENTIAL_PROVIDER': '',  # brightdata, oxylabs, smartproxy
    'RESIDENTIAL_COUNTRY': 'bd',
    
    # SOCKS5/VPN
    'SOCKS5_HOST': '',
    'SOCKS5_PORT': '1080',
    
    # Retry settings
    'PROXY_MAX_RETRIES': 3,
    'PROXY_BAN_THRESHOLD': 5,
}


# =============================================================================
# CLI Tool
# =============================================================================

def main():
    """CLI for proxy testing and configuration."""
    import argparse
    import requests
    
    parser = argparse.ArgumentParser(description="Proxy configuration and testing")
    parser.add_argument("--test", help="Test a proxy URL")
    parser.add_argument("--test-list", help="Test proxies from file")
    parser.add_argument("--generate-config", action="store_true", help="Generate sample .env config")
    
    args = parser.parse_args()
    
    if args.generate_config:
        config = """# Proxy Configuration for BDNewsPaperScraper

# Enable proxy support
PROXY_ENABLED=true

# Proxy type: single, rotating, residential, socks5
PROXY_TYPE=single

# Single proxy URL (format: http://user:pass@host:port)
PROXY_URL=

# Proxy list file (one per line)
PROXY_LIST=proxies.txt

# Rotation strategy: round_robin, random, smart
PROXY_ROTATION=round_robin

# Authentication (if not in URL)
PROXY_USER=
PROXY_PASS=

# Residential Proxy Provider
# Supported: brightdata, oxylabs, smartproxy, webshare
RESIDENTIAL_PROVIDER=
RESIDENTIAL_COUNTRY=bd

# SOCKS5 / VPN
SOCKS5_HOST=127.0.0.1
SOCKS5_PORT=1080

# Retry settings
PROXY_MAX_RETRIES=3
PROXY_BAN_THRESHOLD=5
"""
        with open(".env.proxy", "w") as f:
            f.write(config)
        print("✅ Generated .env.proxy configuration file")
        
    elif args.test:
        print(f"Testing proxy: {args.test}")
        try:
            response = requests.get(
                "https://httpbin.org/ip",
                proxies={"http": args.test, "https": args.test},
                timeout=10
            )
            print(f"✅ Proxy working! IP: {response.json().get('origin')}")
        except Exception as e:
            print(f"❌ Proxy failed: {e}")
    
    elif args.test_list:
        print(f"Testing proxies from: {args.test_list}")
        with open(args.test_list) as f:
            proxies = [line.strip() for line in f if line.strip()]
        
        working = 0
        for proxy in proxies:
            try:
                response = requests.get(
                    "https://httpbin.org/ip",
                    proxies={"http": proxy, "https": proxy},
                    timeout=10
                )
                print(f"✅ {proxy[:50]}... - IP: {response.json().get('origin')}")
                working += 1
            except:
                print(f"❌ {proxy[:50]}...")
        
        print(f"\nResults: {working}/{len(proxies)} working")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
