"""
Item and Field Processor Unit Tests
====================================
Tests for field processor functions, NewsArticleItem auto-metadata,
and FallbackExtractionPipeline.
"""

import hashlib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from BDNewsPaper.items import (
    NewsArticleItem,
    clean_text,
    validate_url,
    normalize_date,
    clean_author,
    extract_keywords,
)
from BDNewsPaper.pipelines import FallbackExtractionPipeline


# ============================================================================
# clean_text
# ============================================================================

class TestCleanText:
    """Tests for the clean_text field processor."""

    def test_none_returns_empty(self):
        assert clean_text(None) == ""

    def test_html_tags_removed(self):
        result = clean_text("<p>Hello <b>world</b></p>")
        assert "<p>" not in result
        assert "<b>" not in result
        assert "Hello world" == result

    def test_html_entities_replaced(self):
        result = clean_text("foo &amp; bar &lt;baz&gt;")
        assert result == "foo & bar <baz>"

    def test_whitespace_normalized(self):
        result = clean_text("hello   world\n\tnewline")
        assert result == "hello world newline"

    def test_list_input_joined(self):
        result = clean_text(["hello", "world"])
        assert result == "hello world"

    def test_empty_string(self):
        assert clean_text("") == ""


# ============================================================================
# validate_url
# ============================================================================

class TestValidateUrl:
    """Tests for the validate_url field processor."""

    def test_valid_http(self):
        assert validate_url("http://example.com/article") == "http://example.com/article"

    def test_valid_https(self):
        assert validate_url("https://example.com/article") == "https://example.com/article"

    def test_missing_scheme_returns_none(self):
        assert validate_url("www.example.com/article") is None

    def test_none_returns_none(self):
        assert validate_url(None) is None

    def test_empty_returns_none(self):
        assert validate_url("") is None


# ============================================================================
# normalize_date
# ============================================================================

class TestNormalizeDate:
    """Tests for the normalize_date field processor."""

    def test_iso_format(self):
        result = normalize_date("2024-12-25")
        assert result == "2024-12-25T00:00:00"

    def test_human_format(self):
        result = normalize_date("December 25, 2024")
        assert result == "2024-12-25T00:00:00"

    def test_datetime_object(self):
        dt = datetime(2024, 12, 25, 10, 30, 0)
        result = normalize_date(dt)
        assert result == "2024-12-25T10:30:00"

    def test_none_returns_unknown(self):
        assert normalize_date(None) == "Unknown"

    def test_empty_returns_unknown(self):
        assert normalize_date("") == "Unknown"

    def test_already_unknown(self):
        assert normalize_date("Unknown") == "Unknown"


# ============================================================================
# clean_author
# ============================================================================

class TestCleanAuthor:
    """Tests for the clean_author field processor."""

    def test_string_input(self):
        assert clean_author("John Doe") == "John Doe"

    def test_list_input(self):
        result = clean_author(["Alice", "Bob"])
        assert result == "Alice, Bob"

    def test_empty_returns_unknown(self):
        assert clean_author("") == "Unknown"

    def test_none_returns_unknown(self):
        assert clean_author(None) == "Unknown"

    def test_list_with_empty_strings(self):
        result = clean_author(["", "", ""])
        assert result == "Unknown"


# ============================================================================
# extract_keywords
# ============================================================================

class TestExtractKeywords:
    """Tests for the extract_keywords field processor."""

    def test_string_input(self):
        result = extract_keywords("politics")
        assert result == "politics"

    def test_list_of_strings(self):
        result = extract_keywords(["politics", "economy"])
        assert result == "politics, economy"

    def test_list_of_dicts(self):
        result = extract_keywords([{"name": "politics"}, {"name": "economy"}])
        assert result == "politics, economy"

    def test_none_returns_none(self):
        assert extract_keywords(None) is None

    def test_empty_list_returns_none(self):
        assert extract_keywords([]) is None


# ============================================================================
# NewsArticleItem auto-metadata
# ============================================================================

