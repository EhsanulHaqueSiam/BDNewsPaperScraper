"""
Smart Fallback Extraction Module
================================
Provides a multi-strategy content extraction pipeline with graceful degradation.

Extraction Chain:
    1. JSON-LD / Microdata (structured data, most reliable)
    2. Trafilatura (ML-based extraction, good for most sites)
    3. Generic Heuristics (article tags, largest text block)
    4. Raw text extraction (last resort)

Usage:
    from BDNewsPaper.extractors import FallbackExtractor
    
    extractor = FallbackExtractor()
    result = extractor.extract(html_content, url)
    # result = {"headline": "...", "body": "...", "author": "...", "date": "..."}
"""

import json
import re
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import logging

try:
    import trafilatura
    from trafilatura.settings import use_config
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from lxml import html as lxml_html
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of content extraction."""
    headline: str = ""
    body: str = ""
    author: str = ""
    publication_date: str = ""
    image_url: str = ""
    source: str = ""  # Which extractor was used
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self, min_body_length: int = 50) -> bool:
        """Check if extraction result is valid."""
        return bool(self.headline) and len(self.body) >= min_body_length
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "headline": self.headline,
            "body": self.body,
            "author": self.author,
            "publication_date": self.publication_date,
            "image_url": self.image_url,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class JSONLDExtractor:
    """Extract content from JSON-LD structured data."""
    
    ARTICLE_TYPES = [
        "Article", "NewsArticle", "BlogPosting", "WebPage",
        "ReportageNewsArticle", "AnalysisNewsArticle"
    ]
    
    def extract(self, html: str, url: str = "") -> Optional[ExtractionResult]:
        """Extract article data from JSON-LD."""
        try:
            # Find all JSON-LD scripts
            pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    data = json.loads(match.strip())
                    
                    # Handle array format
                    if isinstance(data, list):
                        for item in data:
                            result = self._parse_jsonld(item)
                            if result and result.is_valid():
                                return result
                    else:
                        result = self._parse_jsonld(data)
                        if result and result.is_valid():
                            return result
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")
            
        return None
    
    def _parse_jsonld(self, data: Dict) -> Optional[ExtractionResult]:
        """Parse a single JSON-LD object."""
        if not isinstance(data, dict):
            return None
            
        # Check @graph format
        if "@graph" in data:
            for item in data["@graph"]:
                result = self._parse_jsonld(item)
                if result:
                    return result
            return None
        
        # Check if it's an article type
        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else ""
            
        if schema_type not in self.ARTICLE_TYPES:
            return None
        
        # Extract fields
        headline = data.get("headline", "") or data.get("name", "")
        body = data.get("articleBody", "") or data.get("text", "")
        
        # Author can be string or object
        author_data = data.get("author", {})
        if isinstance(author_data, list):
            author_data = author_data[0] if author_data else {}
        if isinstance(author_data, dict):
            author = author_data.get("name", "")
        else:
            author = str(author_data)
        
        # Date
        pub_date = data.get("datePublished", "") or data.get("dateCreated", "")
        
        # Image
        image_data = data.get("image", {})
        if isinstance(image_data, list):
            image_data = image_data[0] if image_data else {}
        if isinstance(image_data, dict):
            image_url = image_data.get("url", "") or image_data.get("contentUrl", "")
        else:
            image_url = str(image_data) if image_data else ""
        
        return ExtractionResult(
            headline=headline,
            body=body,
            author=author,
            publication_date=pub_date,
            image_url=image_url,
            source="json-ld",
            confidence=0.95,  # High confidence for structured data
        )


class TrafilaturaExtractor:
    """Extract content using trafilatura ML-based extraction."""
    
    def __init__(self):
        self.config = None
        if TRAFILATURA_AVAILABLE:
            self.config = use_config()
            self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    
    def extract(self, html: str, url: str = "") -> Optional[ExtractionResult]:
        """Extract article using trafilatura."""
        if not TRAFILATURA_AVAILABLE:
            logger.debug("Trafilatura not available")
            return None
            
        try:
            # Extract with metadata
            result = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=False,
                include_images=True,
                output_format="txt",
                config=self.config,
            )
            
            if not result:
                return None
            
            # Get metadata separately
            metadata = trafilatura.extract_metadata(html, url=url)
            
            headline = ""
            author = ""
            pub_date = ""
            image_url = ""
            
            if metadata:
                headline = metadata.title or ""
                author = metadata.author or ""
                pub_date = metadata.date or ""
                image_url = metadata.image or ""
            
            return ExtractionResult(
                headline=headline,
                body=result,
                author=author,
                publication_date=pub_date,
                image_url=image_url,
                source="trafilatura",
                confidence=0.80,
            )
            
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed: {e}")
            return None


class HeuristicExtractor:
    """Extract content using generic HTML heuristics."""
    
    # Priority selectors for headlines
    HEADLINE_SELECTORS = [
        "h1.article-title", "h1.post-title", "h1.entry-title",
        "h1[itemprop='headline']", ".headline h1", "article h1", "h1"
    ]
    
    # Priority selectors for body
    BODY_SELECTORS = [
        "article .content", ".article-body", ".post-content",
        ".entry-content", "[itemprop='articleBody']",
        "article p", ".content p"
    ]
    
    def extract(self, html: str, url: str = "") -> Optional[ExtractionResult]:
        """Extract using CSS selectors and heuristics."""
        if not LXML_AVAILABLE:
            return self._regex_fallback(html)
            
        try:
            tree = lxml_html.fromstring(html)
            
            # Extract headline
            headline = ""
            for selector in self.HEADLINE_SELECTORS:
                try:
                    elements = tree.cssselect(selector)
                    if elements:
                        headline = elements[0].text_content().strip()
                        if headline:
                            break
                except:
                    continue
            
            # Extract body paragraphs
            body_parts = []
            for selector in self.BODY_SELECTORS:
                try:
                    elements = tree.cssselect(selector)
                    for el in elements:
                        text = el.text_content().strip()
                        if len(text) > 20:  # Skip tiny fragments
                            body_parts.append(text)
                    if body_parts:
                        break
                except:
                    continue
            
            body = " ".join(body_parts)
            
            # Extract author
            author = ""
            author_selectors = [".author", "[rel='author']", ".byline", ".post-author"]
            for selector in author_selectors:
                try:
                    elements = tree.cssselect(selector)
                    if elements:
                        author = elements[0].text_content().strip()
                        break
                except:
                    continue
            
            if headline or body:
                return ExtractionResult(
                    headline=headline,
                    body=body,
                    author=author,
                    source="heuristic",
                    confidence=0.60,
                )
                
        except Exception as e:
            logger.debug(f"Heuristic extraction failed: {e}")
            
        return self._regex_fallback(html)
    
    def _regex_fallback(self, html: str) -> Optional[ExtractionResult]:
        """Last resort regex-based extraction."""
        try:
            # Remove scripts and styles
            clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
            
            # Extract title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', clean, re.IGNORECASE | re.DOTALL)
            headline = title_match.group(1).strip() if title_match else ""
            
            # Strip all HTML tags
            text = re.sub(r'<[^>]+>', ' ', clean)
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Get the largest text block (simplified)
            body = text[:5000] if len(text) > 5000 else text
            
            if headline or body:
                return ExtractionResult(
                    headline=headline,
                    body=body,
                    source="regex",
                    confidence=0.30,
                )
                
        except Exception as e:
            logger.debug(f"Regex fallback failed: {e}")
            
        return None


class FallbackExtractor:
    """
    Main extractor with fallback chain.
    
    Tries multiple extraction methods in order of reliability:
    1. JSON-LD (structured data)
    2. Trafilatura (ML-based)
    3. Heuristics (CSS selectors)
    4. Regex fallback
    """
    
    def __init__(self, min_body_length: int = 50):
        self.min_body_length = min_body_length
        self.extractors = [
            ("json-ld", JSONLDExtractor()),
            ("trafilatura", TrafilaturaExtractor()),
            ("heuristic", HeuristicExtractor()),
        ]
        
    def extract(self, html: str, url: str = "") -> ExtractionResult:
        """
        Extract article content with fallback chain.
        
        Args:
            html: Raw HTML content
            url: Original URL (helps some extractors)
            
        Returns:
            ExtractionResult with best available content
        """
        for name, extractor in self.extractors:
            try:
                result = extractor.extract(html, url)
                if result and result.is_valid(self.min_body_length):
                    logger.debug(f"Extraction succeeded with: {name}")
                    return result
            except Exception as e:
                logger.debug(f"Extractor {name} failed: {e}")
                continue
        
        # Return empty result if all fail
        logger.warning(f"All extractors failed for {url}")
        return ExtractionResult(source="none", confidence=0.0)
    
    def extract_headline_only(self, html: str, url: str = "") -> str:
        """Quick extraction of just the headline."""
        for name, extractor in self.extractors:
            try:
                result = extractor.extract(html, url)
                if result and result.headline:
                    return result.headline
            except:
                continue
        return ""


# Convenience function
def extract_article(html: str, url: str = "", min_body_length: int = 50) -> Dict[str, Any]:
    """
    Convenience function for quick article extraction.
    
    Args:
        html: Raw HTML content
        url: Original URL
        min_body_length: Minimum body length to consider valid
        
    Returns:
        Dictionary with extracted fields
    """
    extractor = FallbackExtractor(min_body_length=min_body_length)
    result = extractor.extract(html, url)
    return result.to_dict()
