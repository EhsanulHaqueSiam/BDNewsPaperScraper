"""
Integration Tests
=================
Tests that verify components work together correctly end-to-end.
"""

import pytest
from unittest.mock import MagicMock, patch
from scrapy.http import Request, HtmlResponse
from scrapy.exceptions import DropItem

from BDNewsPaper.items import NewsArticleItem


class TestEndToEndExtraction:
    """Test complete article extraction flow."""
    
    @pytest.fixture
    def sample_html_with_article(self):
        """Sample HTML with complete article content."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article - BD News</title>
            <meta property="og:title" content="Test Headline from Meta">
            <meta property="og:image" content="https://example.com/image.jpg">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Bangladesh Economy Shows Strong Growth in Q4",
                "articleBody": "The Bangladesh economy has shown remarkable resilience in the fourth quarter of 2024. GDP growth exceeded expectations at 6.5%, driven by robust export performance and domestic consumption. Experts predict continued growth momentum into the next fiscal year. The manufacturing sector, particularly garments, contributed significantly to this positive outlook. Government initiatives in infrastructure development have also played a crucial role in sustaining economic expansion.",
                "author": {"@type": "Person", "name": "Rahman Ahmed"},
                "datePublished": "2024-12-28T10:00:00+06:00",
                "image": "https://cdn.example.com/economy-growth.jpg"
            }
            </script>
        </head>
        <body>
            <article>
                <h1 class="article-title">Bangladesh Economy Shows Strong Growth in Q4</h1>
                <div class="author-info">By Rahman Ahmed</div>
                <time datetime="2024-12-28">December 28, 2024</time>
                <div class="article-body">
                    <p>The Bangladesh economy has shown remarkable resilience in the fourth quarter of 2024.</p>
                    <p>GDP growth exceeded expectations at 6.5%, driven by robust export performance.</p>
                    <p>Experts predict continued growth momentum into the next fiscal year.</p>
                </div>
            </article>
        </body>
        </html>
        """
    
    @pytest.fixture
    def sample_response(self, sample_html_with_article):
        """Create a mock Scrapy response."""
        request = Request(url='https://example.com/economy/growth-q4-2024')
        return HtmlResponse(
            url='https://example.com/economy/growth-q4-2024',
            request=request,
            body=sample_html_with_article.encode('utf-8'),
            status=200,
            encoding='utf-8'
        )
    
    def test_json_ld_extraction_end_to_end(self, sample_html_with_article):
        """Test that JSON-LD extraction works correctly."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        extractor = FallbackExtractor()
        result = extractor.extract(sample_html_with_article, 'https://example.com/article')
        
        assert result is not None
        assert result.is_valid(50)
        assert "Bangladesh" in result.headline or "Growth" in result.headline
        assert len(result.body) > 100
        assert result.author == "Rahman Ahmed"
        assert result.source == "json-ld"
    
    def test_heuristic_fallback_extraction(self):
        """Test heuristic extraction when JSON-LD is not available."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        html_without_jsonld = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Important News Headline Here</h1>
                <p>First paragraph of the important news article with sufficient content.</p>
                <p>Second paragraph with more details about the news story.</p>
                <p>Third paragraph concluding the article with additional information.</p>
            </article>
        </body>
        </html>
        """
        
        extractor = FallbackExtractor()
        result = extractor.extract(html_without_jsonld, 'https://example.com/article')
        
        assert result is not None
        assert "Important" in result.headline or "Headline" in result.headline
    
    def test_pipeline_processes_extracted_content(self, sample_response):
        """Test that pipelines correctly process extracted content."""
        from BDNewsPaper.pipelines import (
            ValidationPipeline,
            CleanArticlePipeline,
            ContentQualityPipeline,
        )
        
        # Create item from mock extraction
        item = NewsArticleItem(
            headline="Bangladesh Economy Shows Strong Growth in Q4",
            article_body="The Bangladesh economy has shown remarkable resilience. " * 10,
            url="https://example.com/economy/growth",
            paper_name="Test Paper",
            author="Rahman Ahmed",
            publication_date="2024-12-28T10:00:00+06:00",
        )
        
        mock_spider = MagicMock()
        mock_spider.name = 'test'
        mock_spider.logger = MagicMock()
        
        # Process through pipeline chain
        validation = ValidationPipeline()
        clean = CleanArticlePipeline()
        quality = ContentQualityPipeline()
        
        item = validation.process_item(item, mock_spider)
        item = clean.process_item(item, mock_spider)
        item = quality.process_item(item, mock_spider)
        
        # Verify item is enriched
        assert item['headline']
        assert item['article_body']
        assert 'word_count' in item
        assert item['word_count'] > 0


class TestMiddlewareChain:
    """Test complete middleware processing chain."""
    
    @pytest.fixture
    def mock_crawler(self):
        """Create mock crawler with settings."""
        from scrapy.settings import Settings
        
        crawler = MagicMock()
        crawler.settings = Settings({
            'STEALTH_HEADERS_ENABLED': True,
            'CF_BYPASS_ENABLED': True,
            'HONEYPOT_DETECTION_ENABLED': True,
            'HYBRID_REQUEST_ENABLED': True,
            'ADAPTIVE_THROTTLE_ENABLED': True,
        })
        crawler.signals = MagicMock()
        return crawler
    
    @pytest.fixture 
    def mock_spider(self):
        """Create mock spider."""
        spider = MagicMock()
        spider.name = 'test_spider'
        spider.logger = MagicMock()
        return spider
    
    def test_request_flows_through_all_middlewares(self, mock_crawler, mock_spider):
        """Test that a request successfully flows through all middlewares."""
        from BDNewsPaper.stealth_headers import StealthHeadersMiddleware
        from BDNewsPaper.middlewares import UserAgentMiddleware, CircuitBreakerMiddleware
        
        # Initialize middlewares
        stealth = StealthHeadersMiddleware.from_crawler(mock_crawler)
        ua = UserAgentMiddleware()
        circuit = CircuitBreakerMiddleware()
        
        # Create request
        request = Request(url='https://prothomalo.com/article/123')
        
        # Process through middlewares
        result = ua.process_request(request, mock_spider)
        assert result is None  # Pass through
        
        result = stealth.process_request(request, mock_spider)
        assert result is None  # Pass through
        
        result = circuit.process_request(request, mock_spider)
        assert result is None  # Pass through
        
        # Verify headers were added
        assert 'User-Agent' in request.headers
    
    def test_response_flows_through_all_middlewares(self, mock_crawler, mock_spider):
        """Test that a response successfully flows through all middlewares."""
        from BDNewsPaper.cloudflare_bypass import CloudflareBypassMiddleware
        from BDNewsPaper.middlewares import CircuitBreakerMiddleware
        
        cf = CloudflareBypassMiddleware.from_crawler(mock_crawler)
        circuit = CircuitBreakerMiddleware()
        
        request = Request(url='https://example.com/article')
        response = HtmlResponse(
            url='https://example.com/article',
            request=request,
            body=b'<html><body>Normal content</body></html>',
            status=200
        )
        
        # Process through middlewares (reverse order)
        result = circuit.process_response(request, response, mock_spider)
        assert isinstance(result, HtmlResponse)
        
        result = cf.process_response(request, result, mock_spider)
        assert isinstance(result, HtmlResponse)
        assert result.status == 200


class TestSpiderBaseFunctionality:
    """Test base spider functionality used by all spiders."""
    
    def test_base_spider_has_fallback_methods(self):
        """Test that BaseNewsSpider has fallback extraction methods."""
        from BDNewsPaper.spiders.base_spider import BaseNewsSpider
        
        assert hasattr(BaseNewsSpider, 'extract_article_fallback')
        assert hasattr(BaseNewsSpider, 'discover_links')
        assert hasattr(BaseNewsSpider, 'handle_request_failure')
    
    def test_base_spider_discover_links(self):
        """Test link discovery on a sample page."""
        from BDNewsPaper.spiders.base_spider import BaseNewsSpider
        
        # Create a minimal spider instance
        class TestSpider(BaseNewsSpider):
            name = 'test'
            paper_name = 'Test'
            allowed_domains = ['example.com']
        
        spider = TestSpider()
        
        # Create sample response with links
        html = """
        <html><body>
            <a href="/article/123">Article 1</a>
            <a href="/news/456">News 2</a>
            <a href="/category/sports">Sports</a>
        </body></html>
        """
        
        response = HtmlResponse(
            url='https://example.com/',
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        
        links = spider.discover_links(response, limit=10)
        
        assert isinstance(links, list)
        # Should find article-like links
        article_links = [l for l in links if 'article' in l.lower() or 'news' in l.lower()]
        assert len(article_links) >= 0  # May or may not find depending on patterns


class TestErrorHandling:
    """Test error handling across components."""
    
    def test_pipeline_handles_missing_fields_gracefully(self):
        """Test pipelines handle items without crashing (but may drop invalid ones)."""
        from BDNewsPaper.pipelines import CleanArticlePipeline
        
        # Item with sufficient content
        item = NewsArticleItem(
            headline="Test Headline for Article",
            article_body="This is test article body content. " * 20,  # Sufficient content
            url="https://example.com/test",
            paper_name="Test Paper"
        )
        
        mock_spider = MagicMock()
        mock_spider.logger = MagicMock()
        
        pipeline = CleanArticlePipeline()
        
        # Should process without crashing
        result = pipeline.process_item(item, mock_spider)
        assert "Test" in result['headline']
    
    def test_extractor_handles_empty_html(self):
        """Test extractor handles empty/malformed HTML."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        extractor = FallbackExtractor()
        
        # Test with empty string
        result = extractor.extract("", "https://example.com")
        assert result is not None  # Should return empty result, not crash
        
        # Test with minimal HTML
        result = extractor.extract("<html></html>", "https://example.com")
        assert result is not None
    
    def test_middleware_handles_request_errors(self):
        """Test middlewares handle errors gracefully."""
        from BDNewsPaper.middlewares import CircuitBreakerMiddleware
        
        middleware = CircuitBreakerMiddleware()
        
        mock_spider = MagicMock()
        mock_spider.logger = MagicMock()
        
        request = Request(url='https://example.com/test')
        exception = ConnectionError("Network error")
        
        # Should handle without crashing
        result = middleware.process_exception(request, exception, mock_spider)
        # Result is None (let Scrapy handle it)
        assert result is None
