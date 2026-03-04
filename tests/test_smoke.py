"""
Comprehensive Smoke Tests
=========================
Rigorous integration tests for middleware, pipelines, and spiders.

These tests verify:
    - No middleware conflicts
    - No pipeline conflicts
    - Proper component initialization
    - End-to-end processing
    - Syntax validation
"""

import pytest
import importlib
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from collections import defaultdict

from scrapy import Spider
from scrapy.http import Request, Response, HtmlResponse
from scrapy.exceptions import IgnoreRequest, DropItem, NotConfigured
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings

from BDNewsPaper.items import NewsArticleItem


# ==============================================================================
# Syntax Validation Tests
# ==============================================================================

class TestSyntaxValidation:
    """Verify all Python files have valid syntax."""
    
    @pytest.fixture
    def bdnewspaper_modules(self):
        """List all Python modules in BDNewsPaper package."""
        package_dir = Path(__file__).parent.parent / 'BDNewsPaper'
        modules = []
        
        for py_file in package_dir.glob('*.py'):
            if py_file.name != '__pycache__':
                module_name = f"BDNewsPaper.{py_file.stem}"
                modules.append(module_name)
        
        return modules
    
    @pytest.fixture
    def spider_modules(self):
        """List all spider modules."""
        spider_dir = Path(__file__).parent.parent / 'BDNewsPaper' / 'spiders'
        modules = []
        
        for py_file in spider_dir.glob('*.py'):
            if py_file.name not in ('__init__.py', '__pycache__'):
                module_name = f"BDNewsPaper.spiders.{py_file.stem}"
                modules.append(module_name)
        
        return modules
    
    def test_all_bdnewspaper_modules_import(self, bdnewspaper_modules):
        """Test that all BDNewsPaper modules can be imported."""
        failed_imports = []
        
        # Modules that require optional dependencies
        optional_modules = {
            'BDNewsPaper.api',          # requires fastapi
            'BDNewsPaper.graphql_api',  # requires fastapi/strawberry
            'BDNewsPaper.distributed',  # requires celery/redis
            'BDNewsPaper.postgres_pipeline',  # requires psycopg2
        }
        
        for module_name in bdnewspaper_modules:
            if module_name in optional_modules:
                continue  # Skip optional dependency modules
            try:
                importlib.import_module(module_name)
            except Exception as e:
                failed_imports.append((module_name, str(e)))
        
        if failed_imports:
            msg = "Failed to import modules:\n"
            for mod, err in failed_imports:
                msg += f"  - {mod}: {err}\n"
            pytest.fail(msg)
    
    def test_all_spider_modules_import(self, spider_modules):
        """Test that all spider modules can be imported."""
        failed_imports = []
        
        for module_name in spider_modules:
            try:
                importlib.import_module(module_name)
            except Exception as e:
                failed_imports.append((module_name, str(e)))
        
        if failed_imports:
            msg = "Failed to import spider modules:\n"
            for mod, err in failed_imports:
                msg += f"  - {mod}: {err}\n"
            pytest.fail(msg)


# ==============================================================================
# Middleware Integration Tests
# ==============================================================================