class TestNewsArticleItemMetadata:
    """Tests for NewsArticleItem automatic metadata generation."""

    def test_word_count_auto_generated(self):
        item = NewsArticleItem()
        item['article_body'] = "one two three four five"
        assert item['word_count'] == 5

    def test_content_hash_auto_generated(self):
        item = NewsArticleItem()
        item['headline'] = "Test Headline"
        item['article_body'] = "some body text"
        expected = hashlib.sha256("Test Headlinesome body text".encode('utf-8')).hexdigest()
        assert item['content_hash'] == expected

    def test_source_language_english(self):
        item = NewsArticleItem()
        item['article_body'] = "This is an English article body"
        assert item['source_language'] == "English"

    def test_source_language_bengali(self):
        item = NewsArticleItem()
        item['article_body'] = "এটি একটি বাংলা নিবন্ধ"
        assert item['source_language'] == "Bengali"

    def test_scraped_at_auto_generated(self):
        item = NewsArticleItem()
        item['article_body'] = "some content here"
        assert 'scraped_at' in item
        # Should be a valid ISO timestamp
        datetime.fromisoformat(item['scraped_at'])

    def test_reading_time_minutes(self):
        item = NewsArticleItem()
        # 400 words -> 2 minutes at 200 wpm
        item['article_body'] = " ".join(["word"] * 400)
        assert item['reading_time_minutes'] == 2

    def test_is_valid_with_all_fields(self):
        item = NewsArticleItem()
        item['headline'] = "Valid Headline"
        item['article_body'] = "Valid body content"
        item['url'] = "https://example.com/test"
        item['paper_name'] = "Test Paper"
        assert item.is_valid() is True

    def test_is_valid_missing_field(self):
        item = NewsArticleItem()
        item['headline'] = "Valid Headline"
        # Missing article_body, url, paper_name
        assert item.is_valid() is False

    def test_to_dict_excludes_empty(self):
        item = NewsArticleItem()
        item['headline'] = "Test"
        item['article_body'] = ""
        result = item.to_dict()
        assert 'headline' in result
        assert 'article_body' not in result

    def test_get_required_fields(self):
        item = NewsArticleItem()
        required = item.get_required_fields()
        assert set(required) == {'headline', 'article_body', 'paper_name', 'url'}


# ============================================================================
# FallbackExtractionPipeline
# ============================================================================

class TestFallbackExtractionPipeline:
    """Tests for FallbackExtractionPipeline."""

    @pytest.fixture
    def mock_spider(self):
        spider = MagicMock()
        spider.name = 'test_spider'
        spider.logger = MagicMock()
        return spider

    @staticmethod
    def _make_item(**kwargs):
        """Helper to build a dict-based item.

        Uses a plain dict so that arbitrary internal fields like ``_raw_html``
        can be set without declaring them on ``NewsArticleItem``.  The pipeline
        wraps items with ``ItemAdapter``, which handles dicts transparently.
        """
        return dict(**kwargs)

    def test_disabled_passes_through(self, mock_spider):
        pipeline = FallbackExtractionPipeline(enabled=False)
        item = self._make_item(
            headline="H",
            article_body="short",
            url="https://example.com/a",
            paper_name="P",
        )
        result = pipeline.process_item(item, mock_spider)
        assert result is item

    def test_sufficient_content_passes_through(self, mock_spider):
        pipeline = FallbackExtractionPipeline(enabled=True, min_body_length=10)
        body = "This body is long enough to pass the minimum length requirement."
        item = self._make_item(
            headline="Sufficient Headline",
            article_body=body,
            url="https://example.com/a",
            paper_name="P",
        )
        result = pipeline.process_item(item, mock_spider)
        assert result is item
        assert result['article_body'] == body

    def test_no_raw_html_passes_through(self, mock_spider):
        pipeline = FallbackExtractionPipeline(enabled=True, min_body_length=50)
        item = self._make_item(
            headline="H",
            article_body="short",
            url="https://example.com/a",
            paper_name="P",
        )
        result = pipeline.process_item(item, mock_spider)
        assert result is item
        assert result['article_body'] == "short"

    def test_fallback_triggered_on_short_body(self, mock_spider):
        pipeline = FallbackExtractionPipeline(enabled=True, min_body_length=50)

        mock_extraction_result = MagicMock()
        mock_extraction_result.is_valid.return_value = True
        mock_extraction_result.body = "Extracted body that is definitely long enough to pass validation."
        mock_extraction_result.headline = "Extracted Headline"
        mock_extraction_result.source = "json-ld"
        mock_extraction_result.author = "Extracted Author"
        mock_extraction_result.publication_date = "2024-01-01"
        mock_extraction_result.image_url = "https://example.com/img.jpg"

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        item = self._make_item(
            headline="H",
            article_body="short",
            url="https://example.com/a",
            paper_name="P",
            _raw_html="<html><body>Full page</body></html>",
        )

        with patch.object(pipeline, '_get_extractor', return_value=mock_extractor):
            result = pipeline.process_item(item, mock_spider)

        assert result['article_body'] == mock_extraction_result.body
        assert pipeline.stats['fallback_success'] == 1

    def test_exception_handled_gracefully(self, mock_spider):
        pipeline = FallbackExtractionPipeline(enabled=True, min_body_length=50)

        mock_extractor = MagicMock()
        mock_extractor.extract.side_effect = RuntimeError("extractor crashed")

        item = self._make_item(
            headline="H",
            article_body="short",
            url="https://example.com/a",
            paper_name="P",
            _raw_html="<html><body>Full page</body></html>",
        )

        with patch.object(pipeline, '_get_extractor', return_value=mock_extractor):
            result = pipeline.process_item(item, mock_spider)

        # Item returned despite error
        assert result is item
        assert pipeline.stats['fallback_failed'] == 1
        mock_spider.logger.warning.assert_called_once()
