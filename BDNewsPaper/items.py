# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from datetime import datetime
from typing import Optional

import scrapy
from itemloaders.processors import TakeFirst, Compose
from w3lib.html import remove_tags


def clean_text(value):
    """Clean and normalize text content."""
    if value:
        # Remove extra whitespace and normalize
        return ' '.join(str(value).strip().split())
    return value


def validate_url(value):
    """Basic URL validation."""
    if value and isinstance(value, str):
        return value if value.startswith(('http://', 'https://')) else None
    return None


def validate_date(value):
    """Validate date format."""
    if not value or value == "Unknown":
        return value
    
    # Try to parse the date to ensure it's valid
    try:
        if isinstance(value, str):
            # Try different formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%B %d, %Y']:
                try:
                    datetime.strptime(value, fmt)
                    return value
                except ValueError:
                    continue
        return value
    except:
        return "Unknown"


class ArticleItem(scrapy.Item):
    """
    Scrapy Item for news articles with enhanced validation and processing.
    
    This item represents a news article with all relevant metadata and content.
    All fields are optional but recommended for complete article representation.
    """
    
    # Core content fields
    headline = scrapy.Field(
        input_processor=Compose(remove_tags, clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    sub_title = scrapy.Field(
        input_processor=Compose(remove_tags, clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    article_body = scrapy.Field(
        input_processor=Compose(remove_tags, clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    # Metadata fields
    paper_name = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    category = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    author = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    publisher = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    # Date fields
    publication_date = scrapy.Field(
        input_processor=Compose(validate_date),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    modification_date = scrapy.Field(
        input_processor=Compose(validate_date),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    # URL and media fields
    url = scrapy.Field(
        input_processor=Compose(validate_url),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    image_url = scrapy.Field(
        input_processor=Compose(validate_url),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    # Additional metadata
    keywords = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    # New enhanced fields
    scraped_at = scrapy.Field(
        serializer=str
    )
    
    source_language = scrapy.Field(
        input_processor=Compose(clean_text),
        output_processor=TakeFirst(),
        serializer=str
    )
    
    word_count = scrapy.Field(
        serializer=int
    )
    
    reading_time_minutes = scrapy.Field(
        serializer=int
    )
    
    content_hash = scrapy.Field(
        serializer=str
    )
    
    tags = scrapy.Field(
        serializer=list
    )

    def __setitem__(self, key, value):
        """Override to add automatic timestamp and content processing."""
        # Auto-add scraped timestamp
        if key == 'article_body' and value and 'scraped_at' not in self:
            self['scraped_at'] = datetime.now().isoformat()
        
        # Auto-calculate word count
        if key == 'article_body' and value and isinstance(value, str):
            words = len(value.split())
            self['word_count'] = words
            # Estimate reading time (average 200 words per minute)
            self['reading_time_minutes'] = max(1, words // 200)
        
        # Auto-set source language for Bengali content
        if key == 'article_body' and value and isinstance(value, str):
            # Simple heuristic: if contains Bengali characters, mark as Bengali
            if any('\u0980' <= char <= '\u09FF' for char in value):
                self['source_language'] = 'Bengali'
            else:
                self['source_language'] = 'English'
        
        super().__setitem__(key, value)

    def get_required_fields(self):
        """Return list of required fields for validation."""
        return ['headline', 'article_body', 'paper_name', 'url']

    def is_valid(self):
        """Check if item contains all required fields."""
        required = self.get_required_fields()
        return all(
            field in self and 
            self[field] and 
            self[field] != "Unknown" 
            for field in required
        )

    def to_dict(self):
        """Convert item to dictionary with clean values."""
        return {
            key: value for key, value in self.items()
            if value is not None and value != ""
        }


