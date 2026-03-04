"""
Cloudflare Bypass Tests
=======================
Tests for Cloudflare bypass middleware and related components.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from scrapy.http import Request, Response, HtmlResponse
from scrapy.exceptions import NotConfigured

from BDNewsPaper.cloudflare_bypass import (
    CloudflareDetector,
    CloudflareCookieCache,
    CookieEntry,
    CloudflareBypassMiddleware,
    get_stealth_playwright_args,
    get_comprehensive_stealth_js,
    get_playwright_stealth_context_options,
    STEALTH_PLAYWRIGHT_ARGS,
)


# ==============================================================================
# CloudflareDetector Tests
# ==============================================================================

class TestCloudflareDetector:
    """Tests for CloudflareDetector challenge detection."""
    
    @pytest.fixture
    def detector(self):
        return CloudflareDetector()
    
    @pytest.fixture
    def make_response(self):
        """Factory to create mock responses."""
        def _make_response(body: str, status: int = 200, url: str = 'http://test.com'):
            request = Request(url=url)
            return HtmlResponse(
                url=url,
                request=request,
                body=body.encode('utf-8'),
                status=status,
                encoding='utf-8',
            )
        return _make_response
    
    def test_detects_challenge_page(self, detector, make_response):
        """Test detection of Cloudflare challenge page."""
        html = """
        <html>
        <head><title>Just a moment...</title></head>
        <body>Checking your browser before accessing the site.</body>
        </html>
        """
        response = make_response(html)
        assert detector.detect(response) == 'challenge'
    
    def test_detects_cf_turnstile(self, detector, make_response):
        """Test detection of Cloudflare Turnstile challenge."""
        html = '<div class="cf-turnstile" data-sitekey="xxx"></div>'
        response = make_response(html)
        assert detector.detect(response) == 'challenge'
    
    def test_detects_cf_browser_verification(self, detector, make_response):
        """Test detection of cf-browser-verification."""
        html = '<div class="cf-browser-verification">Please wait...</div>'
        response = make_response(html)
        assert detector.detect(response) == 'challenge'
    
    def test_detects_blocked_page(self, detector, make_response):
        """Test detection of Cloudflare block page."""
        html = '<h1>Sorry, you have been blocked</h1>'
        response = make_response(html)
        assert detector.detect(response) == 'blocked'
    
    def test_detects_403_as_blocked(self, detector, make_response):
        """Test detection of 403 status as blocked."""
        response = make_response('Forbidden', status=403)
        assert detector.detect(response) == 'blocked'
    
    def test_detects_429_as_ratelimited(self, detector, make_response):
        """Test detection of 429 status as rate limited."""
        response = make_response('Too many requests', status=429)
        assert detector.detect(response) == 'ratelimited'
    
    def test_detects_ratelimit_pattern(self, detector, make_response):
        """Test detection of rate limit message in body."""
        html = '<p>Error 1015: You are being rate limited</p>'
        response = make_response(html)
        assert detector.detect(response) == 'ratelimited'
    
    def test_no_protection_detected(self, detector, make_response):
        """Test that normal pages return 'none'."""
        html = """
        <html>
        <head><title>News Article</title></head>
        <body><p>This is a normal article.</p></body>
        </html>
        """
        response = make_response(html)
        assert detector.detect(response) == 'none'
    
    def test_detects_503_as_challenge(self, detector, make_response):
        """Test detection of 503 status as challenge."""
        response = make_response('Service Unavailable', status=503)
        assert detector.detect(response) == 'challenge'
    
    def test_has_cf_cookies(self, detector):
        """Test detection of Cloudflare cookies."""
        assert detector.has_cf_cookies({'cf_clearance': 'xxx'})
        assert detector.has_cf_cookies({'__cf_bm': 'xxx'})
        assert detector.has_cf_cookies({'other': 'value', 'cf_chl_2': 'xxx'})
        assert not detector.has_cf_cookies({'session': 'xxx'})
        assert not detector.has_cf_cookies({})


# ==============================================================================
# CloudflareCookieCache Tests
# ==============================================================================

class TestCloudflareCookieCache:
    """Tests for CloudflareCookieCache."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        return CloudflareCookieCache(cache_file=tmp_path / 'cf_cookies.json')
    
    def test_set_and_get_cookies(self, cache):
        """Test setting and getting cookies."""
        cookies = {'cf_clearance': 'test_value', '__cf_bm': 'another_value'}
        cache.set('example.com', cookies, 'Mozilla/5.0 Test')
        
        entry = cache.get('example.com')
        assert entry is not None
        assert entry.cookies == cookies
        assert entry.user_agent == 'Mozilla/5.0 Test'
    
    def test_get_nonexistent_domain(self, cache):
        """Test getting cookies for unknown domain."""
        assert cache.get('unknown.com') is None
    
    def test_clear_expired(self, cache):
        """Test clearing expired entries."""
        # Set a cookie
        cache.set('example.com', {'cf_clearance': 'xxx'}, '')
        
        # Manually expire it
        entry = cache.cache.get('example.com')
        if entry:
            entry.expires_at = datetime.now() - timedelta(hours=1)
        
        cache.clear_expired()
        assert cache.get('example.com') is None
    
    def test_save_and_load(self, cache, tmp_path):
        """Test saving and loading from file."""
        cookies = {'cf_clearance': 'persistent'}
        cache.set('test.com', cookies, 'TestUA')
        cache.save_to_file()
        
        # Create new cache from same file
        new_cache = CloudflareCookieCache(cache_file=tmp_path / 'cf_cookies.json')
        entry = new_cache.get('test.com')
        
        assert entry is not None
        assert entry.cookies == cookies


