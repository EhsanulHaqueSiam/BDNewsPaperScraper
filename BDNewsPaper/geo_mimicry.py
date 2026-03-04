"""
Geographic Mimicry Module
=========================
Bangladesh-specific proxy and geo-location features.

Features:
    - Bangladesh proxy provider integration
    - Geo-targeted request headers
    - Locale/timezone consistency
    - Residential proxy rotation
    - Auto-detect geo-blocks

Supported Providers:
    - BrightData (bd-isp)
    - Oxylabs
    - SmartProxy
    - Custom proxy lists

Usage:
    from BDNewsPaper.geo_mimicry import (
        BangladeshProxyMiddleware,
        get_bd_headers,
        is_geo_blocked,
    )

Settings:
    GEO_MIMICRY_ENABLED = True
    GEO_PROXY_PROVIDER = 'brightdata'  # or 'oxylabs', 'smartproxy', 'custom'
    GEO_PROXY_URL = 'http://user:pass@proxy.provider.com:port'
    GEO_PROXY_COUNTRY = 'bd'
"""

import logging
import random
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


# =============================================================================
# BANGLADESH-SPECIFIC HEADERS
# =============================================================================

BD_ACCEPT_LANGUAGES = [
    'bn-BD,bn;q=0.9,en-US;q=0.8,en;q=0.7',
    'en-US,en;q=0.9,bn-BD;q=0.8,bn;q=0.7',
    'en-BD,en;q=0.9,bn;q=0.8',
]

BD_TIMEZONES = ['Asia/Dhaka']

# Major Bangladeshi cities for geo headers
BD_CITIES = [
    {'city': 'Dhaka', 'lat': 23.8103, 'lon': 90.4125},
    {'city': 'Chittagong', 'lat': 22.3569, 'lon': 91.7832},
    {'city': 'Khulna', 'lat': 22.8456, 'lon': 89.5403},
    {'city': 'Rajshahi', 'lat': 24.3745, 'lon': 88.6042},
    {'city': 'Sylhet', 'lat': 24.8949, 'lon': 91.8687},
]

# Bangladeshi ISP headers
BD_ISP_HEADERS = {
    'grameenphone': {
        'Via': '1.1 gp-proxy.grameenphone.com',
        'X-Forwarded-For': '103.4.145.',  # GP IP range prefix
    },
    'robi': {
        'Via': '1.1 proxy.robi.com.bd',
        'X-Forwarded-For': '103.97.184.',
    },
    'banglalink': {
        'Via': '1.1 proxy.banglalink.net',
        'X-Forwarded-For': '103.48.16.',
    },
    'teletalk': {
        'Via': '1.1 proxy.teletalk.com.bd',
        'X-Forwarded-For': '103.197.206.',
    },
}


def get_bd_headers(isp: str = None) -> Dict[str, str]:
    """
    Get headers that appear to come from Bangladesh.
    
    Args:
        isp: Optional specific ISP to mimic (grameenphone, robi, banglalink, teletalk)
    """
    headers = {
        'Accept-Language': random.choice(BD_ACCEPT_LANGUAGES),
    }
    
    # Add ISP-specific headers if specified
    if isp and isp in BD_ISP_HEADERS:
        isp_hdrs = BD_ISP_HEADERS[isp]
        headers.update({
            'Via': isp_hdrs.get('Via', ''),
            'X-Forwarded-For': isp_hdrs.get('X-Forwarded-For', '') + str(random.randint(1, 254)),
        })
    
    return headers


def get_bd_geo_context() -> Dict:
    """Get Playwright context options for Bangladesh geo."""
    city = random.choice(BD_CITIES)
    return {
        'locale': 'bn-BD',
        'timezone_id': 'Asia/Dhaka',
        'geolocation': {
            'latitude': city['lat'],
            'longitude': city['lon'],
            'accuracy': 100,
        },
        'permissions': ['geolocation'],
    }


# =============================================================================
# GEO-BLOCK DETECTION
# =============================================================================

GEO_BLOCK_PATTERNS = [
    r'not available in your region',
    r'not available in your country',
    r'access denied.*location',
    r'sorry.*region',
    r'geo.?restrict',
    r'blocked.*your country',
    r'this content is not available in bangladesh',
    r'international edition',
    r'viewing from outside',
]


def is_geo_blocked(response: Response) -> bool:
    """
    Detect if response indicates geo-blocking.
    """
    # Check status codes
    if response.status in [403, 451]:  # 451 = Unavailable For Legal Reasons
        return True
    
    # Check content - safely access response.text
    try:
        text = response.text[:5000].lower()
        for pattern in GEO_BLOCK_PATTERNS:
            if re.search(pattern, text, re.I):
                return True
    except Exception:
        # Response is not text (e.g., binary response)
        pass
    
    return False


# =============================================================================
# PROXY PROVIDER CONFIGURATIONS
# =============================================================================

@dataclass
class ProxyConfig:
    """Configuration for a proxy provider."""
    name: str
    url_template: str
    country_param: str = 'country'
    session_param: str = 'session'


PROXY_PROVIDERS = {
    'brightdata': ProxyConfig(
        name='BrightData',
        url_template='http://{user}-country-{country}:{password}@brd.superproxy.io:22225',
        country_param='country',
    ),
    'oxylabs': ProxyConfig(
        name='Oxylabs',
        url_template='http://{user}-country-{country}:{password}@pr.oxylabs.io:7777',
        country_param='country',
    ),
    'smartproxy': ProxyConfig(
        name='SmartProxy',
        url_template='http://{user}:{password}@gate.smartproxy.com:7777',
        country_param='country',
    ),
}