class TestMiddlewareIntegration:
    """Test middleware components work together without conflicts."""
    
    @pytest.fixture
    def mock_crawler(self):
        """Create a mock crawler with realistic settings."""
        crawler = MagicMock()
        crawler.settings = Settings({
            'STEALTH_HEADERS_ENABLED': True,
            'STEALTH_BROWSER_TYPE': 'chrome',
            'STEALTH_ROTATE_UA': True,
            'CF_BYPASS_ENABLED': True,
            'CF_PROTECTED_DOMAINS': ['daily-sun.com'],
            'CF_MAX_RETRIES': 3,
            'CF_TLS_CLIENT_ENABLED': False,
            'RETRY_TIMES': 3,
            'RETRY_HTTP_CODES': [500, 502, 503, 504, 429],
            'ADAPTIVE_THROTTLE_ENABLED': True,
            'HONEYPOT_DETECTION_ENABLED': True,
            'HYBRID_REQUEST_ENABLED': True,
        })
        crawler.signals = MagicMock()
        crawler.signals.connect = MagicMock()
        return crawler
    
    @pytest.fixture
    def mock_spider(self):
        """Create a mock spider."""
        spider = MagicMock(spec=Spider)
        spider.name = 'test_spider'
        spider.logger = MagicMock()
        return spider
    
    def test_stealth_headers_middleware_init(self, mock_crawler):
        """Test StealthHeadersMiddleware initialization."""
        from BDNewsPaper.stealth_headers import StealthHeadersMiddleware
        
        middleware = StealthHeadersMiddleware.from_crawler(mock_crawler)
        assert middleware.enabled is True
        assert middleware.browser_type == 'chrome'
    
    def test_cloudflare_bypass_middleware_init(self, mock_crawler):
        """Test CloudflareBypassMiddleware initialization."""
        from BDNewsPaper.cloudflare_bypass import CloudflareBypassMiddleware
        
        middleware = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        assert middleware.enabled is True
        assert 'daily-sun.com' in middleware.protected_domains
    
    def test_middleware_chain_no_conflicts(self, mock_crawler, mock_spider):
        """Test that middleware chain processes requests without conflicts."""
        from BDNewsPaper.stealth_headers import StealthHeadersMiddleware
        from BDNewsPaper.cloudflare_bypass import CloudflareBypassMiddleware
        
        # Initialize middlewares
        stealth = StealthHeadersMiddleware.from_crawler(mock_crawler)
        cf_bypass = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        
        # Create a test request
        request = Request(url='https://example.com/article')
        
        # Process through stealth headers
        result1 = stealth.process_request(request, mock_spider)
        assert result1 is None  # Should pass through
        assert 'User-Agent' in request.headers
        
        # Process through CF bypass (should skip - not protected domain)
        result2 = cf_bypass.process_request(request, mock_spider)
        assert result2 is None  # Should pass through
    
    def test_middleware_response_chain(self, mock_crawler, mock_spider):
        """Test middleware response processing chain."""
        from BDNewsPaper.cloudflare_bypass import CloudflareBypassMiddleware
        
        cf_bypass = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        
        # Create test request and normal response
        request = Request(url='https://example.com/article')
        response = HtmlResponse(
            url='https://example.com/article',
            request=request,
            body=b'<html><body>Normal page</body></html>',
            status=200,
        )
        
        # Process response - should pass through unchanged
        result = cf_bypass.process_response(request, response, mock_spider)
        assert result == response
    
    def test_all_middleware_together(self, mock_crawler, mock_spider):
        """Test ALL middleware components process requests without conflicts."""
        from BDNewsPaper.stealth_headers import StealthHeadersMiddleware
        from BDNewsPaper.cloudflare_bypass import CloudflareBypassMiddleware
        from BDNewsPaper.middlewares import (
            SmartRetryMiddleware,
            CircuitBreakerMiddleware,
            UserAgentMiddleware,
        )
        
        # Initialize all middlewares
        stealth = StealthHeadersMiddleware.from_crawler(mock_crawler)
        cf_bypass = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        retry = SmartRetryMiddleware(mock_crawler.settings)
        circuit = CircuitBreakerMiddleware()
        ua = UserAgentMiddleware()
        
        # Create a test request
        request = Request(url='https://example.com/article')
        
        # Process through ALL middlewares in order
        middlewares = [ua, stealth, circuit, cf_bypass]
        
        for mw in middlewares:
            if hasattr(mw, 'process_request'):
                result = mw.process_request(request, mock_spider)
                # Should return None (pass through) or a modified request
                assert result is None or isinstance(result, Request)
        
        # Verify headers are set
        assert 'User-Agent' in request.headers
    
    def test_middleware_response_chain_all(self, mock_crawler, mock_spider):
        """Test ALL middleware process response without conflicts."""
        from BDNewsPaper.stealth_headers import StealthHeadersMiddleware
        from BDNewsPaper.cloudflare_bypass import CloudflareBypassMiddleware
        from BDNewsPaper.middlewares import (
            SmartRetryMiddleware,
            CircuitBreakerMiddleware,
        )
        
        # Initialize middlewares
        stealth = StealthHeadersMiddleware.from_crawler(mock_crawler)
        cf_bypass = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        retry = SmartRetryMiddleware(mock_crawler.settings)
        circuit = CircuitBreakerMiddleware()
        
        # Create request and successful response
        request = Request(url='https://example.com/article')
        response = HtmlResponse(
            url='https://example.com/article',
            request=request,
            body=b'<html><head><title>Test</title></head><body>Content</body></html>',
            status=200,
        )
        
        # Process through response middlewares (reverse order)
        middlewares = [circuit, retry, cf_bypass]
        
        current_response = response
        for mw in middlewares:
            if hasattr(mw, 'process_response'):
                result = mw.process_response(request, current_response, mock_spider)
                assert result is not None
                if isinstance(result, Response):
                    current_response = result
        
        # Final response should be valid
        assert current_response.status == 200


# ==============================================================================
# Pipeline Integration Tests
# ==============================================================================

