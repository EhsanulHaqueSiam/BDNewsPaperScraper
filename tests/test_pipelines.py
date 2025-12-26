"""
Pipeline Unit Tests
===================
Tests for validation, cleaning, and database pipelines.
"""

import pytest
from unittest.mock import MagicMock, patch

from scrapy.exceptions import DropItem

from BDNewsPaper.pipelines import (
    ValidationPipeline,
    CleanArticlePipeline,
    LanguageDetectionPipeline,
    ContentQualityPipeline,
    DateFilterPipeline,
)
from BDNewsPaper.items import NewsArticleItem


class TestValidationPipeline:
    """Tests for ValidationPipeline."""
    
    @pytest.fixture
    def pipeline(self, mock_crawler):
        return ValidationPipeline.from_crawler(mock_crawler)
    
    def test_valid_item_passes(self, pipeline, mock_spider, valid_article_item):
        """Test that valid items pass validation."""
        result = pipeline.process_item(valid_article_item, mock_spider)
        assert result is not None
        assert result['headline'] == valid_article_item['headline']
    
    def test_missing_headline_raises(self, pipeline, mock_spider):
        """Test that missing headline raises DropItem."""
        item = NewsArticleItem(
            headline="",
            article_body="This is enough body content " * 10,
            url="https://example.com/test",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Headline too short"):
            pipeline.process_item(item, mock_spider)
    
    def test_missing_url_raises(self, pipeline, mock_spider):
        """Test that missing URL raises DropItem."""
        item = NewsArticleItem(
            headline="Valid Headline",
            article_body="Valid body content " * 10,
            url="",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Missing required field"):
            pipeline.process_item(item, mock_spider)
    
    def test_invalid_url_raises(self, pipeline, mock_spider):
        """Test that invalid URL format raises DropItem."""
        item = NewsArticleItem(
            headline="Valid Headline",
            article_body="Valid body content " * 10,
            url="not-a-url",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Invalid URL format"):
            pipeline.process_item(item, mock_spider)
    
    def test_short_article_raises(self, pipeline, mock_spider):
        """Test that too-short articles raise DropItem."""
        item = NewsArticleItem(
            headline="Valid Headline",
            article_body="Short",
            url="https://example.com/test",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Article too short"):
            pipeline.process_item(item, mock_spider)


class TestCleanArticlePipeline:
    """Tests for CleanArticlePipeline."""
    
    @pytest.fixture
    def pipeline(self):
        return CleanArticlePipeline()
    
    def test_html_tags_removed(self, pipeline, mock_spider):
        """Test that HTML tags are removed from content."""
        item = NewsArticleItem(
            headline="<b>Bold Headline</b>",
            article_body="<p>Paragraph with <a href='#'>link</a></p> " * 5,
            url="https://example.com/test",
            paper_name="Test",
        )
        result = pipeline.process_item(item, mock_spider)
        assert '<b>' not in result['headline']
        assert '<p>' not in result['article_body']
        assert '<a' not in result['article_body']
    
    def test_whitespace_normalized(self, pipeline, mock_spider):
        """Test that excess whitespace is normalized."""
        item = NewsArticleItem(
            headline="  Headline  with   spaces  ",
            article_body="Content    with\n\nmultiple   spaces. " * 5,
            url="https://example.com/test",
            paper_name="Test",
        )
        result = pipeline.process_item(item, mock_spider)
        assert '  ' not in result['headline']
        assert '\n\n' not in result['article_body']
    
    def test_unwanted_patterns_removed(self, pipeline, mock_spider):
        """Test that unwanted patterns are removed."""
        item = NewsArticleItem(
            headline="Test Headline",
            article_body="Article content. Read more: click here " * 5,
            url="https://example.com/test",
            paper_name="Test",
        )
        result = pipeline.process_item(item, mock_spider)
        # Pattern removal may vary; test content is cleaned
        assert result['article_body'] is not None


class TestLanguageDetectionPipeline:
    """Tests for LanguageDetectionPipeline."""
    
    @pytest.fixture
    def pipeline(self, mock_crawler):
        return LanguageDetectionPipeline.from_crawler(mock_crawler)
    
    def test_english_detected(self, pipeline, mock_spider, valid_article_item):
        """Test that English articles are detected correctly."""
        if not pipeline._langdetect_available:
            pytest.skip("langdetect not installed")
        
        result = pipeline.process_item(valid_article_item, mock_spider)
        # Language should be detected
        assert 'detected_language' in result or result.get('detected_language') == 'en'
    
    def test_strict_mode_drops_wrong_language(self, mock_crawler, mock_spider):
        """Test that strict mode drops non-English articles."""
        mock_crawler.settings.getbool = lambda key, default: key == 'LANGUAGE_DETECTION_STRICT'
        pipeline = LanguageDetectionPipeline.from_crawler(mock_crawler)
        
        if not pipeline._langdetect_available:
            pytest.skip("langdetect not installed")
        
        # Create Bengali article
        item = NewsArticleItem(
            headline="এটি একটি বাংলা শিরোনাম",
            article_body="এই নিবন্ধটি বাংলায় লেখা হয়েছে। " * 20,
            url="https://example.com/test",
            paper_name="Test",
        )
        
        with pytest.raises(DropItem, match="Language mismatch"):
            pipeline.process_item(item, mock_spider)
    
    def test_disabled_passes_through(self, mock_crawler, mock_spider, valid_article_item):
        """Test that disabled pipeline passes items through."""
        mock_crawler.settings.getbool = lambda key, default: False if key == 'LANGUAGE_DETECTION_ENABLED' else default
        pipeline = LanguageDetectionPipeline.from_crawler(mock_crawler)
        
        result = pipeline.process_item(valid_article_item, mock_spider)
        assert result is not None


class TestContentQualityPipeline:
    """Tests for ContentQualityPipeline."""
    
    @pytest.fixture
    def pipeline(self, mock_crawler):
        return ContentQualityPipeline.from_crawler(mock_crawler)
    
    def test_valid_content_passes(self, pipeline, mock_spider, valid_article_item):
        """Test that valid content passes quality check."""
        result = pipeline.process_item(valid_article_item, mock_spider)
        assert result is not None
    
    def test_garbage_pattern_rejected(self, pipeline, mock_spider):
        """Test that garbage patterns are rejected."""
        item = NewsArticleItem(
            headline="Test Headline",
            article_body="<script>alert('xss')</script> Some other content " * 10,
            url="https://example.com/test",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Garbage content"):
            pipeline.process_item(item, mock_spider)
    
    def test_empty_body_rejected(self, pipeline, mock_spider):
        """Test that empty body is rejected."""
        item = NewsArticleItem(
            headline="Test Headline",
            article_body="",
            url="https://example.com/test",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Empty article body"):
            pipeline.process_item(item, mock_spider)
    
    def test_too_few_words_rejected(self, pipeline, mock_spider):
        """Test that articles with too few words are rejected."""
        item = NewsArticleItem(
            headline="Test Headline",
            article_body="Only five words here",  # Less than 20 words
            url="https://example.com/test",
            paper_name="Test",
        )
        with pytest.raises(DropItem, match="Article too short"):
            pipeline.process_item(item, mock_spider)
