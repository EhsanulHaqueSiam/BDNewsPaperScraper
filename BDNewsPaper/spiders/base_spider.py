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
from BDNewsPaper.link_discovery import ArticleLinkDiscovery, discover_article_links


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
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Create spider instance with settings from crawler."""
        # Extract DATABASE_PATH from settings and pass to spider
        db_path = crawler.settings.get('DATABASE_PATH', 'news_articles.db')
        kwargs['db_path'] = db_path
        spider = super().from_crawler(crawler, *args, **kwargs)
        return spider
    
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
        
        # Initialize database path (from_crawler passes db_path from settings)
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
    # Universal Fallback Extraction Methods
    # ================================================================
    
    def extract_from_jsonld(self, response: Response) -> Optional[Dict[str, Any]]:
        """
        Extract article data from JSON-LD structured data.
        
        Most news sites embed article metadata in JSON-LD format.
        This is the most reliable extraction method when available.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Dictionary with extracted fields, or None if not found
        """
        import json
        
        scripts = response.css('script[type="application/ld+json"]::text').getall()
        
        for script in scripts:
            try:
                data = json.loads(script)
                
                # Handle @graph format
                if isinstance(data, dict) and '@graph' in data:
                    items = data['@graph']
                elif isinstance(data, list):
                    items = data
                else:
                    items = [data]
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    item_type = item.get('@type', '')
                    if isinstance(item_type, list):
                        item_type = item_type[0] if item_type else ''
                    
                    # Check for article types
                    article_types = ['NewsArticle', 'Article', 'BlogPosting', 'WebPage', 
                                    'ReportageNewsArticle', 'AnalysisNewsArticle']
                    if not any(t in str(item_type) for t in article_types):
                        continue
                    
                    # Extract fields
                    result = {
                        'headline': item.get('headline') or item.get('name'),
                        'article_body': item.get('articleBody') or item.get('description'),
                        'publication_date': item.get('datePublished'),
                        'modification_date': item.get('dateModified'),
                    }
                    
                    # Extract author
                    author = item.get('author')
                    if isinstance(author, dict):
                        result['author'] = author.get('name')
                    elif isinstance(author, list) and author:
                        names = [a.get('name') if isinstance(a, dict) else a for a in author]
                        result['author'] = ', '.join(filter(None, names))
                    elif isinstance(author, str):
                        result['author'] = author
                    
                    # Extract image
                    image = item.get('image')
                    if isinstance(image, dict):
                        result['image_url'] = image.get('url')
                    elif isinstance(image, list) and image:
                        first_img = image[0]
                        result['image_url'] = first_img.get('url') if isinstance(first_img, dict) else first_img
                    elif isinstance(image, str):
                        result['image_url'] = image
                    
                    # Only return if we have at least headline
                    if result.get('headline'):
                        self.logger.debug(f"Extracted from JSON-LD: {result.get('headline')[:50]}")
                        return result
                        
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                self.logger.debug(f"JSON-LD parse error: {e}")
                continue
        
        return None
    
    def try_generic_selectors(self, response: Response) -> Dict[str, Any]:
        """
        Try common CSS selectors used by news sites.
        
        Use this as a fallback when spider-specific selectors fail.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Dictionary with extracted fields (may be empty)
        """
        result = {}
        
        # Headline selectors (in order of specificity)
        headline_selectors = [
            'h1.entry-title::text',
            'h1.post-title::text',
            'h1.article-title::text',
            'h1[itemprop="headline"]::text',
            '.headline h1::text',
            'article h1::text',
            '.article-header h1::text',
            '.post-header h1::text',
            'h1.title::text',
            'h1::text',
        ]
        
        for selector in headline_selectors:
            headline = response.css(selector).get()
            if headline and len(headline.strip()) > 10:
                result['headline'] = headline.strip()
                break
        
        # Body selectors (ordered by specificity/reliability)
        body_selectors = [
            # Schema.org/semantic
            '[itemprop="articleBody"] p::text',
            '[itemprop="articleBody"]::text',
            
            # Common CMS patterns
            'article .entry-content p::text',
            '.post-content p::text',
            '.article-body p::text',
            '.article-content p::text',
            '.story-body p::text',
            '.story-content p::text',
            '.content-inner p::text',
            '.main-content p::text',
            
            # Bangla news site patterns
            '.news-content p::text',
            '.content p::text',
            '.news-details p::text',
            '.details-content p::text',
            
            # Generic fallbacks
            'article p::text',
            '.single-content p::text',
            'main p::text',
        ]
        
        for selector in body_selectors:
            paragraphs = response.css(selector).getall()
            if paragraphs:
                body = ' '.join(p.strip() for p in paragraphs if p.strip())
                if len(body) > 100:
                    result['article_body'] = body
                    break
        
        # Date selectors
        date_selectors = [
            'time[datetime]::attr(datetime)',
            '[itemprop="datePublished"]::attr(content)',
            'meta[property="article:published_time"]::attr(content)',
            '.post-date::text',
            '.entry-date::text',
            '.published::text',
        ]
        
        for selector in date_selectors:
            date = response.css(selector).get()
            if date and date.strip():
                result['publication_date'] = date.strip()
                break
        
        # Image selectors
        image_selectors = [
            'meta[property="og:image"]::attr(content)',
            'article img::attr(src)',
            '.featured-image img::attr(src)',
            '.post-thumbnail img::attr(src)',
        ]
        
        for selector in image_selectors:
            image = response.css(selector).get()
            if image and image.strip():
                result['image_url'] = response.urljoin(image.strip())
                break
        
        if result:
            self.logger.debug(f"Generic selectors found: {list(result.keys())}")
        
        return result
    
    def extract_article_fallback(self, response: Response) -> Optional[Dict[str, Any]]:
        """
        Unified fallback extraction using all available methods.
        
        Extraction chain:
        1. JSON-LD structured data (most reliable)
        2. Generic CSS selectors (common patterns)
        3. Meta tags (og:, twitter:)
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Dictionary with extracted fields, or None if all fail
        """
        # Try JSON-LD first (most reliable)
        result = self.extract_from_jsonld(response)
        if result and result.get('headline') and result.get('article_body'):
            result['extraction_source'] = 'jsonld'
            return result
        
        # Try generic selectors
        generic_result = self.try_generic_selectors(response)
        
        # Merge results if JSON-LD was partial
        if result:
            for key, value in generic_result.items():
                if not result.get(key) and value:
                    result[key] = value
            if result.get('headline'):
                result['extraction_source'] = 'jsonld+generic'
                return result
        
        # Use generic result if JSON-LD failed
        if generic_result.get('headline'):
            generic_result['extraction_source'] = 'generic'
            return generic_result
        
        return None
    
    def discover_links(self, response: Response, limit: int = 50) -> List[str]:
        """
        Discover article links using pattern-based URL detection.
        
        This is a robust fallback when CSS selectors fail. It analyzes
        all links on the page and scores them based on URL patterns.
        
        Args:
            response: Scrapy Response object
            limit: Maximum links to return
            
        Returns:
            List of article URLs
        """
        return discover_article_links(response, limit)
    
    def parse_article_auto(self, response: Response) -> Optional[NewsArticleItem]:
        """
        Universal article parser with automatic extraction.
        
        Tries multiple extraction strategies:
        1. JSON-LD structured data
        2. Generic CSS selectors
        3. Meta tags (og:, twitter:)
        
        Use this when spider-specific selectors are broken.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            NewsArticleItem or None if extraction fails
        """
        # Try fallback extraction
        extracted = self.extract_article_fallback(response)
        
        if not extracted:
            self.logger.debug(f"Auto extraction failed for: {response.url}")
            return None
        
        # Extract author as fallback
        author = extracted.get('author') or self.extract_author(response)
        
        # Create item
        item = self.create_article_item(
            url=response.url,
            headline=extracted.get('headline'),
            article_body=extracted.get('article_body'),
            author=author,
            publication_date=extracted.get('publication_date'),
            modification_date=extracted.get('modification_date'),
            image_url=extracted.get('image_url'),
        )
        
        # Store raw HTML for fallback pipeline
        item['_raw_html'] = response.text
        
        self.stats['articles_processed'] += 1
        self.logger.info(f"Auto-extracted: {extracted.get('headline', '')[:50]}")
        
        return item
    
    def parse_listing_auto(self, response: Response) -> Generator:
        """
        Universal listing page parser.
        
        Discovers article links using pattern-based detection,
        then yields requests for each article.
        
        Usage in spider:
            def parse(self, response):
                yield from self.parse_listing_auto(response)
        
        Args:
            response: Scrapy Response object (listing page)
            
        Yields:
            Scrapy Requests for discovered article pages
        """
        article_urls = self.discover_links(response)
        
        self.logger.info(f"Discovered {len(article_urls)} article links on {response.url}")
        
        for url in article_urls:
            # Skip if already in database
            if self.is_url_in_db(url):
                continue
            
            self.stats['articles_found'] += 1
            
            yield Request(
                url=url,
                callback=self.parse_article_auto,
                errback=self.handle_request_failure,
                meta={'auto_parse': True},
            )
    
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
