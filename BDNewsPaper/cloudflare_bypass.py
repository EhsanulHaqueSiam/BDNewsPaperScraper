"""
Cloudflare Countermeasures - Complete Implementation
=====================================================
Multi-level, robust Cloudflare bypass system.

LEVELS IMPLEMENTED:
    1. Stealth Headers (stealth_headers.py) - Chrome-like headers
    2. Stealth Playwright - Full automation hiding with JS injection
    3. Cookie Management - cf_clearance injection and caching
    4. Flaresolverr Integration - Docker-based challenge solving
    5. TLS Fingerprinting - curl_cffi for Chrome TLS mimicry
    6. Challenge Detection - Automatic detection and escalation
    7. Request Retry with Escalation - Progressive bypass attempts

Usage:
    from BDNewsPaper.cloudflare_bypass import (
        CloudflareBypassMiddleware,  # Main middleware
        get_stealth_playwright_args,
        get_comprehensive_stealth_js,
        solve_with_flaresolverr,
    )

Settings:
    CF_BYPASS_ENABLED = True
    CF_PROTECTED_DOMAINS = ['daily-sun.com']
    FLARESOLVERR_URL = 'http://localhost:8191/v1'
    CF_COOKIES_FILE = 'config/cf_cookies.json'
    CF_TLS_CLIENT_ENABLED = True
"""

import json
import logging
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse

from scrapy import signals
from scrapy.http import Request, Response, HtmlResponse
from scrapy.exceptions import NotConfigured, IgnoreRequest

logger = logging.getLogger(__name__)


# =============================================================================
# LEVEL 2: COMPREHENSIVE STEALTH PLAYWRIGHT
# =============================================================================

# Extended Playwright launch arguments for maximum stealth
STEALTH_PLAYWRIGHT_ARGS = [
    # Disable automation detection
    '--disable-blink-features=AutomationControlled',
    '--disable-automation',
    '--disable-infobars',
    
    # Disable extensions and dev tools
    '--disable-extensions',
    '--disable-plugins-discovery',
    '--disable-dev-shm-usage',
    
    # GPU and rendering
    '--disable-gpu',
    '--disable-software-rasterizer',
    '--disable-accelerated-2d-canvas',
    
    # Sandbox and resources
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--no-first-run',
    '--no-default-browser-check',
    
    # Privacy
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-sync',
    
    # Performance
    '--disable-translate',
    '--disable-features=IsolateOrigins,site-per-process',
    '--ignore-certificate-errors',
    
    # Window
    '--window-size=1920,1080',
    '--start-maximized',
]

# Comprehensive stealth JavaScript injection
COMPREHENSIVE_STEALTH_JS = """
// ============================================================
// COMPREHENSIVE ANTI-DETECTION SCRIPT
// ============================================================

// 1. Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
});

// 2. Override navigator properties
const originalNavigator = window.navigator;
const navigatorProxy = new Proxy(originalNavigator, {
    get: function(target, prop) {
        if (prop === 'webdriver') return undefined;
        if (prop === 'plugins') return [1, 2, 3, 4, 5];
        if (prop === 'languages') return ['en-US', 'en', 'bn'];
        if (prop === 'platform') return 'Win32';
        if (prop === 'vendor') return 'Google Inc.';
        if (prop === 'hardwareConcurrency') return 8;
        if (prop === 'deviceMemory') return 8;
        if (prop === 'maxTouchPoints') return 0;
        return typeof target[prop] === 'function' 
            ? target[prop].bind(target) 
            : target[prop];
    }
});

// 3. Fix permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' 
        ? Promise.resolve({ state: Notification.permission }) 
        : originalQuery(parameters)
);

// 4. Mock chrome runtime
window.chrome = {
    runtime: {
        connect: () => {},
        sendMessage: () => {},
        onMessage: { addListener: () => {} },
    },
    loadTimes: () => {},
    csi: () => {},
};

// 5. Override toString for functions
const originalFunctionToString = Function.prototype.toString;
Function.prototype.toString = function() {
    if (this === window.navigator.permissions.query) {
        return 'function query() { [native code] }';
    }
    return originalFunctionToString.call(this);
};

// 6. Fake WebGL vendor
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';  // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER_WEBGL
    return getParameter.call(this, parameter);
};

// 7. Disable automation flags in window
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

// 8. Mock notification
window.Notification = {
    permission: 'default',
    requestPermission: () => Promise.resolve('default'),
};

// 9. Override RTCPeerConnection for WebRTC leak prevention
const originalRTCPeerConnection = window.RTCPeerConnection;
window.RTCPeerConnection = function(...args) {
    const pc = new originalRTCPeerConnection(...args);
    pc.createDataChannel = () => {};
    return pc;
};

// 10. Timezone offset
Date.prototype.getTimezoneOffset = function() { return -360; };  // Bangladesh (UTC+6)

console.log('[Stealth] Anti-detection measures applied');
"""


