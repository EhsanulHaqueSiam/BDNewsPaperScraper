"""
Test Configuration and Fixtures
================================
Shared pytest fixtures for BDNewsPaper tests.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

import scrapy
from scrapy.http import HtmlResponse, Request
from itemadapter import ItemAdapter

from BDNewsPaper.items import NewsArticleItem


# ==============================================================================
# Path Fixtures
# ==============================================================================

@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / 'fixtures'


@pytest.fixture
def project_root():
    """Path to project root."""
    return Path(__file__).parent.parent


# ==============================================================================
# Mock Spider Fixture
# ==============================================================================

@pytest.fixture
def mock_spider():
    """Create a mock spider for testing."""
    spider = MagicMock(spec=scrapy.Spider)
    spider.name = 'test_spider'
    spider.logger = MagicMock()
    return spider


@pytest.fixture
def mock_crawler():
    """Create a mock crawler with settings."""
    crawler = MagicMock()
    crawler.settings = MagicMock()
    crawler.settings.getint = lambda key, default=None: default
    crawler.settings.getfloat = lambda key, default=None: default
    crawler.settings.getbool = lambda key, default=None: default
    crawler.settings.getlist = lambda key, default=None: default or []
    crawler.settings.get = lambda key, default=None: default
    return crawler


# ==============================================================================
# Response Fixtures
# ==============================================================================

@pytest.fixture
def make_response():
    """Factory fixture to create mock HTML responses."""
    def _make_response(html_content: str, url: str = 'http://test.com/article'):
        request = Request(url=url)
        response = HtmlResponse(
            url=url,
            request=request,
            body=html_content.encode('utf-8'),
            encoding='utf-8',
        )
        return response
    return _make_response


@pytest.fixture
def sample_article_html():
    """Sample article HTML for testing parsers."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article Title</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": "Test Headline from JSON-LD",
            "articleBody": "This is the article body from JSON-LD. It contains test content.",
            "datePublished": "2024-12-25T10:00:00+06:00",
            "author": [{"@type": "Person", "name": "Test Author"}]
        }
        </script>
    </head>
    <body>
        <article>
            <h1>Test Headline from HTML</h1>
            <p class="byline">By Test Author</p>
            <div class="article-content">
                <p>This is the first paragraph of the article.</p>
                <p>This is the second paragraph with more content.</p>
                <p>This is the third paragraph concluding the article.</p>
            </div>
        </article>
    </body>
    </html>
    """


# ==============================================================================
# Item Fixtures
# ==============================================================================

@pytest.fixture
def valid_article_item():
    """Create a valid NewsArticleItem for testing."""
    return NewsArticleItem(
        headline="Test Headline with Sufficient Length",
        article_body="This is a test article body with enough content to pass validation. " * 10,
        url="https://example.com/test-article",
        paper_name="Test Paper",
        publication_date="2024-12-25T10:00:00+06:00",
        category="Test",
        author="Test Author",
    )


@pytest.fixture
def minimal_article_item():
    """Create a minimal NewsArticleItem with only required fields."""
    return NewsArticleItem(
        headline="Minimal Headline",
        article_body="Short body" * 10,
        url="https://example.com/minimal",
        paper_name="Test Paper",
    )


@pytest.fixture
def invalid_article_item():
    """Create an invalid NewsArticleItem for testing validation."""
    return NewsArticleItem(
        headline="",  # Empty headline
        article_body="Short",  # Too short
        url="invalid-url",  # Invalid URL
        paper_name="",  # Missing paper name
    )


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / 'test_articles.db')


# ==============================================================================
# Settings Fixtures
# ==============================================================================

@pytest.fixture
def default_settings():
    """Default scrapy settings for testing."""
    return {
        'DATABASE_PATH': ':memory:',
        'MIN_ARTICLE_LENGTH': 50,
        'MIN_HEADLINE_LENGTH': 5,
        'LANGUAGE_DETECTION_ENABLED': True,
        'LANGUAGE_DETECTION_STRICT': False,
        'EXPECTED_LANGUAGES': ['en'],
    }