class TestPipelineIntegration:
    """Test pipeline components work together without conflicts."""
    
    @pytest.fixture
    def mock_spider(self):
        """Create a mock spider."""
        spider = MagicMock(spec=Spider)
        spider.name = 'test_spider'
        spider.logger = MagicMock()
        return spider
    
    @pytest.fixture
    def valid_item(self):
        """Create a valid article item."""
        return NewsArticleItem(
            headline="Test Headline with Sufficient Content",
            article_body="This is a comprehensive test article body that contains "
                        "enough content to pass all validation checks. " * 10,
            url="https://example.com/valid-article",
            paper_name="Test Paper",
            publication_date="2024-12-25T10:00:00+06:00",
            category="Test",
            author="Test Author",
        )
    
    @pytest.fixture
    def invalid_item(self):
        """Create an invalid article item."""
        return NewsArticleItem(
            headline="",  # Empty headline
            article_body="Short",  # Too short
            url="invalid-url",  # Invalid URL
            paper_name="Test",
        )
    
    def test_validation_pipeline(self, mock_spider, valid_item):
        """Test ValidationPipeline accepts valid items."""
        from BDNewsPaper.pipelines import ValidationPipeline
        
        pipeline = ValidationPipeline()
        result = pipeline.process_item(valid_item, mock_spider)
        
        assert result['headline'] == valid_item['headline']
    
    def test_validation_pipeline_rejects_invalid(self, mock_spider, invalid_item):
        """Test ValidationPipeline rejects invalid items."""
        from BDNewsPaper.pipelines import ValidationPipeline
        
        pipeline = ValidationPipeline()
        
        with pytest.raises(DropItem):
            pipeline.process_item(invalid_item, mock_spider)
    
    def test_clean_article_pipeline(self, mock_spider, valid_item):
        """Test CleanArticlePipeline cleans content."""
        from BDNewsPaper.pipelines import CleanArticlePipeline
        
        # Add some HTML to clean
        valid_item['article_body'] = "<p>Test content</p> with HTML " * 20
        
        pipeline = CleanArticlePipeline()
        result = pipeline.process_item(valid_item, mock_spider)
        
        # HTML should be removed
        assert '<p>' not in result.get('article_body', '')
    
    def test_pipeline_chain_no_conflicts(self, mock_spider, valid_item):
        """Test full pipeline chain processes item without conflicts."""
        from BDNewsPaper.pipelines import (
            ValidationPipeline,
            CleanArticlePipeline,
            LanguageDetectionPipeline,
            ContentQualityPipeline,
        )
        
        # Create pipeline instances
        validation = ValidationPipeline()
        clean = CleanArticlePipeline()
        language = LanguageDetectionPipeline(enabled=True, strict=False)
        quality = ContentQualityPipeline()
        
        # Process through chain
        item = valid_item
        item = validation.process_item(item, mock_spider)
        item = clean.process_item(item, mock_spider)
        item = language.process_item(item, mock_spider)
        item = quality.process_item(item, mock_spider)
        
        # Item should still be valid
        assert item['headline']
        assert item['article_body']
        assert item['url']


# ==============================================================================
# Spider Smoke Tests
# ==============================================================================

class TestSpiderSmoke:
    """Smoke tests for spider functionality."""
    
    @pytest.fixture
    def spider_classes(self):
        """Get list of all spider classes."""
        from BDNewsPaper.spiders import (
            bssnews, tbsnews, prothomalo,
        )
        # Import a few key spiders
        return [
            ('bssnews', bssnews.BSSNewsSpider),
            ('tbsnews', tbsnews.TBSNewsSpider),
        ]
    
    def test_smoke_test_spider_exists(self):
        """Test that SmokeTestSpider can be imported."""
        from BDNewsPaper.spiders.smoketest import SmokeTestSpider
        
        assert SmokeTestSpider.name == 'smoketest'
        assert SmokeTestSpider.paper_name == 'Smoke Test Paper'
    
    def test_smoke_test_spider_init(self):
        """Test SmokeTestSpider initialization."""
        from BDNewsPaper.spiders.smoketest import SmokeTestSpider
        
        spider = SmokeTestSpider()
        assert spider.name == 'smoketest'
        assert spider.max_items == 3
    
    def test_smoke_test_spider_start_requests(self):
        """Test SmokeTestSpider generates start requests."""
        from BDNewsPaper.spiders.smoketest import SmokeTestSpider
        
        spider = SmokeTestSpider()
        requests = list(spider.start_requests())
        
        assert len(requests) > 0
        assert all(isinstance(r, Request) for r in requests)
        assert all('httpbin.org' in r.url for r in requests)
    
    def test_base_spider_inheritance(self):
        """Test that spiders properly inherit from BaseNewsSpider."""
        from BDNewsPaper.spiders.base_spider import BaseNewsSpider
        from BDNewsPaper.spiders.bssnews import BSSNewsSpider
        from BDNewsPaper.spiders.tbsnews import TBSNewsSpider
        
        assert issubclass(BSSNewsSpider, BaseNewsSpider)
        assert issubclass(TBSNewsSpider, BaseNewsSpider)
    
    def test_spider_required_attributes(self):
        """Test that spiders have required attributes."""
        from BDNewsPaper.spiders.bssnews import BSSNewsSpider
        from BDNewsPaper.spiders.tbsnews import TBSNewsSpider
        
        for SpiderClass in [BSSNewsSpider, TBSNewsSpider]:
            assert hasattr(SpiderClass, 'name')
            assert hasattr(SpiderClass, 'paper_name')
            assert hasattr(SpiderClass, 'allowed_domains')


