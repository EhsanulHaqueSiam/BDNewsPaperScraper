# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import hashlib
import logging
import re
import sqlite3
import threading
from datetime import datetime
from typing import Optional

from itemadapter.adapter import ItemAdapter
from scrapy.exceptions import DropItem
from w3lib.html import remove_tags

from BDNewsPaper.config import MIN_ARTICLE_LENGTH, MIN_HEADLINE_LENGTH, DHAKA_TZ


logger = logging.getLogger(__name__)


# ============================================================================
# Validation Pipeline
# ============================================================================

class ValidationPipeline:
    """
    Enhanced validation pipeline for data quality.
    
    Validates required fields and content length.
    Configurable via settings:
        - MIN_ARTICLE_LENGTH: Minimum article body length (default: 50)
        - MIN_HEADLINE_LENGTH: Minimum headline length (default: 5)
        - VALIDATION_STRICT_MODE: If False, log warnings instead of dropping (default: True)
    """
    
    def __init__(self, min_article_length: int = 50, min_headline_length: int = 5, strict_mode: bool = True):
        self.min_article_length = min_article_length
        self.min_headline_length = min_headline_length
        self.strict_mode = strict_mode
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            min_article_length=crawler.settings.getint('MIN_ARTICLE_LENGTH', MIN_ARTICLE_LENGTH),
            min_headline_length=crawler.settings.getint('MIN_HEADLINE_LENGTH', MIN_HEADLINE_LENGTH),
            strict_mode=crawler.settings.getbool('VALIDATION_STRICT_MODE', True),
        )
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Required fields validation (always strict)
        required_fields = ['headline', 'url', 'paper_name']
        for field in required_fields:
            if not adapter.get(field):
                raise DropItem(f"Missing required field: {field} in {adapter.get('url', 'unknown URL')}")
        
        # URL validation (always strict - invalid URLs are fatal)
        url = adapter.get('url')
        if not self._is_valid_url(url):
            raise DropItem(f"Invalid URL format: {url}")
        
        # Headline length validation
        headline = adapter.get('headline', '')
        if len(headline.strip()) < self.min_headline_length:
            if self.strict_mode:
                raise DropItem(f"Headline too short ({len(headline)} chars): {url}")
            else:
                spider.logger.warning(f"[RELAXED] Headline too short ({len(headline)} chars): {url}")
        
        # Content length validation
        article_body = adapter.get('article_body', '')
        if not article_body or len(article_body.strip()) < self.min_article_length:
            if self.strict_mode:
                raise DropItem(f"Article too short ({len(article_body) if article_body else 0} chars): {url}")
            else:
                spider.logger.warning(f"[RELAXED] Article too short ({len(article_body) if article_body else 0} chars): {url}")
        
        return item
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        if not url or not isinstance(url, str):
            return False
        return url.startswith(('http://', 'https://'))


# ============================================================================
# Content Cleaning Pipeline
# ============================================================================

