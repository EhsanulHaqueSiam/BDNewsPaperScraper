"""
Cloudflare Bypass Module
========================
Multi-level Cloudflare countermeasures for protected sites.

Levels:
    1. Stealth Headers (already in stealth_headers.py)
    2. Stealth Playwright (automation hiding)
    3. Flaresolverr Integration (Docker solver)
    4. Cookie Injection (manual cf_clearance)

Usage:
    from BDNewsPaper.cloudflare_bypass import (
        get_flaresolverr_cookies,
        get_stealth_playwright_args,
        CloudflareCookieMiddleware,
    )

Settings:
    - FLARESOLVERR_URL: Flaresolverr endpoint (default: http://localhost:8191/v1)
    - CF_COOKIES_FILE: Path to cookies JSON file
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    import requests as httpx
    HTTPX_AVAILABLE = False

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


# Stealth Playwright arguments to hide automation
STEALTH_PLAYWRIGHT_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-infobars',
    '--disable-extensions',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--window-size=1920,1080',
]

# Stealth JavaScript to inject
STEALTH_JS = """
// Remove webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Fake plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Fake languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en', 'bn'],
});

// Override permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""


def get_stealth_playwright_args() -> List[str]:
    """Get Playwright launch arguments for stealth mode."""
    return STEALTH_PLAYWRIGHT_ARGS.copy()


def get_stealth_js() -> str:
    """Get JavaScript to inject for hiding automation."""
    return STEALTH_JS


@dataclass
class FlaresolverrResponse:
    """Response from Flaresolverr."""
    status: str
    message: str
    solution: Optional[Dict[str, Any]] = None
    
    @property
    def cookies(self) -> Dict[str, str]:
        """Extract cookies from solution."""
        if not self.solution:
            return {}
        return {c['name']: c['value'] for c in self.solution.get('cookies', [])}
    
    @property
    def user_agent(self) -> str:
        """Get User-Agent from solution."""
        if not self.solution:
            return ''
        return self.solution.get('userAgent', '')


class FlaresolverrClient:
    """
    Client for Flaresolverr Docker service.
    
    Flaresolverr is a proxy that solves Cloudflare challenges
    and returns the cookies needed to access protected sites.
    
    Install: docker run -d --name=flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr
    """
    
    def __init__(self, url: str = 'http://localhost:8191/v1'):
        self.url = url
        self.session_id = None
    
    def solve(self, target_url: str, timeout: int = 60) -> FlaresolverrResponse:
        """
        Solve Cloudflare challenge for a URL.
        
        Returns cookies and user-agent needed to access the site.
        """
        try:
            response = httpx.post(
                self.url,
                json={
                    'cmd': 'request.get',
                    'url': target_url,
                    'maxTimeout': timeout * 1000,
                },
                timeout=timeout + 10,
            )
            
            data = response.json()
            
            return FlaresolverrResponse(
                status=data.get('status', 'error'),
                message=data.get('message', ''),
                solution=data.get('solution'),
            )
            
        except Exception as e:
            logger.error(f"Flaresolverr error: {e}")
            return FlaresolverrResponse(
                status='error',
                message=str(e),
            )
    
    def create_session(self) -> str:
        """Create a persistent browser session."""
        try:
            response = httpx.post(
                self.url,
                json={'cmd': 'sessions.create'},
                timeout=30,
            )
            data = response.json()
            self.session_id = data.get('session')
            return self.session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return ''
    
    def destroy_session(self):
        """Destroy the browser session."""
        if not self.session_id:
            return
        try:
            httpx.post(
                self.url,
                json={'cmd': 'sessions.destroy', 'session': self.session_id},
                timeout=10,
            )
        except:
            pass


def get_flaresolverr_cookies(
    url: str,
    flaresolverr_url: str = 'http://localhost:8191/v1',
    timeout: int = 60,
) -> Dict[str, str]:
    """
    Get Cloudflare bypass cookies for a URL using Flaresolverr.
    
    Args:
        url: Target URL to solve
        flaresolverr_url: Flaresolverr endpoint
        timeout: Max time to wait for solution
        
    Returns:
        Dictionary of cookies including cf_clearance
    """
    client = FlaresolverrClient(flaresolverr_url)
    response = client.solve(url, timeout)
    
    if response.status == 'ok':
        return response.cookies
    
    logger.warning(f"Flaresolverr failed: {response.message}")
    return {}