# ==============================================================================
# Full Integration Smoke Test
# ==============================================================================

class TestFullIntegration:
    """Full integration smoke test."""
    
    def test_settings_load(self):
        """Test that settings module loads correctly."""
        from BDNewsPaper import settings
        
        assert hasattr(settings, 'BOT_NAME')
        assert settings.BOT_NAME == 'BDNewsPaper'
        assert hasattr(settings, 'SPIDER_MODULES')
        assert hasattr(settings, 'ITEM_PIPELINES')
        assert hasattr(settings, 'DOWNLOADER_MIDDLEWARES')
    
    def test_middleware_order_valid(self):
        """Test that middleware priorities don't conflict."""
        from BDNewsPaper import settings
        
        middlewares = settings.DOWNLOADER_MIDDLEWARES
        
        # Get all priority values (excluding None/disabled)
        priorities = [v for v in middlewares.values() if v is not None]
        
        # Check no duplicate priorities
        assert len(priorities) == len(set(priorities)), "Duplicate middleware priorities found"
    
    def test_pipeline_order_valid(self):
        """Test that pipeline priorities don't conflict."""
        from BDNewsPaper import settings
        
        pipelines = settings.ITEM_PIPELINES
        priorities = list(pipelines.values())
        
        # Check no duplicate priorities
        assert len(priorities) == len(set(priorities)), "Duplicate pipeline priorities found"
        
        # Check order makes sense (validation before cleaning)
        # Lower number = runs first
        validation_priority = pipelines.get('BDNewsPaper.pipelines.ValidationPipeline', 0)
        clean_priority = pipelines.get('BDNewsPaper.pipelines.CleanArticlePipeline', 0)
        
        assert validation_priority < clean_priority, "Validation should run before cleaning"
    
    def test_items_schema(self):
        """Test NewsArticleItem has required fields."""
        from BDNewsPaper.items import NewsArticleItem
        
        item = NewsArticleItem()
        
        # Check key fields exist
        required_fields = ['headline', 'article_body', 'url', 'paper_name']
        for field in required_fields:
            assert field in item.fields, f"Missing required field: {field}"
    
    def test_config_module(self):
        """Test config module loads correctly."""
        from BDNewsPaper.config import (
            DHAKA_TZ,
            DEFAULT_START_DATE,
            get_default_end_date,
        )
        
        assert DHAKA_TZ is not None
        assert DEFAULT_START_DATE is not None
        assert get_default_end_date() is not None


# ==============================================================================
# All Spiders Import Test
# ==============================================================================

class TestAllSpidersImport:
    """Test that all spiders can be imported without errors."""
    
    def test_all_spiders_import(self):
        """Import all spider modules and verify they work."""
        from pathlib import Path
        import importlib
        
        spider_dir = Path(__file__).parent.parent / 'BDNewsPaper' / 'spiders'
        failed = []
        success = []
        
        for py_file in sorted(spider_dir.glob('*.py')):
            if py_file.name.startswith('_') or py_file.name == '__pycache__':
                continue
            
            module_name = f"BDNewsPaper.spiders.{py_file.stem}"
            try:
                mod = importlib.import_module(module_name)
                success.append(module_name)
            except Exception as e:
                failed.append((module_name, str(e)))
        
        if failed:
            msg = f"Successfully imported {len(success)} spiders, but {len(failed)} failed:\n"
            for mod, err in failed:
                msg += f"  - {mod}: {err}\n"
            pytest.fail(msg)
        
        # Should have imported many spiders
        assert len(success) >= 50, f"Expected 50+ spiders, only found {len(success)}"
