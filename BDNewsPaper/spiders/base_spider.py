"""
Base Spider Class for BDNewsPaper Scrapers
===========================================
Common functionality shared by all newspaper spiders.
"""

import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Set

import pytz
import scrapy
from scrapy import signals
from scrapy.http import Request, Response

from BDNewsPaper.config import (
    DHAKA_TZ,
    DEFAULT_START_DATE,
    get_default_end_date,
    get_spider_config,
)
from BDNewsPaper.items import NewsArticleItem


class BaseNewsSpider(scrapy.Spider):
    """
    Base class for all newspaper spiders with common functionality.
    
    Features:
        - Standardized date range parsing
        - Category filtering support
        - Database duplicate checking
        - Statistics tracking
        - Common error handling
    
    Child classes should override:
        - paper_name: Name of the newspaper
        - start_requests(): Generate initial requests
        - parse(): Parse responses
    """
    
    # ================================================================
    # Class Attributes (override in subclasses)
    # ================================================================
    
    paper_name = "Unknown"
    
    # Filtering capabilities
    supports_api_date_filter = False
    supports_api_category_filter = False
    
    # Default custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.25,
        'AUTOTHROTTLE_MAX_DELAY': 2.0,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
    }
    
    # ================================================================
    # Initialization
    # ================================================================
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize timezone
        self.dhaka_tz = DHAKA_TZ
        
        # Parse date arguments
        self._parse_date_args(kwargs)
        
        # Parse category arguments
        self._parse_category_args(kwargs)
        
        # Parse pagination arguments
        self._parse_pagination_args(kwargs)
        
        # Parse search query arguments
        self._parse_search_args(kwargs)
        
        # Initialize database path
        self.db_path = kwargs.get('db_path', 'news_articles.db')
        
        # Initialize tracking sets
        self.processed_urls: Set[str] = set()
        self.should_stop = False
        
        # Initialize statistics
        self._init_statistics()
        
        # Thread safety for database operations
        self._db_lock = threading.Lock()
        self._local = threading.local()
        
        self.logger.info(f"Spider {self.name} initialized")
        self.logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        if self.categories:
            self.logger.info(f"Categories: {self.categories}")
        if self.search_query:
            self.logger.info(f"Search query: {self.search_query}")
    
    def _parse_date_args(self, kwargs: Dict[str, Any]) -> None:
        """Parse and validate date arguments."""
        try:
            start_date_str = kwargs.get('start_date', DEFAULT_START_DATE)
            end_date_str = kwargs.get('end_date', get_default_end_date())
            
            self.start_date = self._parse_date(start_date_str)
            self.end_date = self._parse_date(end_date_str, end_of_day=True)
            
            # Swap if dates are in wrong order
            if self.start_date > self.end_date:
                self.logger.warning("Start date is after end date, swapping...")
                self.start_date, self.end_date = self.end_date, self.start_date
                
        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            self.start_date = self.dhaka_tz.localize(
                datetime.strptime(DEFAULT_START_DATE, '%Y-%m-%d')
            )
            self.end_date = self.dhaka_tz.localize(datetime.now())
    
    def _parse_date(self, date_str: str, end_of_day: bool = False) -> datetime:
        """Parse date string and localize to Dhaka timezone."""
        if date_str.lower() == 'today':
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        if len(date_str.split()) == 1:  # Only date provided
            time_part = "23:59:59" if end_of_day else "00:00:00"
            date_str = f"{date_str} {time_part}"
        
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return self.dhaka_tz.localize(dt)
    
    def _parse_category_args(self, kwargs: Dict[str, Any]) -> None:
        """Parse category filter arguments."""
        categories_str = kwargs.get('categories', '')
        
        if categories_str:
            self.categories = [cat.strip() for cat in categories_str.split(',')]
        else:
            self.categories = []
    
    def _parse_pagination_args(self, kwargs: Dict[str, Any]) -> None:
        """Parse pagination arguments."""
        try:
            self.max_pages = int(kwargs.get('max_pages', 100))
            self.max_pages = min(max(self.max_pages, 1), 10000)  # Safety bounds
        except (ValueError, TypeError):
            self.max_pages = 100
        
        try:
            self.page_limit = int(kwargs.get('page_limit', 100))
        except (ValueError, TypeError):
            self.page_limit = 100
    
    def _parse_search_args(self, kwargs: Dict[str, Any]) -> None:
        """Parse search query arguments."""
        self.search_query = kwargs.get('search_query', '').strip()
        # Also support 'search' as alias
        if not self.search_query:
            self.search_query = kwargs.get('search', '').strip()
    
    def _init_statistics(self) -> None:
        """Initialize statistics tracking."""
        self.stats = {
            'requests_made': 0,
            'articles_found': 0,
            'articles_processed': 0,
            'duplicates_skipped': 0,
            'date_filtered': 0,
            'search_filtered': 0,  # Added for search filtering
            'errors': 0,
            'start_time': datetime.now(),
        }
    
    # ================================================================
    # Database Operations (Thread-Safe)
    # ================================================================
    
    def _get_db_connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
        return self._local.connection
    
    def is_url_in_db(self, url: str) -> bool:
        """Check if URL already exists in database."""
        # Check in-memory cache first
        if url in self.processed_urls:
            return True
        
        try:
            with self._db_lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,))
                result = cursor.fetchone() is not None
                
                if result:
                    self.stats['duplicates_skipped'] += 1
                else:
                    self.processed_urls.add(url)
                
                return result
                
        except sqlite3.Error as e:
            self.logger.warning(f"Database check failed for {url}: {e}")
            return False
    
    # ================================================================
    # Date Validation
    # ================================================================
    
    def is_date_in_range(self, date_obj: datetime) -> bool:
        """Check if date is within configured range."""
        if date_obj.tzinfo is None:
            date_obj = self.dhaka_tz.localize(date_obj)
        
        return self.start_date <= date_obj <= self.end_date
    
    def is_before_start_date(self, date_obj: datetime) -> bool:
        """Check if date is before the start date (stop condition)."""
        if date_obj.tzinfo is None:
            date_obj = self.dhaka_tz.localize(date_obj)
        
        return date_obj < self.start_date
    
    # ================================================================
    # URL Validation
    # ================================================================
    
    def is_valid_article_url(self, url: Optional[str]) -> bool:
        """
        Check if URL is a valid article link.
        
        Filters out invalid patterns like #, javascript:, empty, etc.
        Use this before creating article requests to prevent
        ValidationPipeline drops.
        
        Args:
            url: URL string to validate
            
        Returns:
            True if valid article URL, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if not url:
            return False
        # Filter out common invalid patterns
        invalid_patterns = ['#', 'javascript:', 'void(0)', 'mailto:', 'tel:', 'data:']
        for pattern in invalid_patterns:
            if url == pattern or url.startswith(pattern):
                return False
        # Must be a path or full URL
        return url.startswith('/') or url.startswith('http://') or url.startswith('https://')
    
    # ================================================================
    # Search/Keyword Filtering
    # ================================================================
    
    def matches_search_query(self, headline: str = '', body: str = '') -> bool:
        """
        Check if article matches search query (client-side filtering).
        
        Used for spiders that don't support API-level search.
        Returns True if no search query is set or if query is found.
        
        Args:
            headline: Article headline to search
            body: Article body to search
        
        Returns:
            True if article matches query or no query is set
        """
        if not self.search_query:
            return True  # No filter applied
        
        query_lower = self.search_query.lower()
        text_to_search = f"{headline} {body}".lower()
        
        # Support multiple keywords with OR logic (comma-separated)
        keywords = [k.strip() for k in query_lower.split(',') if k.strip()]
        
        for keyword in keywords:
            if keyword in text_to_search:
                return True
        
        return False
    
    def filter_by_search_query(self, headline: str = '', body: str = '') -> bool:
        """
        Check if article should be filtered out by search query.
        Returns True if article should be KEPT, False if filtered out.
        Also updates stats.
        """
        if self.matches_search_query(headline, body):
            return True
        
        self.stats['search_filtered'] += 1
        return False
    
    def parse_article_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats to datetime object."""
        if not date_str or date_str == "Unknown":
            return None
        
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = self.dhaka_tz.localize(dt)
                return dt
            except ValueError:
                continue
        
        return None
    
    # ================================================================
    # Author Extraction
    # ================================================================
    
    def extract_author(self, response: Response) -> Optional[str]:
        """
        Extract author from article page using multiple strategies.
        
        Strategies (in order):
            1. JSON-LD structured data
            2. Meta tags (author, article:author)
            3. Byline patterns (By Name, Reporter: Name)
            4. Schema.org Person markup
        
        Args:
            response: Scrapy Response object
        
        Returns:
            Author name(s) as string, or None if not found
        """
        import json
        import re
        
        author = None
        
        # Strategy 1: JSON-LD structured data
        try:
            json_ld_scripts = response.css('script[type="application/ld+json"]::text').getall()
            for script_text in json_ld_scripts:
                try:
                    data = json.loads(script_text)
                    
                    # Handle @graph format
                    if isinstance(data, dict) and '@graph' in data:
                        data = data['@graph']
                    
                    # Handle list of items
                    if isinstance(data, list):
                        for item in data:
                            author = self._extract_author_from_jsonld(item)
                            if author:
                                return author
                    else:
                        author = self._extract_author_from_jsonld(data)
                        if author:
                            return author
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            self.logger.debug(f"JSON-LD author extraction failed: {e}")
        
        # Strategy 2: Meta tags
        meta_selectors = [
            'meta[name="author"]::attr(content)',
            'meta[property="article:author"]::attr(content)',
            'meta[name="article:author"]::attr(content)',
            'meta[property="og:article:author"]::attr(content)',
            'meta[name="dcterms.creator"]::attr(content)',
            'meta[name="dc.creator"]::attr(content)',
        ]
        
        for selector in meta_selectors:
            author = response.css(selector).get()
            if author and author.strip():
                return self._clean_author_name(author)
        
        # Strategy 3: Byline patterns in HTML
        byline_selectors = [
            '.author::text',
            '.byline::text',
            '.author-name::text',
            '.writer::text',
            '.reporter::text',
            '[rel="author"]::text',
            '.article-author::text',
            '.post-author::text',
            '.entry-author::text',
            'span[itemprop="author"]::text',
            'a[rel="author"]::text',
        ]
        
        for selector in byline_selectors:
            author = response.css(selector).get()
            if author and author.strip():
                return self._clean_author_name(author)
        
        # Strategy 4: Regex patterns for bylines
        byline_patterns = [
            r'[Bb]y\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'[Rr]eporter:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'[Ww]ritten by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'[Aa]uthor:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        ]
        
        # Search in first 2000 chars of response body
        body_text = response.text[:2000] if response.text else ''
        
        for pattern in byline_patterns:
            match = re.search(pattern, body_text)
            if match:
                author = match.group(1)
                return self._clean_author_name(author)
        
        return None
    
    def _extract_author_from_jsonld(self, data: dict) -> Optional[str]:
        """Extract author from JSON-LD data structure."""
        if not isinstance(data, dict):
            return None
        
        # Check if this is an article type
        item_type = data.get('@type', '')
        if isinstance(item_type, list):
            item_type = item_type[0] if item_type else ''
        
        if 'Article' not in item_type and 'NewsArticle' not in item_type:
            return None
        
        author_data = data.get('author')
        if not author_data:
            return None
        
        # Handle various author formats
        if isinstance(author_data, str):
            return self._clean_author_name(author_data)
        
        if isinstance(author_data, dict):
            name = author_data.get('name') or author_data.get('@name')
            if name:
                return self._clean_author_name(name)
        
        if isinstance(author_data, list):
            names = []
            for author in author_data:
                if isinstance(author, str):
                    names.append(author)
                elif isinstance(author, dict):
                    name = author.get('name') or author.get('@name')
                    if name:
                        names.append(name)
            if names:
                return ', '.join(self._clean_author_name(n) for n in names[:3])
        
        return None
    
    def _clean_author_name(self, name: str) -> str:
        """Clean and normalize author name."""
        import re
        
        if not name:
            return ''
        
        # Remove common prefixes
        name = re.sub(r'^[Bb]y\s+', '', name)
        name = re.sub(r'^[Rr]eporter:\s*', '', name)
        name = re.sub(r'^[Ww]ritten by\s+', '', name)
        
        # Remove HTML tags
        name = re.sub(r'<[^>]+>', '', name)
        
        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove common suffixes
        name = re.sub(r'\s*\|.*$', '', name)
        name = re.sub(r'\s*,\s*Staff Reporter$', '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    # ================================================================
    # Item Creation
    # ================================================================
    
    def create_article_item(self, **kwargs) -> NewsArticleItem:
        """Create a standardized article item with common fields."""
        item = NewsArticleItem()
        
        # Set paper name
        item['paper_name'] = kwargs.get('paper_name', self.paper_name)
        
        # Set other fields if provided
        field_mappings = [
            'url', 'headline', 'article_body', 'sub_title', 'category',
            'author', 'publication_date', 'modification_date', 'image_url',
            'keywords', 'publisher'
        ]
        
        for field in field_mappings:
            if field in kwargs and kwargs[field]:
                item[field] = kwargs[field]
        
        return item
    
    # ================================================================
    # Error Handling
    # ================================================================
    
    def handle_request_failure(self, failure):
        """Enhanced error handling for failed requests."""
        self.stats['errors'] += 1
        url = failure.request.url
        error_msg = str(failure.value)
        
        if "DNS lookup failed" in error_msg:
            self.logger.warning(f"DNS lookup failed for {url}")
        elif "Connection refused" in error_msg:
            self.logger.warning(f"Connection refused for {url}")
        elif "timeout" in error_msg.lower():
            self.logger.warning(f"Request timeout for {url}")
        else:
            self.logger.error(f"Request failed for {url}: {error_msg}")
    
    # ================================================================
    # Spider Lifecycle
    # ================================================================
    
    def closed(self, reason: str) -> None:
        """Log final statistics when spider closes."""
        runtime = datetime.now() - self.stats['start_time']
        
        self.logger.info("=" * 60)
        self.logger.info(f"{self.paper_name.upper()} SPIDER STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total Runtime: {runtime}")
        self.logger.info(f"Requests made: {self.stats['requests_made']}")
        self.logger.info(f"Articles found: {self.stats['articles_found']}")
        self.logger.info(f"Articles processed: {self.stats['articles_processed']}")
        self.logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        self.logger.info(f"Date filtered: {self.stats['date_filtered']}")
        if self.search_query:
            self.logger.info(f"Search filtered: {self.stats['search_filtered']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        
        if runtime.total_seconds() > 0:
            rate = self.stats['articles_processed'] / (runtime.total_seconds() / 60)
            self.logger.info(f"Articles per minute: {rate:.1f}")
        
        self.logger.info("=" * 60)
        
        # Close database connection
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing database: {e}")
