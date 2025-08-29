import scrapy
from datetime import datetime, timedelta
import pytz
import json
import sqlite3
from urllib.parse import urlencode
from typing import Dict, List, Optional, Generator, Any
from BDNewsPaper.items import ArticleItem


class ProthomaloSpider(scrapy.Spider):
    name = "prothomalo"
    allowed_domains = ["en.prothomalo.com"]
    start_urls = ["https://en.prothomalo.com"]

    # Configuration - can be overridden via spider arguments
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.25,
        'AUTOTHROTTLE_MAX_DELAY': 2.0,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
    }

    def __init__(self, *args, **kwargs):
        super(ProthomaloSpider, self).__init__(*args, **kwargs)
        
        # Configuration with command-line argument support
        self.local_timezone = pytz.timezone("Asia/Dhaka")
        
        # Date range configuration - can be overridden via arguments
        start_date = kwargs.get('start_date', '2024-06-01')
        end_date = kwargs.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date, end_of_day=True)
        
        self.startDateTimeUnix = int(self.start_dt.timestamp() * 1000)
        self.endDateTimeUnix = int(self.end_dt.timestamp() * 1000)

        # Pagination settings
        self.limit = int(kwargs.get('page_limit', 1000))
        self.max_pages = int(kwargs.get('max_pages', 50))  # Safety limit
        
        # API configuration
        self.base_url = "https://en.prothomalo.com/api/v1/advanced-search"
        
        # Enhanced categories with better organization
        self.categories = {
            "Bangladesh": "16600,16725,16727,16728,17129,17134,17135,17136,17137,17139,35627",
            "Sports": "16603,16747,16748,17138",
            "Opinion": "16606,16751,16752,17202",
            "Entertainment": "16604,16762,35629,35639,35640",
            "Youth": "16622,16756,17140",
            "Environment": "16623,16767,16768",
            "Science & Tech": "16605,16770,16771,17143",
            "Corporate": "16624,16772,16773",
        }
        
        # Filter categories if specified
        selected_categories = kwargs.get('categories')
        if selected_categories:
            cat_list = [cat.strip() for cat in selected_categories.split(',')]
            self.categories = {k: v for k, v in self.categories.items() if k in cat_list}
        
        # Statistics tracking
        self.stats = {
            'api_requests': 0,
            'articles_found': 0,
            'articles_processed': 0,
            'duplicates_skipped': 0,
            'errors': 0
        }
        
        # Database connection will be initialized per request to avoid threading issues
        self.db_path = kwargs.get('db_path', 'news_articles.db')
        
        self.logger.info(f"Spider initialized for date range: {start_date} to {end_date}")
        self.logger.info(f"Categories to scrape: {list(self.categories.keys())}")

    def _parse_date(self, date_str: str, end_of_day: bool = False) -> datetime:
        """Parse date string and localize to Dhaka timezone."""
        try:
            if len(date_str.split()) == 1:  # Only date provided
                time_part = "23:59:59" if end_of_day else "00:00:00"
                date_str = f"{date_str} {time_part}"
            
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return self.local_timezone.localize(dt)
        except ValueError as e:
            self.logger.error(f"Invalid date format '{date_str}': {e}")
            # Fallback to reasonable defaults
            if end_of_day:
                return self.local_timezone.localize(datetime.now())
            else:
                return self.local_timezone.localize(datetime.now() - timedelta(days=30))

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial API requests for each category."""
        for category, section_id in self.categories.items():
            self.logger.info(f"Starting requests for category: {category}")
            yield self.make_api_request(category, section_id, offset=0)

    def make_api_request(self, category: str, section_id: str, offset: int = 0) -> scrapy.Request:
        """Create optimized API request with proper URL encoding."""
        # Build query parameters properly
        params = {
            'section-id': section_id,
            'published-after': self.startDateTimeUnix,
            'published-before': self.endDateTimeUnix,
            'sort': 'latest-published',
            'offset': offset,
            'limit': self.limit,
            'fields': ','.join([
                'headline', 'subheadline', 'slug', 'url', 'tags',
                'hero-image-s3-key', 'hero-image-caption', 'hero-image-metadata',
                'last-published-at', 'alternative', 'authors', 'author-name',
                'author-id', 'sections', 'story-template', 'metadata',
                'hero-image-attribution', 'access'
            ])
        }
        
        api_url = f"{self.base_url}?{urlencode(params)}"
        
        return scrapy.Request(
            url=api_url,
            callback=self.parse_api_response,
            meta={
                "category": category,
                "section_id": section_id,
                "offset": offset,
                "page_num": offset // self.limit + 1
            },
            errback=self.handle_request_failure,
            dont_filter=True,  # Allow duplicate requests for pagination
        )

    def parse_api_response(self, response: scrapy.http.Response) -> Generator[scrapy.Request, None, None]:
        """Parse API response and extract article URLs."""
        self.stats['api_requests'] += 1
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from {response.url}: {e}")
            self.stats['errors'] += 1
            return

        category = response.meta["category"]
        section_id = response.meta["section_id"]
        offset = response.meta["offset"]
        page_num = response.meta["page_num"]

        total_results = data.get("total", 0)
        items = data.get("items", [])
        
        self.logger.info(
            f"Category '{category}' page {page_num}: "
            f"Found {len(items)} articles (Total: {total_results})"
        )

        # Process articles
        for item in items:
            url = item.get("url")
            if url:
                full_url = response.urljoin(url)
                
                # Check for duplicates using a separate connection
                if not self._is_url_in_db(full_url):
                    self.stats['articles_found'] += 1
                    yield scrapy.Request(
                        url=full_url,
                        callback=self.parse_news_article,
                        meta={
                            "category": category,
                            "api_data": item  # Pass API data for fallback
                        },
                        errback=self.handle_request_failure,
                    )
                else:
                    self.stats['duplicates_skipped'] += 1

        # Smart pagination with safety limits
        if (offset + self.limit < total_results and 
            page_num < self.max_pages and 
            len(items) > 0):  # Don't paginate if no items returned
            
            next_offset = offset + self.limit
            self.logger.info(f"Requesting next page for {category}: page {page_num + 1}")
            yield self.make_api_request(category, section_id, offset=next_offset)
        else:
            self.logger.info(f"Completed category '{category}' - processed {page_num} pages")

    def _is_url_in_db(self, url: str) -> bool:
        """Check if URL exists in database using a separate connection."""
        try:
            # Use a separate connection for each check to avoid threading issues
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.warning(f"Database check failed for {url}: {e}")
            return False  # Assume not duplicate if check fails

    def parse_news_article(self, response: scrapy.http.Response) -> Generator[ArticleItem, None, None]:
        """Enhanced article parsing with multiple extraction strategies."""
        self.stats['articles_processed'] += 1
        self.logger.debug(f"Processing article: {response.url}")
        
        # Strategy 1: JSON-LD structured data (primary)
        item = self._extract_from_jsonld(response)
        
        # Strategy 2: Fallback to API data if JSON-LD fails
        if not item:
            api_data = response.meta.get('api_data')
            if api_data:
                item = self._extract_from_api_data(api_data, response)
        
        # Strategy 3: HTML parsing fallback (last resort)
        if not item:
            item = self._extract_from_html(response)
        
        if item:
            # Add category from meta
            item['category'] = response.meta.get('category', 'Unknown')
            yield item
        else:
            self.logger.warning(f"Could not extract data from {response.url}")
            self.stats['errors'] += 1

    def _extract_from_jsonld(self, response: scrapy.http.Response) -> Optional[ArticleItem]:
        """Extract data from JSON-LD structured data."""
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
                
                return self._create_article_item(data, response)
                
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.debug(f"JSON-LD parsing error in {response.url}: {e}")
                continue
        
        return None

    def _extract_from_api_data(self, api_data: Dict[str, Any], response: scrapy.http.Response) -> Optional[ArticleItem]:
        """Extract data from API response as fallback."""
        try:
            # Convert API data to JSON-LD-like structure
            converted_data = {
                "headline": api_data.get("headline"),
                "url": response.url,
                "datePublished": api_data.get("last-published-at"),
                "author": api_data.get("authors", []),
                "image": api_data.get("hero-image-s3-key"),
            }
            return self._create_article_item(converted_data, response)
        except Exception as e:
            self.logger.debug(f"API data extraction error for {response.url}: {e}")
            return None

    def _extract_from_html(self, response: scrapy.http.Response) -> Optional[ArticleItem]:
        """HTML parsing fallback method."""
        try:
            item = ArticleItem()
            
            # Extract basic fields from HTML
            item["headline"] = response.css('h1::text').get() or "No headline available"
            item["url"] = response.url
            item["paper_name"] = "ProthomAlo"
            item["publication_date"] = "Unknown date"
            item["article_body"] = " ".join(response.css('div.story-content p::text').getall()) or "No content"
            
            # Only return if we have meaningful content
            if len(item["article_body"]) > 50:
                return item
                
        except Exception as e:
            self.logger.debug(f"HTML extraction error for {response.url}: {e}")
        
        return None

    def _create_article_item(self, data: Dict[str, Any], response: scrapy.http.Response) -> ArticleItem:
        """Create ArticleItem with enhanced data validation."""
        item = ArticleItem()
        
        # Basic fields with validation
        item["headline"] = self._clean_text(data.get("headline", "No headline available"))
        item["url"] = data.get("url", response.url)
        item["paper_name"] = "ProthomAlo"
        
        # Date handling with better parsing
        item["publication_date"] = self._parse_article_date(data.get("datePublished"))
        item["modification_date"] = self._parse_article_date(data.get("dateModified"))
        
        # Content with validation
        article_body = self._clean_text(data.get("articleBody", ""))
        item["article_body"] = article_body if len(article_body) > 20 else "No article body"
        
        # Enhanced image handling
        item["image_url"] = self._extract_image_urls(data.get("image"))
        
        # Keywords processing
        item["keywords"] = self._process_keywords(data.get("keywords"))
        
        # Publisher information
        publisher_data = data.get("publisher", {})
        item["publisher"] = self._clean_text(publisher_data.get("name", "ProthomAlo"))
        
        # Enhanced author extraction
        item["author"] = self._extract_authors(data.get("author"))
        
        return item

    def _clean_text(self, text: Any) -> str:
        """Clean and validate text content."""
        if not text:
            return ""
        
        if isinstance(text, list):
            text = " ".join(str(t) for t in text if t)
        
        text = str(text).strip()
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text

    def _parse_article_date(self, date_str: Any) -> str:
        """Parse article date with better error handling."""
        if not date_str:
            return "Unknown date"
        
        try:
            # Handle various date formats
            if isinstance(date_str, str):
                # Try ISO format first
                if 'T' in date_str:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.isoformat()
                return date_str
            return str(date_str)
        except Exception:
            return "Unknown date"

    def _extract_image_urls(self, image_data: Any) -> Optional[List[str]]:
        """Extract and validate image URLs."""
        if not image_data:
            return None
        
        urls = []
        
        if isinstance(image_data, list):
            for img in image_data:
                if isinstance(img, dict) and img.get("url"):
                    urls.append(img["url"])
                elif isinstance(img, str) and img.startswith(('http://', 'https://')):
                    urls.append(img)
        elif isinstance(image_data, dict) and image_data.get("url"):
            urls.append(image_data["url"])
        elif isinstance(image_data, str) and image_data.startswith(('http://', 'https://')):
            urls.append(image_data)
        
        return urls if urls else None

    def _process_keywords(self, keywords: Any) -> Optional[str]:
        """Process keywords with better validation."""
        if not keywords:
            return None
        
        if isinstance(keywords, list):
            # Filter and clean keywords
            clean_keywords = [
                self._clean_text(kw) for kw in keywords 
                if kw and isinstance(kw, (str, dict))
            ]
            # Handle dict keywords (extract name or value)
            processed = []
            for kw in clean_keywords:
                if isinstance(kw, dict):
                    processed.append(kw.get('name', kw.get('value', str(kw))))
                else:
                    processed.append(str(kw))
            
            return ", ".join(processed) if processed else None
        
        return self._clean_text(keywords) if keywords else None

    def _extract_authors(self, authors: Any) -> List[str]:
        """Enhanced author extraction with better validation."""
        if not authors:
            return ["Unknown"]
        
        author_list = []
        
        if isinstance(authors, list):
            for author in authors:
                if isinstance(author, dict):
                    name = author.get("name") or author.get("author-name", "Unknown")
                    author_list.append(self._clean_text(name))
                elif isinstance(author, str):
                    author_list.append(self._clean_text(author))
        elif isinstance(authors, dict):
            name = authors.get("name") or authors.get("author-name", "Unknown")
            author_list.append(self._clean_text(name))
        elif isinstance(authors, str):
            author_list.append(self._clean_text(authors))
        
        # Filter out empty names
        author_list = [author for author in author_list if author and author != "Unknown"]
        
        return author_list if author_list else ["Unknown"]

    def handle_request_failure(self, failure):
        """Enhanced error handling with more details."""
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
        """Enhanced spider closing with statistics."""
        self.logger.info("=" * 50)
        self.logger.info("PROTHOMALO SPIDER STATISTICS")
        self.logger.info("=" * 50)
        self.logger.info(f"API requests made: {self.stats['api_requests']}")
        self.logger.info(f"Articles found: {self.stats['articles_found']}")
        self.logger.info(f"Articles processed: {self.stats['articles_processed']}")
        self.logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        self.logger.info(f"Errors encountered: {self.stats['errors']}")
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info("=" * 50)