class CloudflareCookieMiddleware:
    """
    Middleware that injects Cloudflare bypass cookies.
    
    Can load cookies from:
    1. Flaresolverr (automatic)
    2. JSON file (manual export)
    3. In-memory cache
    
    Settings:
        - CF_BYPASS_ENABLED: Enable/disable (default: True)
        - CF_COOKIES_FILE: Path to cookies JSON
        - FLARESOLVERR_URL: Flaresolverr endpoint
        - CF_PROTECTED_DOMAINS: List of domains needing bypass
    """
    
    def __init__(
        self,
        enabled: bool = True,
        cookies_file: Optional[str] = None,
        flaresolverr_url: Optional[str] = None,
        protected_domains: List[str] = None,
    ):
        self.enabled = enabled
        self.cookies_file = Path(cookies_file) if cookies_file else None
        self.flaresolverr_url = flaresolverr_url
        self.protected_domains = set(protected_domains or [])
        
        # Cookie cache: domain -> {cookies}
        self.cookie_cache: Dict[str, Dict[str, str]] = {}
        self.user_agents: Dict[str, str] = {}
        
        self._load_cookies_from_file()
    
    def _load_cookies_from_file(self):
        """Load cookies from JSON file if exists."""
        if not self.cookies_file or not self.cookies_file.exists():
            return
        
        try:
            with open(self.cookies_file) as f:
                data = json.load(f)
            
            for domain, cookies in data.items():
                if isinstance(cookies, dict):
                    self.cookie_cache[domain] = cookies
                    
            logger.info(f"Loaded CF cookies for {len(self.cookie_cache)} domains")
            
        except Exception as e:
            logger.warning(f"Failed to load cookies file: {e}")
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('CF_BYPASS_ENABLED', True)
        if not enabled:
            raise NotConfigured("Cloudflare bypass disabled")
        
        middleware = cls(
            enabled=True,
            cookies_file=crawler.settings.get('CF_COOKIES_FILE'),
            flaresolverr_url=crawler.settings.get('FLARESOLVERR_URL'),
            protected_domains=crawler.settings.getlist('CF_PROTECTED_DOMAINS', []),
        )
        
        return middleware
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    def _needs_bypass(self, domain: str) -> bool:
        """Check if domain needs Cloudflare bypass."""
        if not self.protected_domains:
            return False
        return any(pd in domain for pd in self.protected_domains)
    
    def _get_cookies(self, domain: str) -> Dict[str, str]:
        """Get cookies for domain, fetching via Flaresolverr if needed."""
        if domain in self.cookie_cache:
            return self.cookie_cache[domain]
        
        if self.flaresolverr_url:
            logger.info(f"Fetching CF cookies via Flaresolverr for {domain}")
            cookies = get_flaresolverr_cookies(
                f"https://{domain}",
                self.flaresolverr_url,
            )
            if cookies:
                self.cookie_cache[domain] = cookies
                return cookies
        
        return {}
    
    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Inject Cloudflare cookies into request."""
        if not self.enabled:
            return None
        
        domain = self._get_domain(request.url)
        
        if not self._needs_bypass(domain):
            return None
        
        cookies = self._get_cookies(domain)
        
        if cookies:
            # Inject cookies
            for name, value in cookies.items():
                request.cookies[name] = value
            
            # Use cached user-agent if available
            if domain in self.user_agents:
                request.headers['User-Agent'] = self.user_agents[domain]
            
            spider.logger.debug(f"Injected CF cookies for {domain}")
        
        return None


# Export default stealth settings for Playwright spiders
PLAYWRIGHT_STEALTH_SETTINGS = {
    'PLAYWRIGHT_LAUNCH_OPTIONS': {
        'headless': True,
        'args': STEALTH_PLAYWRIGHT_ARGS,
    },
    'PLAYWRIGHT_CONTEXTS': {
        'default': {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        },
    },
}
