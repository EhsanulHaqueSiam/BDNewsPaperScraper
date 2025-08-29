import scrapy
import json
import sqlite3
import re
import html
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator, Any
from scrapy.exceptions import CloseSpider
from BDNewsPaper.items import ArticleItem


class DailysunSpider(scrapy.Spider):
    name = "dailysun"
    allowed_domains = ["www.daily-sun.com"]

    # Enhanced custom settings for better performance
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.25,
        'AUTOTHROTTLE_MAX_DELAY': 2.0,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'ROBOTSTXT_OBEY': False,
    }

    # Default categories - can be overridden via command line
    DEFAULT_CATEGORIES = [
        "national",
        "economy",
        "diplomacy",
        "sports",
        "bashundhara-shuvosangho",
        "world",
        "opinion",
        "sun-faith",
        "feature",
        "sci-tech",
        "education-online",
        "health",
        "entertainment",
        "corporate",
    ]

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.daily-sun.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Timezone configuration
        self.dhaka_tz = pytz.timezone('Asia/Dhaka')
        
        # Parse command-line arguments with proper error handling
        self._parse_arguments(kwargs)
        
        # Initialize database connection with proper error handling
        self._init_database()
        
        # Initialize statistics tracking
        self._init_statistics()
        
        # Initialize pagination state
        self._init_pagination_state()
        
        # Create start URLs based on selected categories
        self.start_urls = [
            f"https://www.daily-sun.com/api/catpagination/online/{category}"
            for category in self.categories
        ]
        
        self.logger.info(f"DailySun Spider initialized")
        self.logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"Categories: {self.categories}")
        self.logger.info(f"Max pages per category: {self.max_pages}")

    def _parse_arguments(self, kwargs: Dict[str, Any]) -> None:
        """Parse and validate command-line arguments."""
        # Date range parsing with timezone awareness
        try:
            start_date_str = kwargs.get('start_date', '2024-06-01')
            end_date_str = kwargs.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            
            self.start_date = self._parse_date(start_date_str)
            self.end_date = self._parse_date(end_date_str, end_of_day=True)
            
            if self.start_date > self.end_date:
                self.logger.warning("Start date is after end date, swapping...")
                self.start_date, self.end_date = self.end_date, self.start_date
                
        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            self.start_date = self.dhaka_tz.localize(datetime(2024, 6, 1))
            self.end_date = self.dhaka_tz.localize(datetime.now())

        # Categories parsing
        categories_str = kwargs.get('categories', '')
        if categories_str:
            requested_categories = [cat.strip() for cat in categories_str.split(',')]
            self.categories = [
                cat for cat in requested_categories 
                if cat in self.DEFAULT_CATEGORIES
            ]
            if not self.categories:
                self.logger.warning("No valid categories found, using all categories")
                self.categories = self.DEFAULT_CATEGORIES
        else:
            self.categories = self.DEFAULT_CATEGORIES

        # Pagination settings
        try:
            self.max_pages = int(kwargs.get('max_pages', 100))
            self.max_pages = min(max(self.max_pages, 1), 5000)  # Safety bounds
        except (ValueError, TypeError):
            self.max_pages = 100

        # Database path
        self.db_path = kwargs.get('db_path', 'news_articles.db')
        
        # Statistics toggle
        self.enable_stats = str(kwargs.get('enable_stats', 'true')).lower() == 'true'

    def _parse_date(self, date_str: str, end_of_day: bool = False) -> datetime:
        """Parse date string and localize to Dhaka timezone."""
        try:
            if len(date_str.split()) == 1:  # Only date provided
                time_part = "23:59:59" if end_of_day else "00:00:00"
                date_str = f"{date_str} {time_part}"
            
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return self.dhaka_tz.localize(dt)
        except ValueError as e:
            self.logger.error(f"Invalid date format '{date_str}': {e}")
            # Fallback to reasonable defaults
            if end_of_day:
                return self.dhaka_tz.localize(datetime.now())
            else:
                return self.dhaka_tz.localize(datetime.now() - timedelta(days=30))

    def _init_database(self) -> None:
        """Initialize database connection with proper error handling."""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30.0)
            self.cursor = self.conn.cursor()
            
            # Enable WAL mode for better concurrent access
            self.cursor.execute('PRAGMA journal_mode=WAL')
            self.cursor.execute('PRAGMA synchronous=NORMAL')
            self.cursor.execute('PRAGMA cache_size=10000')
            self.cursor.execute('PRAGMA temp_store=MEMORY')
            
            # Ensure articles table exists
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
            
            self.logger.info("Database initialized successfully")
            
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def _init_statistics(self) -> None:
        """Initialize statistics tracking."""
        self.stats = {
            'api_requests': 0,
            'articles_found': 0,
            'articles_processed': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'categories_completed': 0,
            'start_time': datetime.now()
        }

    def _init_pagination_state(self) -> None:
        """Initialize pagination state tracking."""
        self.continue_scraping = {category: True for category in self.categories}
        self.processed_urls = set()
        self.pagination_state = {
            category: {'current_page': 1, 'consecutive_empty': 0, 'max_empty': 3}
            for category in self.categories
        }

    def is_url_in_db(self, url: str) -> bool:
        """Check if URL exists in database using a separate connection for thread safety."""
        try:
            # Use a separate connection for each check to avoid threading issues
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,))
                result = cursor.fetchone() is not None
                
                if result:
                    self.stats['duplicates_skipped'] += 1
                
                return result
        except sqlite3.Error as e:
            self.logger.error(f"Database error checking URL {url}: {e}")
            return False

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Send requests for each category with enhanced error handling."""
        for start_url in self.start_urls:
            category = start_url.split("/")[-1]
            
            self.stats['api_requests'] += 1
            
            yield scrapy.Request(
                url=start_url,
                headers=self.headers,
                callback=self.parse_api,
                meta={"page": 1, "category": category},
                errback=self.handle_request_failure,
                dont_filter=True
            )

    def parse_api(self, response) -> Generator[scrapy.Request, None, None]:
        """Parse JSON response and extract articles with enhanced error handling."""
        category = response.meta["category"]
        page = response.meta["page"]
        
        try:
            if response.status != 200:
                self.logger.warning(f"Non-200 status {response.status} for {category} page {page}")
                self.stats['errors'] += 1
                return

            if not response.text.strip():
                self.logger.warning(f"Empty response for {category} page {page}")
                self._handle_empty_page(category, page)
                return

            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {category} page {page}: {e}")
                self.stats['errors'] += 1
                return

            articles = data.get("category", {}).get("data", [])
            
            if not articles:
                self.logger.warning(f"No articles found for {category} page {page}")
                self._handle_empty_page(category, page)
                return

            if not self.continue_scraping[category]:
                self.logger.info(f"Skipping category {category} as scraping has stopped")
                return

            articles_found = 0
            for article in articles:
                request = self._process_article(article, category)
                if request is None:
                    # Date limit reached, stop this category
                    self.continue_scraping[category] = False
                    break
                elif isinstance(request, scrapy.Request):
                    articles_found += 1
                    self.stats['articles_found'] += 1
                    yield request

            self.logger.debug(f"{category} page {page}: {articles_found} articles processed")

            # Handle pagination with safety limits
            if (self.continue_scraping[category] and 
                page < self.max_pages and 
                articles_found > 0):
                
                self.pagination_state[category]['consecutive_empty'] = 0
                next_page = page + 1
                self.stats['api_requests'] += 1
                
                yield scrapy.Request(
                    url=response.url,
                    headers=self.headers,
                    callback=self.parse_api,
                    meta={"page": next_page, "category": category},
                    errback=self.handle_request_failure,
                    dont_filter=True
                )
            else:
                if articles_found == 0:
                    self._handle_empty_page(category, page)
                else:
                    self.logger.info(f"Completed category '{category}' - processed {page} pages")
                    self.continue_scraping[category] = False
                    self.stats['categories_completed'] += 1

        except Exception as e:
            self.logger.error(f"Unexpected error parsing {category} page {page}: {e}")
            self.stats['errors'] += 1

    def _process_article(self, article: Dict[str, Any], category: str) -> Optional[scrapy.Request]:
        """Process individual article with enhanced validation."""
        try:
            n_id = article.get("n_id")
            created_at = article.get("created_at")
            n_head = article.get("n_head")

            if not n_id or not created_at:
                self.logger.debug(f"Missing required fields in article: {article}")
                return None

            # Parse and validate article date with timezone awareness
            try:
                publish_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                publish_date = self.dhaka_tz.localize(publish_date)
                
                # Check if article is before start date (stop condition)
                if publish_date < self.start_date:
                    self.logger.info(f"Stopping {category}: Article date {publish_date} < Start date {self.start_date}")
                    return None
                
                # Check if article is after end date (skip article)
                if publish_date > self.end_date:
                    self.logger.debug(f"Skipping future article: {publish_date} > {self.end_date}")
                    return None  # Continue processing but skip this article
                    
            except ValueError as e:
                self.logger.warning(f"Invalid date format '{created_at}': {e}")
                return None

            # Construct article URL
            post_url = f"https://www.daily-sun.com/post/{n_id}"

            # Check for duplicates
            if self.is_url_in_db(post_url):
                self.logger.debug(f"Skipping duplicate URL: {post_url}")
                return None

            # Add to processed URLs set
            if post_url in self.processed_urls:
                self.logger.debug(f"URL already processed in session: {post_url}")
                return None
            
            self.processed_urls.add(post_url)

            return scrapy.Request(
                url=post_url,
                headers=self.headers,
                callback=self.parse_post,
                meta={
                    "publish_date": created_at,
                    "category": category,
                    "post_url": post_url,
                    "news_id": n_id,
                    "headline": n_head,
                },
                errback=self.handle_request_failure,
                dont_filter=False
            )

        except Exception as e:
            self.logger.error(f"Error processing article {article}: {e}")
            self.stats['errors'] += 1
            return None

    def _handle_empty_page(self, category: str, page: int) -> None:
        """Handle empty pages with consecutive tracking."""
        self.pagination_state[category]['consecutive_empty'] += 1
        
        if self.pagination_state[category]['consecutive_empty'] >= self.pagination_state[category]['max_empty']:
            self.logger.info(f"Stopping {category} after {self.pagination_state[category]['consecutive_empty']} consecutive empty pages")
            self.continue_scraping[category] = False
            self.stats['categories_completed'] += 1

    def parse_post(self, response) -> Optional[ArticleItem]:
        """Parse individual article pages with enhanced extraction."""
        if response.status != 200:
            self.logger.warning(f"Non-200 status {response.status} for article: {response.url}")
            self.stats['errors'] += 1
            return None

        try:
            item = self._extract_article_data(response)
            if item and self._validate_article(item):
                self.stats['articles_processed'] += 1
                return item
            else:
                self.logger.warning(f"Article validation failed for {response.url}")
                self.stats['errors'] += 1
                return None
                
        except Exception as e:
            self.logger.error(f"Error parsing article {response.url}: {e}")
            self.stats['errors'] += 1
            return None

    def _extract_article_data(self, response) -> Optional[ArticleItem]:
        """Extract article data with multiple fallback strategies."""
        item = ArticleItem()
        
        # Basic metadata from request meta
        item["headline"] = self._clean_text(response.meta.get("headline", "No headline"))
        item["url"] = response.meta["post_url"]
        item["publication_date"] = response.meta["publish_date"]
        item["paper_name"] = "daily-sun"
        item["category"] = response.meta["category"]
        
        # Extract article body with enhanced fallback strategies
        item["article_body"] = self._extract_article_body(response)
        
        return item

    def _extract_article_body(self, response) -> str:
        """Extract article body with multiple strategies."""
        # Strategy 1: Extract from Next.js script data (original method)
        body = self._extract_from_nextjs_script(response)
        if body and len(body) > 50:
            return body
        
        # Strategy 2: Extract from JSON-LD structured data
        body = self._extract_from_jsonld(response)
        if body and len(body) > 50:
            return body
        
        # Strategy 3: Direct HTML parsing fallback
        body = self._extract_from_html(response)
        if body and len(body) > 50:
            return body
        
        # Strategy 4: Meta description fallback
        meta_desc = response.xpath("//meta[@name='description']/@content").get()
        if meta_desc and len(meta_desc) > 50:
            self.logger.warning(f"Using meta description for {response.url}")
            return self._clean_text(meta_desc)
        
        self.logger.warning(f"Could not extract article body from {response.url}")
        return "No content available"

    def _extract_from_nextjs_script(self, response) -> Optional[str]:
        """Extract from Next.js script data (original working method)."""
        try:
            script_content = response.xpath(
                "//script[contains(text(), 'self.__next_f.push([1,\"\\u0026lt;')]/text()"
            ).get()

            if script_content:
                # Extract JSON-like data from the script content
                start = script_content.find("[")
                end = script_content.find("]") + 1
                data = script_content[start:end]

                # Parse the JSON data
                parsed_data = json.loads(data)

                # Decode the HTML content
                html_content = html.unescape(parsed_data[1])

                # Clean HTML tags using regex
                plain_text = re.sub(r"<[^>]*>", "", html_content)
                
                # Clean up whitespace
                plain_text = self._clean_text(plain_text)
                
                return plain_text if len(plain_text) > 50 else None
                
        except (json.JSONDecodeError, IndexError, TypeError) as e:
            self.logger.debug(f"NextJS script extraction failed for {response.url}: {e}")
            
        return None

    def _extract_from_jsonld(self, response) -> Optional[str]:
        """Extract from JSON-LD structured data."""
        try:
            scripts = response.xpath("//script[@type='application/ld+json']/text()").getall()
            
            for script in scripts:
                try:
                    data = json.loads(script)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        data = next((item for item in data if item.get("@type") in ["Article", "NewsArticle"]), None)
                        if not data:
                            continue
                    elif data.get("@type") not in ["Article", "NewsArticle"]:
                        continue
                    
                    article_body = data.get("articleBody") or data.get("description")
                    if article_body and len(article_body) > 50:
                        return self._clean_text(article_body)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.debug(f"JSON-LD parsing error in {response.url}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"JSON-LD extraction failed for {response.url}: {e}")
            
        return None

    def _extract_from_html(self, response) -> Optional[str]:
        """Extract from HTML with multiple selectors."""
        try:
            # Try multiple content selectors
            content_selectors = [
                "//div[contains(@class, 'article-content')]//p/text()",
                "//div[contains(@class, 'post-content')]//p/text()",
                "//div[contains(@class, 'news-content')]//p/text()",
                "//article//p/text()",
                "//main//p/text()",
                ".post-content p::text",
                ".article-body p::text",
                ".content p::text"
            ]
            
            for selector in content_selectors:
                if selector.startswith("//"):
                    paragraphs = response.xpath(selector).getall()
                else:
                    paragraphs = response.css(selector).getall()
                
                if paragraphs:
                    content = " ".join(p.strip() for p in paragraphs if p.strip())
                    if len(content) > 50:
                        return self._clean_text(content)
                        
        except Exception as e:
            self.logger.debug(f"HTML extraction failed for {response.url}: {e}")
            
        return None

    def _clean_text(self, text: Any) -> str:
        """Clean and validate text content."""
        if not text:
            return ""
        
        if isinstance(text, list):
            text = " ".join(str(t) for t in text if t)
        
        text = str(text).strip()
        
        # Remove HTML entities
        text = html.unescape(text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common unwanted patterns
        text = re.sub(r'\[.*?\]', '', text)  # Remove [bracketed] content
        text = re.sub(r'\(.*?\)', '', text)  # Remove (parenthetical) content if too long
        
        return text.strip()

    def _validate_article(self, item: ArticleItem) -> bool:
        """Validate article data."""
        if not item.get('headline') or not item.get('article_body'):
            return False
        
        if len(item['headline']) < 5 or len(item['article_body']) < 50:
            return False
        
        # Check for placeholder content
        if item['article_body'] in ['No content available', 'No article body']:
            return False
        
        return True

    def handle_request_failure(self, failure):
        """Enhanced error handling with detailed logging."""
        self.stats['errors'] += 1
        url = failure.request.url
        error_msg = str(failure.value)
        
        # Log different types of failures differently
        if "DNS lookup failed" in error_msg:
            self.logger.warning(f"DNS lookup failed for {url}")
        elif "Connection refused" in error_msg:
            self.logger.warning(f"Connection refused for {url}")
        elif "timeout" in error_msg.lower():
            self.logger.warning(f"Request timeout for {url}")
        else:
            self.logger.error(f"Request failed for {url}: {error_msg}")

    def closed(self, reason):
        """Enhanced spider closing with comprehensive statistics."""
        runtime = datetime.now() - self.stats['start_time']
        total_articles = self.stats['articles_processed']
        total_requests = self.stats['api_requests']
        
        self.logger.info("=" * 60)
        self.logger.info("DAILY SUN SPIDER FINAL STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total Runtime: {runtime}")
        self.logger.info(f"API requests made: {self.stats['api_requests']}")
        self.logger.info(f"Articles found: {self.stats['articles_found']}")
        self.logger.info(f"Articles processed: {self.stats['articles_processed']}")
        self.logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        self.logger.info(f"Errors encountered: {self.stats['errors']}")
        self.logger.info(f"Categories completed: {self.stats['categories_completed']}/{len(self.categories)}")
        
        if total_requests > 0:
            success_rate = (total_articles / total_requests) * 100
            self.logger.info(f"Overall Success Rate: {success_rate:.1f}%")
        
        if runtime.total_seconds() > 0:
            rate = total_articles / (runtime.total_seconds() / 60)
            self.logger.info(f"Articles per minute: {rate:.1f}")
        
        self.logger.info(f"Total unique URLs processed: {len(self.processed_urls)}")
        self.logger.info("=" * 60)
        
        # Close database connection
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception as e:
                self.logger.error(f"Error closing database connection: {e}")