# ==============================================================================
# CloudflareBypassMiddleware Tests
# ==============================================================================

class TestCloudflareBypassMiddleware:
    """Tests for CloudflareBypassMiddleware."""
    
    @pytest.fixture
    def mock_crawler(self):
        crawler = MagicMock()
        crawler.settings.getbool = lambda k, d=None: {
            'CF_BYPASS_ENABLED': True,
            'CF_TLS_CLIENT_ENABLED': False,
        }.get(k, d)
        crawler.settings.getlist = lambda k, d=None: {
            'CF_PROTECTED_DOMAINS': ['daily-sun.com'],
        }.get(k, d or [])
        crawler.settings.get = lambda k, d=None: {
            'CF_COOKIES_FILE': None,
            'FLARESOLVERR_URL': None,
        }.get(k, d)
        crawler.settings.getint = lambda k, d=None: {
            'CF_MAX_RETRIES': 3,
        }.get(k, d)
        crawler.signals.connect = MagicMock()
        return crawler
    
    @pytest.fixture
    def middleware(self, mock_crawler):
        return CloudflareBypassMiddleware.from_crawler(mock_crawler)
    
    def test_from_crawler_creates_middleware(self, mock_crawler):
        """Test middleware creation from crawler."""
        middleware = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        assert middleware.enabled is True
        assert 'daily-sun.com' in middleware.protected_domains
    
    def test_disabled_raises_not_configured(self):
        """Test that disabled middleware raises NotConfigured."""
        crawler = MagicMock()
        crawler.settings.getbool = lambda k, d=None: False if k == 'CF_BYPASS_ENABLED' else d
        
        with pytest.raises(NotConfigured):
            CloudflareBypassMiddleware.from_crawler(crawler)
    
    def test_process_request_injects_cookies(self, middleware, mock_spider):
        """Test that cached cookies are injected into requests."""
        # Prime the cache
        middleware.cookie_cache.set('daily-sun.com', {'cf_clearance': 'xxx'}, 'TestUA')
        
        request = Request(url='http://daily-sun.com/article')
        middleware.process_request(request, mock_spider)
        
        assert 'cf_clearance' in request.cookies
        assert request.meta.get('_cf_bypass_domain') == 'daily-sun.com'
    
    def test_process_request_skips_non_protected(self, middleware, mock_spider):
        """Test that non-protected domains are skipped."""
        request = Request(url='http://other-site.com/page')
        result = middleware.process_request(request, mock_spider)
        
        assert result is None
        assert '_cf_bypass_domain' not in request.meta
    
    def test_process_response_detects_challenge(self, middleware, mock_spider):
        """Test that challenges are detected and escalation is triggered."""
        request = Request(
            url='http://daily-sun.com/article',
            meta={'_cf_bypass_domain': 'daily-sun.com', '_cf_bypass_attempt': 0}
        )
        html = '<title>Just a moment...</title>'
        response = HtmlResponse(
            url='http://daily-sun.com/article',
            request=request,
            body=html.encode('utf-8'),
            status=200,
        )
        
        result = middleware.process_response(request, response, mock_spider)
        
        # Should return a new request with playwright enabled
        if isinstance(result, Request):
            assert result.meta.get('playwright') is True
        assert middleware.stats['challenges_detected'] >= 1


# ==============================================================================
# Helper Function Tests
# ==============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_stealth_playwright_args_not_empty(self):
        """Test that stealth args are provided."""
        args = get_stealth_playwright_args()
        assert len(args) > 10
        assert '--disable-blink-features=AutomationControlled' in args
    
    def test_stealth_js_contains_webdriver_override(self):
        """Test that stealth JS removes webdriver flag."""
        js = get_comprehensive_stealth_js()
        assert 'webdriver' in js
        assert 'navigator' in js
    
    def test_playwright_context_options(self):
        """Test that context options are returned."""
        options = get_playwright_stealth_context_options()
        assert 'viewport' in options
        assert options['locale'] == 'en-US'
        assert 'timezone_id' in options