class CleanArticlePipeline:
    """
    Enhanced article cleaning pipeline for text processing.
    
    Cleans HTML, normalizes whitespace, and removes unwanted patterns.
    """
    
    # Patterns to remove from article content
    UNWANTED_PATTERNS = [
        r'^\s*Advertisement\s*',
        r'\s*Read more:.*$',
        r'\s*Also read:.*$',
        r'\s*Subscribe.*$',
        r'\s*Click here.*$',
        r'\s*SHARE\s*$',
        r'\s*Share\s*$',
    ]
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Clean the article body
        if adapter.get("article_body"):
            item["article_body"] = self._clean_article_body(adapter.get("article_body"))
        
        # Clean headline
        if adapter.get("headline"):
            item["headline"] = self._clean_text(adapter.get("headline"))
        
        # Clean subtitle
        if adapter.get("sub_title"):
            item["sub_title"] = self._clean_text(adapter.get("sub_title"))
        
        # Normalize author field
        author = adapter.get("author")
        if isinstance(author, list):
            item["author"] = ", ".join(str(a) for a in author if a)
        elif author:
            item["author"] = self._clean_text(author)
        
        # Clean keywords
        if adapter.get("keywords"):
            item["keywords"] = self._clean_text(adapter.get("keywords"))
        
        # Validate cleaned content
        article_body = adapter.get("article_body", "")
        if not article_body or len(article_body.strip()) < MIN_ARTICLE_LENGTH:
            raise DropItem(f"Insufficient article content after cleaning: {adapter.get('url', 'unknown URL')}")
        
        return item
    
    def _clean_article_body(self, article_body: str) -> str:
        """Enhanced article body cleaning."""
        if not article_body:
            return ""
        
        # Convert to string if needed
        if isinstance(article_body, list):
            article_body = " ".join(str(p) for p in article_body if p)
        
        cleaned_body = str(article_body)
        
        # Remove HTML tags
        cleaned_body = remove_tags(cleaned_body)
        
        # Replace HTML entities
        html_entities = {
            '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"',
            '&apos;': "'", '&nbsp;': ' ', '&#39;': "'", '&#x27;': "'"
        }
        for entity, char in html_entities.items():
            cleaned_body = cleaned_body.replace(entity, char)
        
        # Remove unwanted patterns
        for pattern in self.UNWANTED_PATTERNS:
            cleaned_body = re.sub(pattern, '', cleaned_body, flags=re.IGNORECASE | re.MULTILINE)
        
        # Normalize whitespace
        cleaned_body = re.sub(r'\s+', ' ', cleaned_body).strip()
        
        return cleaned_body
    
    def _clean_text(self, text: str) -> str:
        """Generic text cleaner."""
        if not text:
            return ""
        
        if isinstance(text, list):
            text = " ".join(str(t) for t in text if t)
        
        text = str(text)
        text = remove_tags(text)
        text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


# ============================================================================
# Language Detection Pipeline
# ============================================================================

class LanguageDetectionPipeline:
    """
    Detect and validate article language.
    
    Uses langdetect library to identify language and optionally
    reject articles that don't match the expected language.
    
    Configure via settings:
        - LANGUAGE_DETECTION_ENABLED: Enable/disable (default: True)
        - LANGUAGE_DETECTION_STRICT: Drop non-matching articles (default: False)
        - EXPECTED_LANGUAGES: List of allowed languages (default: ['en'])
    """
    
    def __init__(self, enabled: bool = True, strict: bool = False,
                 expected_languages: list = None):
        self.enabled = enabled
        self.strict = strict
        self.expected_languages = expected_languages or ['en']
        self._langdetect_available = False
        
        try:
            from langdetect import detect, LangDetectException
            self._detect = detect
            self._LangDetectException = LangDetectException
            self._langdetect_available = True
        except ImportError:
            logger.warning("langdetect not installed. Language detection disabled.")
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            enabled=crawler.settings.getbool('LANGUAGE_DETECTION_ENABLED', True),
            strict=crawler.settings.getbool('LANGUAGE_DETECTION_STRICT', False),
            expected_languages=crawler.settings.getlist('EXPECTED_LANGUAGES', ['en']),
        )
    
    def process_item(self, item, spider):
        if not self.enabled or not self._langdetect_available:
            return item
        
        adapter = ItemAdapter(item)
        
        # Get text for detection (headline + first 500 chars of body)
        headline = adapter.get('headline', '')
        body = adapter.get('article_body', '')
        text_sample = f"{headline} {body[:500]}"
        
        if len(text_sample.strip()) < 20:
            # Not enough text to detect language
            return item
        
        try:
            detected_lang = self._detect(text_sample)
            item['detected_language'] = detected_lang
            
            # Log detection
            spider.logger.debug(f"Detected language: {detected_lang} for {adapter.get('url', 'unknown')}")
            
            # Check if language matches expected
            if self.strict and detected_lang not in self.expected_languages:
                raise DropItem(
                    f"Language mismatch: detected '{detected_lang}', "
                    f"expected {self.expected_languages} for {adapter.get('url')}"
                )
            
        except self._LangDetectException as e:
            spider.logger.debug(f"Language detection failed: {e}")
            item['detected_language'] = 'unknown'
        
        return item


# ============================================================================
# Content Quality Pipeline
# ============================================================================

