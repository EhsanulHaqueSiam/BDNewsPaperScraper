"""
Hybrid Request Engine Middleware
================================
Automatically switches between fast HTTP and browser-based requests.

Strategy:
    1. Start with fast httpx/requests (default)
    2. On 403/429/JS-challenge detection → auto-switch to Playwright
    3. Learn which domains need browser rendering

Settings:
    - HYBRID_REQUEST_ENABLED: Enable/disable (default: True)
    - HYBRID_PLAYWRIGHT_DOMAINS: List of domains that always use Playwright
    - HYBRID_CHALLENGE_PATTERNS: Patterns that trigger Playwright switch
"""

import re
import logging
from collections import defaultdict
from typing import Set, List, Optional, Dict

from scrapy import signals
from scrapy.http import Request, Response, HtmlResponse
from scrapy.exceptions import NotConfigured, IgnoreRequest

logger = logging.getLogger(__name__)


class HybridRequestMiddleware:
    """
    Middleware that switches between HTTP and Playwright based on response.
    
    Detects JavaScript challenges and Cloudflare protection, then
    automatically retries with Playwright for affected domains.
    """
    
    # Patterns indicating JS challenge or protection
    DEFAULT_CHALLENGE_PATTERNS = [
        r'<title>Just a moment\.\.\.</title>',  # Cloudflare
        r'_cf_chl_opt',  # Cloudflare challenge
        r'challenge-platform',
        r'Checking your browser',
        r'Please enable JavaScript',
        r'needs JavaScript',
        r'turnstile',  # Cloudflare Turnstile
        r'hcaptcha',
        r'Please wait while we verify',
    ]
    
    def __init__(
        self,
        enabled: bool = True,
        playwright_domains: List[str] = None,
        challenge_patterns: List[str] = None,
        max_retries: int = 2,
    ):
        self.enabled = enabled
        self.playwright_domains: Set[str] = set(playwright_domains or [])
        self.max_retries = max_retries
        
        # Compile challenge patterns
        patterns = challenge_patterns or self.DEFAULT_CHALLENGE_PATTERNS
        self.challenge_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Track domains that need Playwright
        self.learned_playwright_domains: Set[str] = set()
        
        self.stats = {
            'challenges_detected': 0,
            'playwright_switches': 0,
            'domains_learned': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('HYBRID_REQUEST_ENABLED', True)
        if not enabled:
            raise NotConfigured("Hybrid request engine disabled")
        
        middleware = cls(
            enabled=True,
            playwright_domains=crawler.settings.getlist('HYBRID_PLAYWRIGHT_DOMAINS', []),
            challenge_patterns=crawler.settings.getlist('HYBRID_CHALLENGE_PATTERNS', None),
            max_retries=crawler.settings.getint('HYBRID_MAX_RETRIES', 2),
        )
        
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    def _needs_playwright(self, domain: str) -> bool:
        """Check if domain needs Playwright."""
        return (
            domain in self.playwright_domains or
            domain in self.learned_playwright_domains
        )
    
    def _detect_challenge(self, response: Response) -> bool:
        """Detect JavaScript challenge in response."""
        # Check status codes
        if response.status in [403, 429, 503]:
            return True
        
        # Check content length (challenge pages are usually small)
        if len(response.body) < 5000:
            try:
                text = response.text
                for pattern in self.challenge_patterns:
                    if pattern.search(text):
                        return True
            except Exception:
                # Response is not text (e.g., binary response)
                pass
        
        return False
    
    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Add Playwright meta for known domains."""
        if not self.enabled:
            return None
        
        domain = self._get_domain(request.url)
        
        # If domain needs Playwright, add the meta
        if self._needs_playwright(domain) and not request.meta.get('playwright'):
            request.meta['playwright'] = True
            request.meta['playwright_include_page'] = False
            request.meta['_hybrid_playwright'] = True
            spider.logger.debug(f"Hybrid: Using Playwright for {domain}")
        
        return None
    
    def process_response(self, request: Request, response: Response, spider) -> Response:
        """Check for challenges and retry with Playwright if needed."""
        if not self.enabled:
            return response
        
        # Skip if already using Playwright
        if request.meta.get('playwright') or request.meta.get('_hybrid_playwright'):
            return response
        
        domain = self._get_domain(request.url)
        
        # Detect challenge
        if self._detect_challenge(response):
            self.stats['challenges_detected'] += 1
            
            # Check retry count
            retries = request.meta.get('_hybrid_retries', 0)
            if retries >= self.max_retries:
                spider.logger.warning(f"Hybrid: Max retries reached for {request.url}")
                return response
            
            # Learn this domain needs Playwright
            if domain not in self.learned_playwright_domains:
                self.learned_playwright_domains.add(domain)
                self.stats['domains_learned'] += 1
                spider.logger.info(f"Hybrid: Learned {domain} needs Playwright")
            
            # Create new request with Playwright
            self.stats['playwright_switches'] += 1
            spider.logger.info(f"Hybrid: Switching to Playwright for {request.url}")
            
            new_request = request.replace(
                meta={
                    **request.meta,
                    'playwright': True,
                    'playwright_include_page': False,
                    '_hybrid_playwright': True,
                    '_hybrid_retries': retries + 1,
                },
                dont_filter=True,
            )
            
            return new_request
        
        return response
    
    def spider_closed(self, spider, reason):
        """Log hybrid request statistics."""
        if self.stats['challenges_detected'] > 0:
            spider.logger.info(
                f"Hybrid Request Stats: "
                f"ChallengesDetected={self.stats['challenges_detected']}, "
                f"PlaywrightSwitches={self.stats['playwright_switches']}, "
                f"DomainsLearned={self.stats['domains_learned']}"
            )
            
            if self.learned_playwright_domains:
                spider.logger.info(
                    f"Domains needing Playwright: {', '.join(self.learned_playwright_domains)}"
                )