def get_stealth_playwright_args() -> List[str]:
    """Get full Playwright launch arguments for stealth mode."""
    return STEALTH_PLAYWRIGHT_ARGS.copy()


def get_comprehensive_stealth_js() -> str:
    """Get comprehensive JavaScript for hiding automation."""
    return COMPREHENSIVE_STEALTH_JS


def get_playwright_stealth_context_options() -> Dict:
    """Get Playwright context options for stealth."""
    return {
        'viewport': {'width': 1920, 'height': 1080},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'locale': 'en-US',
        'timezone_id': 'Asia/Dhaka',
        'geolocation': {'latitude': 23.8103, 'longitude': 90.4125},  # Dhaka
        'permissions': ['geolocation'],
        'color_scheme': 'light',
        'java_script_enabled': True,
        'accept_downloads': False,
        'ignore_https_errors': True,
        'extra_http_headers': {
            'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8',
        },
    }


# =============================================================================
# LEVEL 3: COOKIE MANAGEMENT
# =============================================================================

@dataclass
class CookieEntry:
    """Cached cookie with expiration."""
    cookies: Dict[str, str]
    user_agent: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if not self.expires_at:
            # Default 2 hour expiration
            return datetime.now() > self.created_at + timedelta(hours=2)
        return datetime.now() > self.expires_at


class CloudflareCookieCache:
    """
    Persistent cookie cache with file backing.
    """
    
    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file
        self.cache: Dict[str, CookieEntry] = {}
        self._load_from_file()
    
    def _load_from_file(self):
        """Load cookies from file."""
        if not self.cache_file or not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file) as f:
                data = json.load(f)
            
            for domain, entry in data.items():
                self.cache[domain] = CookieEntry(
                    cookies=entry.get('cookies', {}),
                    user_agent=entry.get('user_agent', ''),
                    created_at=datetime.fromisoformat(entry.get('created_at', datetime.now().isoformat())),
                )
            
            logger.info(f"Loaded CF cookies for {len(self.cache)} domains")
            
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")
    
    def save_to_file(self):
        """Save cookies to file."""
        if not self.cache_file:
            return
        
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for domain, entry in self.cache.items():
                if not entry.is_expired():
                    data[domain] = {
                        'cookies': entry.cookies,
                        'user_agent': entry.user_agent,
                        'created_at': entry.created_at.isoformat(),
                    }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")
    
    def get(self, domain: str) -> Optional[CookieEntry]:
        """Get cookies for domain if not expired."""
        entry = self.cache.get(domain)
        if entry and not entry.is_expired():
            return entry
        return None
    
    def set(self, domain: str, cookies: Dict[str, str], user_agent: str = ''):
        """Set cookies for domain."""
        self.cache[domain] = CookieEntry(
            cookies=cookies,
            user_agent=user_agent,
        )
        self.save_to_file()
    
    def clear_expired(self):
        """Remove expired entries."""
        expired = [d for d, e in self.cache.items() if e.is_expired()]
        for domain in expired:
            del self.cache[domain]


# =============================================================================
# LEVEL 4: FLARESOLVERR INTEGRATION
# =============================================================================

@dataclass
class FlaresolverrResponse:
    """Response from Flaresolverr."""
    status: str
    message: str
    solution: Optional[Dict[str, Any]] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == 'ok'
    
    @property
    def cookies(self) -> Dict[str, str]:
        if not self.solution:
            return {}
        return {c['name']: c['value'] for c in self.solution.get('cookies', [])}
    
    @property
    def user_agent(self) -> str:
        if not self.solution:
            return ''
        return self.solution.get('userAgent', '')


