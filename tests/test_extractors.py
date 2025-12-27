"""
Tests for Smart Fallback Extraction Module
==========================================
Tests all 4 extraction layers: JSON-LD, Trafilatura, Heuristics, Regex
"""

import pytest
from unittest.mock import patch, MagicMock


# Sample HTML with JSON-LD
SAMPLE_HTML_JSONLD = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "Test Headline from JSON-LD",
        "articleBody": "This is the article body content from JSON-LD. It should be long enough to pass validation. Adding more text here.",
        "author": {"@type": "Person", "name": "John Doe"},
        "datePublished": "2024-12-28T10:00:00+06:00",
        "image": "https://example.com/image.jpg"
    }
    </script>
</head>
<body>
    <article>
        <h1>Fallback Headline</h1>
        <p>Fallback body content.</p>
    </article>
</body>
</html>
"""

# Sample HTML without JSON-LD
SAMPLE_HTML_HEURISTIC = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="OG Title Test">
    <meta property="og:image" content="https://example.com/og-image.jpg">
</head>
<body>
    <article>
        <h1 class="article-title">Heuristic Headline Test</h1>
        <div class="article-body">
            <p>First paragraph of the article content. This should be extracted.</p>
            <p>Second paragraph with more content. This is important text.</p>
            <p>Third paragraph concluding the article. Additional information here.</p>
        </div>
        <span class="author">Jane Smith</span>
        <time datetime="2024-12-28">December 28, 2024</time>
    </article>
</body>
</html>
"""

# Sample HTML with minimal content
SAMPLE_HTML_MINIMAL = """
<!DOCTYPE html>
<html>
<body>
    <h1>Simple Title</h1>
    <p>Short body.</p>
</body>
</html>
"""


class TestExtractionResult:
    """Test ExtractionResult dataclass."""
    
    def test_is_valid_with_sufficient_content(self):
        """Test validation with sufficient content."""
        from BDNewsPaper.extractors import ExtractionResult
        
        result = ExtractionResult(
            headline="Test Headline",
            body="This is a body with more than fifty characters of content for testing purposes.",
            source="test"
        )
        assert result.is_valid(min_body_length=50) is True
    
    def test_is_valid_with_short_content(self):
        """Test validation fails with short content."""
        from BDNewsPaper.extractors import ExtractionResult
        
        result = ExtractionResult(
            headline="Test",
            body="Short",
            source="test"
        )
        assert result.is_valid(min_body_length=50) is False
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        from BDNewsPaper.extractors import ExtractionResult
        
        result = ExtractionResult(
            headline="Test",
            body="Body content",
            author="Author",
            source="jsonld"
        )
        d = result.to_dict()
        assert d['headline'] == "Test"
        assert d['body'] == "Body content"
        assert d['author'] == "Author"
        assert d['source'] == "jsonld"


class TestJSONLDExtractor:
    """Test JSON-LD extraction."""
    
    def test_extract_from_jsonld(self):
        """Test extraction from JSON-LD structured data."""
        from BDNewsPaper.extractors import JSONLDExtractor
        
        extractor = JSONLDExtractor()
        result = extractor.extract(SAMPLE_HTML_JSONLD, "https://example.com/article")
        
        assert result is not None
        assert result.headline == "Test Headline from JSON-LD"
        assert "article body content" in result.body.lower()
        assert result.author == "John Doe"
        assert result.source == "json-ld"
    
    def test_extract_no_jsonld(self):
        """Test extraction returns None when no JSON-LD present."""
        from BDNewsPaper.extractors import JSONLDExtractor
        
        extractor = JSONLDExtractor()
        result = extractor.extract(SAMPLE_HTML_HEURISTIC, "https://example.com/article")
        
        # Should return empty result or None
        assert result is None or result.headline == ""


class TestHeuristicExtractor:
    """Test heuristic CSS selector extraction."""
    
    def test_extract_headline(self):
        """Test headline extraction via heuristics."""
        from BDNewsPaper.extractors import HeuristicExtractor
        
        extractor = HeuristicExtractor()
        result = extractor.extract(SAMPLE_HTML_HEURISTIC, "https://example.com/article")
        
        assert result is not None
        # Should extract from h1.article-title or og:title
        assert "Heuristic" in result.headline or "OG Title" in result.headline
    
    def test_extract_body_paragraphs(self):
        """Test body extraction from paragraphs."""
        from BDNewsPaper.extractors import HeuristicExtractor
        
        extractor = HeuristicExtractor()
        result = extractor.extract(SAMPLE_HTML_HEURISTIC, "https://example.com/article")
        
        assert result is not None
        assert len(result.body) > 50
        assert "paragraph" in result.body.lower()


class TestFallbackExtractor:
    """Test the complete fallback chain."""
    
    def test_fallback_chain_jsonld_first(self):
        """Test that JSON-LD is tried first in the chain."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        extractor = FallbackExtractor(min_body_length=50)
        result = extractor.extract(SAMPLE_HTML_JSONLD, "https://example.com/article")
        
        assert result is not None
        assert result.is_valid(50)
        assert result.source == "json-ld"
    
    def test_fallback_to_heuristics(self):
        """Test fallback to heuristics when JSON-LD missing."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        extractor = FallbackExtractor(min_body_length=50)
        result = extractor.extract(SAMPLE_HTML_HEURISTIC, "https://example.com/article")
        
        assert result is not None
        assert result.headline != ""
    
    def test_extract_headline_only(self):
        """Test quick headline-only extraction."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        extractor = FallbackExtractor()
        headline = extractor.extract_headline_only(SAMPLE_HTML_JSONLD, "https://example.com")
        
        assert headline != ""
        assert "Test Headline" in headline or "JSON-LD" in headline


class TestExtractArticleConvenience:
    """Test the convenience function."""
    
    def test_extract_article(self):
        """Test extract_article convenience function."""
        from BDNewsPaper.extractors import extract_article
        
        result = extract_article(SAMPLE_HTML_JSONLD, "https://example.com/article")
        
        assert isinstance(result, dict)
        assert 'headline' in result
        assert 'body' in result
        assert result['headline'] != ""


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_html(self):
        """Test handling of empty HTML."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        extractor = FallbackExtractor()
        result = extractor.extract("", "https://example.com")
        
        # Should not raise, return empty result
        assert result is not None
    
    def test_malformed_jsonld(self):
        """Test handling of malformed JSON-LD."""
        from BDNewsPaper.extractors import JSONLDExtractor
        
        html_with_bad_jsonld = """
        <html>
        <script type="application/ld+json">
        {invalid json here}
        </script>
        </html>
        """
        
        extractor = JSONLDExtractor()
        result = extractor.extract(html_with_bad_jsonld, "https://example.com")
        
        # Should not raise, handle gracefully
        assert result is None or result.headline == ""
    
    def test_bengali_content(self):
        """Test extraction of Bengali content."""
        from BDNewsPaper.extractors import FallbackExtractor
        
        bengali_html = """
        <html>
        <body>
            <h1>বাংলা শিরোনাম পরীক্ষা</h1>
            <article>
                <p>এটি বাংলা বিষয়বস্তু। এই অনুচ্ছেদে বাংলা টেক্সট রয়েছে যা পরীক্ষার জন্য ব্যবহৃত হচ্ছে। আরও টেক্সট যোগ করা হচ্ছে।</p>
            </article>
        </body>
        </html>
        """
        
        extractor = FallbackExtractor()
        result = extractor.extract(bengali_html, "https://example.com")
        
        assert result is not None
        assert "বাংলা" in result.headline or len(result.headline) > 0