class ContentQualityPipeline:
    """
    Enhanced content quality validation.
    
    Detects:
        - Garbage content (high special character ratio)
        - Scraping artifacts (common error patterns)
        - Suspiciously short or long content
    """
    
    # Common garbage patterns
    GARBAGE_PATTERNS = [
        r'javascript:',
        r'<script',
        r'window\.',
        r'document\.',
        r'function\(\)',
        r'\{.*:\s*\{',  # JSON-like structures
    ]
    
    def __init__(self, max_special_char_ratio: float = 0.3,
                 min_words: int = 20, max_words: int = 50000):
        self.max_special_char_ratio = max_special_char_ratio
        self.min_words = min_words
        self.max_words = max_words
        self._garbage_regex = re.compile('|'.join(self.GARBAGE_PATTERNS), re.IGNORECASE)
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            max_special_char_ratio=crawler.settings.getfloat('MAX_SPECIAL_CHAR_RATIO', 0.3),
            min_words=crawler.settings.getint('MIN_ARTICLE_WORDS', 20),
            max_words=crawler.settings.getint('MAX_ARTICLE_WORDS', 50000),
        )
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        body = adapter.get('article_body', '')
        url = adapter.get('url', 'unknown')
        
        if not body:
            raise DropItem(f"Empty article body: {url}")
        
        # Check for garbage patterns
        if self._garbage_regex.search(body):
            spider.logger.warning(f"Garbage pattern detected in {url}")
            raise DropItem(f"Garbage content detected: {url}")
        
        # Check special character ratio
        alpha_count = sum(1 for c in body if c.isalpha())
        total_count = len(body.replace(' ', ''))
        
        if total_count > 0:
            alpha_ratio = alpha_count / total_count
            if alpha_ratio < (1 - self.max_special_char_ratio):
                spider.logger.warning(f"High special char ratio in {url}: {1 - alpha_ratio:.2f}")
                raise DropItem(f"Too many special characters: {url}")
        
        # Check word count
        word_count = len(body.split())
        if word_count < self.min_words:
            raise DropItem(f"Article too short ({word_count} words): {url}")
        if word_count > self.max_words:
            spider.logger.warning(f"Unusually long article ({word_count} words): {url}")
        
        return item


# ============================================================================
# Date Filter Pipeline
# ============================================================================

class DateFilterPipeline:
    """
    Filter articles by publication date.
    
    This is a fallback for spiders that don't support API-level date filtering.
    Configure via settings:
        - FILTER_START_DATE: Start date (YYYY-MM-DD)
        - FILTER_END_DATE: End date (YYYY-MM-DD)
        - DATE_FILTER_ENABLED: Enable/disable filtering (default: False)
    """
    
    def __init__(self, start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None,
                 enabled: bool = False):
        self.start_date = start_date
        self.end_date = end_date
        self.enabled = enabled
    
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('DATE_FILTER_ENABLED', False)
        
        start_date = None
        end_date = None
        
        if enabled:
            start_str = crawler.settings.get('FILTER_START_DATE')
            end_str = crawler.settings.get('FILTER_END_DATE')
            
            if start_str:
                try:
                    start_date = DHAKA_TZ.localize(
                        datetime.strptime(start_str, '%Y-%m-%d')
                    )
                except ValueError:
                    logger.warning(f"Invalid FILTER_START_DATE: {start_str}")
            
            if end_str:
                try:
                    end_date = DHAKA_TZ.localize(
                        datetime.strptime(end_str, '%Y-%m-%d').replace(
                            hour=23, minute=59, second=59
                        )
                    )
                except ValueError:
                    logger.warning(f"Invalid FILTER_END_DATE: {end_str}")
        
        return cls(start_date=start_date, end_date=end_date, enabled=enabled)
    
    def process_item(self, item, spider):
        if not self.enabled:
            return item
        
        adapter = ItemAdapter(item)
        pub_date_str = adapter.get('publication_date')
        
        if not pub_date_str or pub_date_str == "Unknown":
            # Can't filter without date, let it pass
            return item
        
        try:
            pub_date = self._parse_date(pub_date_str)
            if not pub_date:
                return item
            
            # Check date range
            if self.start_date and pub_date < self.start_date:
                raise DropItem(f"Article date {pub_date} before start date {self.start_date}")
            
            if self.end_date and pub_date > self.end_date:
                raise DropItem(f"Article date {pub_date} after end date {self.end_date}")
            
        except Exception as e:
            logger.debug(f"Date parsing error for {adapter.get('url')}: {e}")
        
        return item
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.split('+')[0].split('Z')[0], fmt)
                if dt.tzinfo is None:
                    dt = DHAKA_TZ.localize(dt)
                return dt
            except ValueError:
                continue
        
        return None