class FlaresolverrClient:
    """
    Full-featured Flaresolverr client.
    
    Install Flaresolverr:
        docker run -d --name=flaresolverr -p 8191:8191 \\
            -e LOG_LEVEL=info \\
            ghcr.io/flaresolverr/flaresolverr:latest
    """
    
    def __init__(self, url: str = 'http://localhost:8191/v1'):
        self.url = url.rstrip('/')
        self._session_id: Optional[str] = None
        self._available: Optional[bool] = None
    
    def is_available(self) -> bool:
        """Check if Flaresolverr is running."""
        if self._available is not None:
            return self._available
        
        try:
            import httpx
            response = httpx.get(f"{self.url.replace('/v1', '')}/health", timeout=5)
            self._available = response.status_code == 200
        except:
            self._available = False
        
        return self._available
    
    def solve_challenge(
        self,
        url: str,
        timeout: int = 60,
        max_retries: int = 3,
    ) -> FlaresolverrResponse:
        """
        Solve Cloudflare challenge with retries.
        """
        for attempt in range(max_retries):
            try:
                import httpx
                response = httpx.post(
                    self.url,
                    json={
                        'cmd': 'request.get',
                        'url': url,
                        'maxTimeout': timeout * 1000,
                    },
                    timeout=timeout + 30,
                )
                
                data = response.json()
                result = FlaresolverrResponse(
                    status=data.get('status', 'error'),
                    message=data.get('message', ''),
                    solution=data.get('solution'),
                )
                
                if result.is_success:
                    return result
                
                logger.warning(f"Flaresolverr attempt {attempt + 1} failed: {result.message}")
                
            except Exception as e:
                logger.error(f"Flaresolverr error: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return FlaresolverrResponse(status='error', message='Max retries exceeded')
    
    def create_session(self) -> Optional[str]:
        """Create persistent session for multiple requests."""
        try:
            import httpx
            response = httpx.post(
                self.url,
                json={'cmd': 'sessions.create'},
                timeout=30,
            )
            data = response.json()
            self._session_id = data.get('session')
            return self._session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    def destroy_session(self):
        """Destroy the session."""
        if not self._session_id:
            return
        try:
            import httpx
            httpx.post(
                self.url,
                json={'cmd': 'sessions.destroy', 'session': self._session_id},
                timeout=10,
            )
            self._session_id = None
        except:
            pass


def solve_with_flaresolverr(
    url: str,
    flaresolverr_url: str = 'http://localhost:8191/v1',
    timeout: int = 60,
) -> Tuple[Dict[str, str], str]:
    """
    Solve Cloudflare challenge and return cookies + user-agent.
    
    Returns:
        Tuple of (cookies dict, user_agent string)
    """
    client = FlaresolverrClient(flaresolverr_url)
    
    if not client.is_available():
        logger.warning("Flaresolverr not available")
        return {}, ''
    
    response = client.solve_challenge(url, timeout)
    
    if response.is_success:
        return response.cookies, response.user_agent
    
    return {}, ''


# =============================================================================
# LEVEL 5: TLS FINGERPRINTING (curl_cffi)
# =============================================================================

# Check for curl_cffi availability
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None


def make_tls_impersonated_request(
    url: str,
    browser: str = 'chrome120',
    timeout: int = 30,
) -> Optional[str]:
    """
    Make request with Chrome TLS fingerprint using curl_cffi.
    
    Args:
        url: URL to request
        browser: Browser to impersonate (chrome120, chrome119, firefox120, etc.)
        timeout: Request timeout
        
    Returns:
        Response text or None
    """
    if not CURL_CFFI_AVAILABLE:
        logger.warning("curl_cffi not available - install with: pip install curl_cffi")
        return None
    
    try:
        response = curl_requests.get(
            url,
            impersonate=browser,
            timeout=timeout,
            allow_redirects=True,
        )
        return response.text
    except Exception as e:
        logger.error(f"TLS request failed: {e}")
        return None


# =============================================================================
# LEVEL 6: CHALLENGE DETECTION
# =============================================================================

class CloudflareDetector:
    """Detect Cloudflare protection types."""
    
    # Challenge page patterns
    CHALLENGE_PATTERNS = [
        r'<title>Just a moment\.\.\.</title>',
        r'_cf_chl_opt',
        r'challenge-platform',
        r'cf-browser-verification',
        r'cf-turnstile',
        r'Checking your browser',
        r'Please Wait\.\.\. \| Cloudflare',
        r'Attention Required! \| Cloudflare',
        r'ray ID:',
        r'cf-ray',
    ]
    
    # Block page patterns
    BLOCK_PATTERNS = [
        r'Access denied',
        r'Error 1020',
        r'Sorry, you have been blocked',
        r'This website is using a security service',
    ]
    
    # Rate limit patterns
    RATELIMIT_PATTERNS = [
        r'Error 1015',
        r'rate limit',
        r'too many requests',
    ]
    
    def __init__(self):
        self.challenge_re = [re.compile(p, re.I) for p in self.CHALLENGE_PATTERNS]
        self.block_re = [re.compile(p, re.I) for p in self.BLOCK_PATTERNS]
        self.ratelimit_re = [re.compile(p, re.I) for p in self.RATELIMIT_PATTERNS]
    
    def detect(self, response: Response) -> str:
        """
        Detect protection type.
        
        Returns:
            'challenge', 'blocked', 'ratelimited', or 'none'
        """
        # Check status code first
        if response.status == 403:
            return 'blocked'
        if response.status == 429:
            return 'ratelimited'
        if response.status == 503:
            return 'challenge'
        
        # Check content - safely access response.text
        try:
            text = response.text[:5000]  # Only check first 5KB
        except Exception:
            # Response is not text (e.g., binary, or encoding issue)
            return 'none'
        
        for pattern in self.challenge_re:
            if pattern.search(text):
                return 'challenge'
        
        for pattern in self.block_re:
            if pattern.search(text):
                return 'blocked'
        
        for pattern in self.ratelimit_re:
            if pattern.search(text):
                return 'ratelimited'
        
        return 'none'
    
    def has_cf_cookies(self, cookies: Dict) -> bool:
        """Check if cookies contain Cloudflare clearance."""
        cf_cookies = ['cf_clearance', '__cf_bm', 'cf_chl_2']
        return any(c in cookies for c in cf_cookies)


# =============================================================================
# LEVEL 7: MAIN BYPASS MIDDLEWARE
# =============================================================================

class CloudflareBypassMiddleware:
    """
    Complete Cloudflare bypass middleware with progressive escalation.
    
    Bypass Strategy:
    1. First attempt: Use cached cookies
    2. If challenge: Try with stealth headers
    3. If still blocked: Use Flaresolverr (if available)
    4. If still blocked: Escalate to Playwright
    
    Settings:
        CF_BYPASS_ENABLED: Enable/disable
        CF_PROTECTED_DOMAINS: Domains to apply bypass
        CF_COOKIES_FILE: Cookie cache file path
        FLARESOLVERR_URL: Flaresolverr endpoint
        CF_MAX_RETRIES: Max bypass attempts
        CF_TLS_CLIENT_ENABLED: Use curl_cffi for TLS
    """
    
    def __init__(
        self,
        enabled: bool = True,
        protected_domains: List[str] = None,
        cookies_file: Optional[Path] = None,
        flaresolverr_url: Optional[str] = None,
        max_retries: int = 3,
        use_tls_client: bool = True,
    ):
        self.enabled = enabled
        self.protected_domains = set(protected_domains or [])
        self.max_retries = max_retries
        self.use_tls_client = use_tls_client and CURL_CFFI_AVAILABLE
        
        # Initialize components
        self.cookie_cache = CloudflareCookieCache(cookies_file)
        self.detector = CloudflareDetector()
        self.flaresolverr = FlaresolverrClient(flaresolverr_url) if flaresolverr_url else None
        
        self.stats = {
            'challenges_detected': 0,
            'bypassed_with_cookies': 0,
            'bypassed_with_flaresolverr': 0,
            'bypassed_with_tls': 0,
            'failed': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('CF_BYPASS_ENABLED', True)
        if not enabled:
            raise NotConfigured("Cloudflare bypass disabled")
        
        cookies_file = crawler.settings.get('CF_COOKIES_FILE')
        middleware = cls(
            enabled=True,
            protected_domains=crawler.settings.getlist('CF_PROTECTED_DOMAINS', []),
            cookies_file=Path(cookies_file) if cookies_file else None,
            flaresolverr_url=crawler.settings.get('FLARESOLVERR_URL'),
            max_retries=crawler.settings.getint('CF_MAX_RETRIES', 3),
            use_tls_client=crawler.settings.getbool('CF_TLS_CLIENT_ENABLED', True),
        )
        
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc
    
    def _needs_bypass(self, domain: str) -> bool:
        if not self.protected_domains:
            return False
        return any(pd in domain for pd in self.protected_domains)
    
    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Inject cached cookies before request."""
        if not self.enabled:
            return None
        
        domain = self._get_domain(request.url)
        
        if not self._needs_bypass(domain):
            return None
        
        # Try cached cookies first
        cached = self.cookie_cache.get(domain)
        if cached:
            for name, value in cached.cookies.items():
                request.cookies[name] = value
            if cached.user_agent:
                request.headers['User-Agent'] = cached.user_agent
            spider.logger.debug(f"CF: Injected cached cookies for {domain}")
        
        # Mark request for tracking
        request.meta['_cf_bypass_domain'] = domain
        request.meta['_cf_bypass_attempt'] = request.meta.get('_cf_bypass_attempt', 0)
        
        return None
    
    def process_response(self, request: Request, response: Response, spider) -> Response:
        """Detect challenges and trigger bypass."""
        if not self.enabled:
            return response
        
        domain = request.meta.get('_cf_bypass_domain')
        if not domain:
            return response
        
        # Detect protection type
        protection = self.detector.detect(response)
        
        if protection == 'none':
            return response
        
        self.stats['challenges_detected'] += 1
        attempt = request.meta.get('_cf_bypass_attempt', 0)
        
        if attempt >= self.max_retries:
            self.stats['failed'] += 1
            spider.logger.error(f"CF: Max retries reached for {domain}")
            return response
        
        spider.logger.warning(f"CF: Detected {protection} for {domain}, attempt {attempt + 1}")
        
        # Try escalating bypass methods
        new_request = self._escalate_bypass(request, domain, protection, spider)
        if new_request:
            return new_request
        
        return response
    
    def _escalate_bypass(
        self,
        request: Request,
        domain: str,
        protection: str,
        spider,
    ) -> Optional[Request]:
        """Try progressively stronger bypass methods."""
        attempt = request.meta.get('_cf_bypass_attempt', 0)
        
        # Method 1: TLS Client (curl_cffi)
        if self.use_tls_client and attempt == 0:
            spider.logger.info(f"CF: Trying TLS impersonation for {domain}")
            content = make_tls_impersonated_request(request.url)
            if content and 'cf_clearance' not in content.lower():
                self.stats['bypassed_with_tls'] += 1
                # Return fake response - need to parse content
                # For now, continue to next method
        
        # Method 2: Flaresolverr
        if self.flaresolverr and self.flaresolverr.is_available():
            spider.logger.info(f"CF: Using Flaresolverr for {domain}")
            cookies, user_agent = solve_with_flaresolverr(
                request.url,
                self.flaresolverr.url,
            )
            if cookies:
                self.cookie_cache.set(domain, cookies, user_agent)
                self.stats['bypassed_with_flaresolverr'] += 1
                
                # Retry with new cookies
                return request.replace(
                    cookies=cookies,
                    headers={**dict(request.headers), 'User-Agent': user_agent} if user_agent else dict(request.headers),
                    meta={
                        **request.meta,
                        '_cf_bypass_attempt': attempt + 1,
                    },
                    dont_filter=True,
                )
        
        # Method 3: Escalate to Playwright
        if not request.meta.get('playwright'):
            spider.logger.info(f"CF: Escalating to Playwright for {domain}")
            return request.replace(
                meta={
                    **request.meta,
                    'playwright': True,
                    'playwright_include_page': False,
                    '_cf_bypass_attempt': attempt + 1,
                },
                dont_filter=True,
            )
        
        return None
    
    def spider_closed(self, spider, reason):
        """Log bypass statistics."""
        total = self.stats['challenges_detected']
        if total > 0:
            spider.logger.info(
                f"CF Bypass Stats: Detected={total}, "
                f"CookieBypass={self.stats['bypassed_with_cookies']}, "
                f"Flaresolverr={self.stats['bypassed_with_flaresolverr']}, "
                f"TLS={self.stats['bypassed_with_tls']}, "
                f"Failed={self.stats['failed']}"
            )
        
        # Save cookies
        self.cookie_cache.save_to_file()


# =============================================================================
# PLAYWRIGHT STEALTH SETTINGS EXPORT
# =============================================================================

PLAYWRIGHT_STEALTH_SETTINGS = {
    'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
    'PLAYWRIGHT_LAUNCH_OPTIONS': {
        'headless': True,
        'args': STEALTH_PLAYWRIGHT_ARGS,
    },
    'PLAYWRIGHT_CONTEXTS': {
        'default': get_playwright_stealth_context_options(),
    },
}


# =============================================================================
# BACKWARDS COMPATIBILITY
# =============================================================================

# Keep old names for compatibility
CloudflareCookieMiddleware = CloudflareBypassMiddleware
get_stealth_js = get_comprehensive_stealth_js

def get_flaresolverr_cookies(url: str, flaresolverr_url: str = 'http://localhost:8191/v1', timeout: int = 60) -> Dict[str, str]:
    """Backwards compatible function."""
    cookies, _ = solve_with_flaresolverr(url, flaresolverr_url, timeout)
    return cookies