def get_provider_proxy_url(
    provider: str,
    username: str,
    password: str,
    country: str = 'bd',
    session: str = None,
) -> str:
    """
    Get proxy URL for a specific provider.
    """
    if provider not in PROXY_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    
    config = PROXY_PROVIDERS[provider]
    
    # Build user string with session if provided
    user = username
    if session:
        user = f"{username}-session-{session}"
    
    url = config.url_template.format(
        user=user,
        password=password,
        country=country,
    )
    
    return url


# =============================================================================
# GEO MIMICRY MIDDLEWARE
# =============================================================================

class BangladeshProxyMiddleware:
    """
    Middleware for geographic mimicry using Bangladesh proxies.
    
    Automatically:
    - Routes requests through Bangladesh IP
    - Adds BD-specific headers
    - Detects and retries geo-blocked responses
    - Rotates sessions for variety
    
    Settings:
        GEO_MIMICRY_ENABLED: Enable/disable
        GEO_PROXY_PROVIDER: brightdata, oxylabs, smartproxy, or custom
        GEO_PROXY_URL: Full proxy URL (for custom)
        GEO_PROXY_USER: Proxy username
        GEO_PROXY_PASS: Proxy password
        GEO_DOMAINS: Domains to apply geo mimicry to
        GEO_RETRY_ON_BLOCK: Retry with different IP on geo-block
    """
    
    def __init__(
        self,
        enabled: bool = True,
        provider: str = None,
        proxy_url: str = None,
        username: str = None,
        password: str = None,
        domains: List[str] = None,
        retry_on_block: bool = True,
    ):
        self.enabled = enabled
        self.provider = provider
        self.proxy_url = proxy_url
        self.username = username
        self.password = password
        self.domains = set(domains or [])
        self.retry_on_block = retry_on_block
        
        self.session_counter = 0
        
        self.stats = {
            'requests_proxied': 0,
            'geo_blocks_detected': 0,
            'retries': 0,
        }
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('GEO_MIMICRY_ENABLED', False)
        if not enabled:
            raise NotConfigured("Geographic mimicry disabled")
        
        middleware = cls(
            enabled=True,
            provider=crawler.settings.get('GEO_PROXY_PROVIDER'),
            proxy_url=crawler.settings.get('GEO_PROXY_URL'),
            username=crawler.settings.get('GEO_PROXY_USER'),
            password=crawler.settings.get('GEO_PROXY_PASS'),
            domains=crawler.settings.getlist('GEO_DOMAINS', []),
            retry_on_block=crawler.settings.getbool('GEO_RETRY_ON_BLOCK', True),
        )
        
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc
    
    def _needs_geo(self, domain: str) -> bool:
        if not self.domains:
            return False
        return any(d in domain for d in self.domains)
    
    def _get_proxy_url(self, session_id: str = None) -> Optional[str]:
        """Get proxy URL for request."""
        if self.proxy_url:
            return self.proxy_url
        
        if self.provider and self.username and self.password:
            return get_provider_proxy_url(
                self.provider,
                self.username,
                self.password,
                country='bd',
                session=session_id,
            )
        
        return None
    
    def _get_session_id(self) -> str:
        """Generate rotating session ID."""
        self.session_counter += 1
        return f"bd{self.session_counter % 100}"
    
    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Add Bangladesh proxy and headers to request."""
        if not self.enabled:
            return None
        
        domain = self._get_domain(request.url)
        
        if not self._needs_geo(domain):
            return None
        
        # Get proxy URL
        session = self._get_session_id()
        proxy_url = self._get_proxy_url(session)
        
        if proxy_url:
            request.meta['proxy'] = proxy_url
            self.stats['requests_proxied'] += 1
        
        # Add Bangladesh headers
        bd_headers = get_bd_headers()
        for key, value in bd_headers.items():
            request.headers.setdefault(key, value)
        
        # Track session for retry
        request.meta['_geo_session'] = session
        request.meta['_geo_attempt'] = request.meta.get('_geo_attempt', 0)
        
        spider.logger.debug(f"GeoMimicry: Proxied {domain} via BD (session: {session})")
        
        return None
    
    def process_response(self, request: Request, response: Response, spider) -> Response:
        """Detect geo-blocks and retry with different IP."""
        if not self.enabled or not self.retry_on_block:
            return response
        
        if '_geo_session' not in request.meta:
            return response
        
        attempt = request.meta.get('_geo_attempt', 0)
        
        if is_geo_blocked(response) and attempt < 3:
            self.stats['geo_blocks_detected'] += 1
            self.stats['retries'] += 1
            
            spider.logger.warning(
                f"GeoMimicry: Geo-block detected for {request.url}, retrying (attempt {attempt + 1})"
            )
            
            # Retry with new session (new IP)
            return request.replace(
                meta={
                    **request.meta,
                    '_geo_attempt': attempt + 1,
                    '_geo_session': self._get_session_id(),
                },
                dont_filter=True,
            )
        
        return response
    
    def spider_closed(self, spider, reason):
        """Log geo mimicry statistics."""
        if self.stats['requests_proxied'] > 0:
            spider.logger.info(
                f"GeoMimicry Stats: Proxied={self.stats['requests_proxied']}, "
                f"GeoBlocks={self.stats['geo_blocks_detected']}, "
                f"Retries={self.stats['retries']}"
            )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'BangladeshProxyMiddleware',
    'get_bd_headers',
    'get_bd_geo_context',
    'is_geo_blocked',
    'get_provider_proxy_url',
    'BD_CITIES',
    'BD_ISP_HEADERS',
]