# ============================================================================
# Database Pipeline (Thread-Safe)
# ============================================================================

class SharedSQLitePipeline:
    """
    Thread-safe SQLite database for all spiders.
    
    Features:
        - Thread-safe connection pooling
        - WAL mode for better concurrency
        - Automatic schema creation
        - Duplicate URL detection
    """
    
    def __init__(self, db_path: str = 'news_articles.db'):
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
    
    @classmethod
    def from_crawler(cls, crawler):
        db_path = crawler.settings.get('DATABASE_PATH', 'news_articles.db')
        return cls(db_path=db_path)
    
    def _get_connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=10000;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            
            self._local.connection = conn
        
        return self._local.connection
    
    def open_spider(self, spider):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create articles table with all fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                paper_name TEXT NOT NULL,
                headline TEXT NOT NULL,
                article TEXT NOT NULL,
                sub_title TEXT,
                category TEXT,
                author TEXT,
                publication_date TEXT,
                modification_date TEXT,
                image_url TEXT,
                keywords TEXT,
                source_language TEXT,
                word_count INTEGER,
                content_hash TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON articles(url);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_name ON articles(paper_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_publication_date ON articles(publication_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON articles(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON articles(content_hash);")
        
        conn.commit()
        spider.logger.info(f"Database initialized at {self.db_path}")
    
    def close_spider(self, spider):
        """Close database connection and log statistics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get count for this spider
            cursor.execute(
                "SELECT COUNT(*) FROM articles WHERE paper_name = ?",
                (spider.name,)
            )
            count = cursor.fetchone()[0]
            spider.logger.info(f"Spider {spider.name} has {count} articles in database")
            
            # Optimize database
            cursor.execute("PRAGMA optimize;")
            conn.commit()
            conn.close()
            self._local.connection = None
            
        except Exception as e:
            spider.logger.error(f"Error closing database: {e}")
    
    def process_item(self, item, spider):
        """Save item to database with duplicate detection."""
        adapter = ItemAdapter(item)
        url = adapter.get("url")
        
        if not url:
            raise DropItem("Missing URL field")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check for duplicate URL
        with self._lock:
            cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
            if cursor.fetchone():
                spider.logger.debug(f"Duplicate URL skipped: {url}")
                raise DropItem(f"Duplicate URL: {url}")
            
            # Also check content hash if available
            content_hash = adapter.get("content_hash")
            if content_hash:
                cursor.execute("SELECT id FROM articles WHERE content_hash = ?", (content_hash,))
                if cursor.fetchone():
                    spider.logger.debug(f"Duplicate content skipped: {url}")
                    raise DropItem(f"Duplicate content: {url}")
            
            try:
                cursor.execute("""
                    INSERT INTO articles (
                        url, paper_name, headline, article, sub_title, category,
                        author, publication_date, modification_date, image_url,
                        keywords, source_language, word_count, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    url,
                    adapter.get("paper_name", spider.name),
                    adapter.get("headline", ""),
                    adapter.get("article_body", ""),
                    adapter.get("sub_title"),
                    adapter.get("category"),
                    adapter.get("author"),
                    adapter.get("publication_date"),
                    adapter.get("modification_date"),
                    adapter.get("image_url"),
                    adapter.get("keywords"),
                    adapter.get("source_language"),
                    adapter.get("word_count"),
                    content_hash,
                ))
                conn.commit()
                spider.logger.debug(f"Saved: {adapter.get('headline', '')[:50]}...")
                
            except sqlite3.Error as e:
                spider.logger.error(f"Database error for {url}: {e}")
                raise DropItem(f"Database error: {e}")
        
        return item
