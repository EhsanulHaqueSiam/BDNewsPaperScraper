"""
Stealth Headers Middleware
==========================
Anti-bot evasion through realistic browser header mimicry.

Features:
    - Rotate User-Agents with realistic browser distributions
    - Proper header ordering (Chrome-like)
    - Accept-Language with locale variations
    - Sec-CH-* Client Hints for modern browsers
    - Referer policy management

Settings:
    - STEALTH_HEADERS_ENABLED: Enable/disable (default: True)
    - STEALTH_BROWSER_TYPE: chrome, firefox, safari (default: chrome)
"""

import random
import logging
from typing import Dict, List, Optional

from scrapy import signals
from scrapy.http import Request
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


# Realistic User-Agent strings for different browsers
USER_AGENTS = {
    'chrome': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ],
    'firefox': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ],
    'safari': [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    ],
}

# Accept-Language variations
ACCEPT_LANGUAGES = [
    'en-US,en;q=0.9',
    'en-GB,en;q=0.9,en-US;q=0.8',
    'en-US,en;q=0.9,bn;q=0.8',  # English with Bengali
    'bn-BD,bn;q=0.9,en-US;q=0.8,en;q=0.7',  # Bengali (Bangladesh) primary
]


class StealthHeadersMiddleware:
    """
    Middleware that applies realistic browser headers to requests.
    
    Mimics real browser behavior to avoid bot detection.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        browser_type: str = 'chrome',
        rotate_ua: bool = True,
    ):
        self.enabled = enabled
        self.browser_type = browser_type
        self.rotate_ua = rotate_ua
        self.user_agents = USER_AGENTS.get(browser_type, USER_AGENTS['chrome'])
        self.current_ua = random.choice(self.user_agents)
        
        self.stats = {
            'requests_modified': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('STEALTH_HEADERS_ENABLED', True)
        if not enabled:
            raise NotConfigured("Stealth headers disabled")
        
        middleware = cls(
            enabled=True,
            browser_type=crawler.settings.get('STEALTH_BROWSER_TYPE', 'chrome'),
            rotate_ua=crawler.settings.getbool('STEALTH_ROTATE_UA', True),
        )
        
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def _get_chrome_headers(self, request: Request) -> Dict[str, str]:
        """Generate Chrome-like headers in proper order."""
        ua = random.choice(self.user_agents) if self.rotate_ua else self.current_ua
        
        headers = {
            # Order matters for Chrome fingerprinting
            'Host': self._get_host(request.url),
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        }
        
        return headers
    
    def _get_firefox_headers(self, request: Request) -> Dict[str, str]:
        """Generate Firefox-like headers."""
        ua = random.choice(self.user_agents) if self.rotate_ua else self.current_ua
        
        headers = {
            'Host': self._get_host(request.url),
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice(ACCEPT_LANGUAGES),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        return headers
    
    def _get_host(self, url: str) -> str:
        """Extract host from URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Apply stealth headers to request."""
        if not self.enabled:
            return None
        
        # Skip if already has custom headers set
        if request.meta.get('_stealth_headers_applied'):
            return None
        
        # Get appropriate headers
        if self.browser_type == 'firefox':
            headers = self._get_firefox_headers(request)
        else:
            headers = self._get_chrome_headers(request)
        
        # Apply headers
        for key, value in headers.items():
            if key.lower() not in [h.lower() for h in request.headers.keys()]:
                request.headers[key] = value
        
        request.meta['_stealth_headers_applied'] = True
        self.stats['requests_modified'] += 1
        
        return None
    
    def spider_closed(self, spider, reason):
        """Log stealth headers statistics."""
        if self.stats['requests_modified'] > 0:
            spider.logger.info(
                f"Stealth Headers: Modified {self.stats['requests_modified']} requests"
            )
