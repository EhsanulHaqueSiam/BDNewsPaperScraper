# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import hashlib
import re
from datetime import datetime
from typing import Any, List, Optional

import scrapy
from itemloaders.processors import TakeFirst, Compose, MapCompose, Identity
from w3lib.html import remove_tags


# ============================================================================
# Field Processors
# ============================================================================

def clean_text(value: Any) -> str:
    """Clean and normalize text content."""
    if not value:
        return ""
    
    if isinstance(value, list):
        value = " ".join(str(v) for v in value if v)
    
    text = str(value).strip()
    
    # Remove HTML tags
    text = remove_tags(text)
    
    # Replace common HTML entities
    html_entities = {
        '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"',
        '&apos;': "'", '&nbsp;': ' ', '&#39;': "'", '&#x27;': "'"
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def validate_url(value: Any) -> Optional[str]:
    """Validate and clean URL."""
    if not value or not isinstance(value, str):
        return None
    
    url = value.strip()
    if url.startswith(('http://', 'https://')):
        return url
    return None


def normalize_date(value: Any) -> str:
    """Normalize date to ISO format string."""
    if not value:
        return "Unknown"
    
    if value == "Unknown":
        return value
    
    # If already a datetime object
    if isinstance(value, datetime):
        return value.isoformat()
    
    # Try to parse common formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%B %d, %Y',
        '%b %d, %Y',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(str(value).strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    return str(value).strip()


def clean_author(value: Any) -> str:
    """Clean and normalize author field."""
    if not value:
        return "Unknown"
    
    if isinstance(value, list):
        # Filter and join author names
        authors = [clean_text(a) for a in value if a]
        authors = [a for a in authors if a and a != "Unknown"]
        return ", ".join(authors) if authors else "Unknown"
    
    cleaned = clean_text(value)
    return cleaned if cleaned else "Unknown"


def extract_keywords(value: Any) -> Optional[str]:
    """Extract and clean keywords."""
    if not value:
        return None
    
    if isinstance(value, list):
        keywords = []
        for kw in value:
            if isinstance(kw, dict):
                name = kw.get('name') or kw.get('value')
                if name:
                    keywords.append(clean_text(name))
            elif kw:
                keywords.append(clean_text(kw))
        return ", ".join(keywords) if keywords else None
    
    return clean_text(value) if value else None


# ============================================================================
# Unified Item Model
# ============================================================================

class NewsArticleItem(scrapy.Item):
    """
    Unified Scrapy Item for news articles.
    
    This standardized item represents a news article with consistent field names
    across all newspaper spiders. All fields use processors for automatic 
    cleaning and validation.
    
    Required Fields:
        - url: Unique article URL
        - headline: Article title
        - article_body: Main content text
        - paper_name: Source newspaper name
    
    Optional Fields:
        - sub_title: Article subtitle/summary
        - category: Article category/section
        - author: Author name(s)
        - publication_date: When published
        - modification_date: When last modified
        - image_url: Featured image URL
        - keywords: Article keywords/tags
        - publisher: Publisher name
    
    Auto-generated Fields:
        - scraped_at: Timestamp when scraped
        - source_language: 'Bengali' or 'English'
        - word_count: Number of words in body
        - reading_time_minutes: Estimated reading time
        - content_hash: MD5 hash for deduplication
    """
    
    # ===== Required Core Fields =====
    url = scrapy.Field(
        input_processor=Compose(validate_url),
        output_processor=TakeFirst(),
    )
    
    headline = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
    )
    
    article_body = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
    )
    
    paper_name = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
    )
    
    # ===== Optional Metadata Fields =====
    sub_title = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
    )
    
    category = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
    )
    
    author = scrapy.Field(
        input_processor=Compose(clean_author),
        output_processor=TakeFirst(),
    )
    
    publisher = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
    )
    
    # ===== Date Fields =====
    publication_date = scrapy.Field(
        input_processor=Compose(normalize_date),
        output_processor=TakeFirst(),
    )
    
    modification_date = scrapy.Field(
        input_processor=Compose(normalize_date),
        output_processor=TakeFirst(),
    )
    
    # ===== Media Fields =====
    image_url = scrapy.Field(
        input_processor=Compose(validate_url),
        output_processor=TakeFirst(),
    )
    
    # ===== Taxonomy Fields =====
    keywords = scrapy.Field(
        input_processor=Compose(extract_keywords),
        output_processor=TakeFirst(),
    )
    
    tags = scrapy.Field(
        output_processor=Identity(),  # Keep as list
    )
    
    # ===== Auto-generated Metadata =====
    scraped_at = scrapy.Field()
    source_language = scrapy.Field()
    word_count = scrapy.Field()
    reading_time_minutes = scrapy.Field()
    content_hash = scrapy.Field()
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Override to add automatic metadata generation."""
        # Set the value first
        super().__setitem__(key, value)
        
        # Auto-generate metadata when article_body is set
        if key == 'article_body' and value:
            self._generate_metadata(value)
    
    def _generate_metadata(self, body: str) -> None:
        """Generate automatic metadata from article body."""
        if not body or not isinstance(body, str):
            return
        
        # Auto-add scraped timestamp
        if 'scraped_at' not in self:
            super().__setitem__('scraped_at', datetime.now().isoformat())
        
        # Auto-calculate word count
        words = len(body.split())
        super().__setitem__('word_count', words)
        
        # Estimate reading time (average 200 words per minute)
        super().__setitem__('reading_time_minutes', max(1, words // 200))
        
        # Detect language (Bengali Unicode range: U+0980-U+09FF)
        has_bengali = any('\u0980' <= char <= '\u09FF' for char in body)
        super().__setitem__('source_language', 'Bengali' if has_bengali else 'English')
        
        # Generate content hash for deduplication
        content = f"{self.get('headline', '')}{body}".encode('utf-8')
        super().__setitem__('content_hash', hashlib.md5(content).hexdigest())
    
    def get_required_fields(self) -> List[str]:
        """Return list of required fields for validation."""
        return ['headline', 'article_body', 'paper_name', 'url']
    
    def is_valid(self) -> bool:
        """Check if item contains all required fields with valid content."""
        for field in self.get_required_fields():
            if field not in self:
                return False
            value = self[field]
            if not value or value == "Unknown":
                return False
        return True
    
    def to_dict(self) -> dict:
        """Convert item to dictionary with clean values."""
        return {
            key: value for key, value in self.items()
            if value is not None and value != ""
        }


# ============================================================================
# Backward Compatibility Alias
# ============================================================================

# Keep ArticleItem as an alias for backward compatibility with existing spiders
ArticleItem = NewsArticleItem
