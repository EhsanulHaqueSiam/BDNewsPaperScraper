import scrapy
import json
import sqlite3
import threading
import time
import re
import html
from collections import defaultdict
from typing import Dict, List, Optional, Set, Generator, Any
from datetime import datetime, timedelta
import pytz

from BDNewsPaper.items import ArticleItem


class DailysunSpider(scrapy.Spider):
    name = "dailysun"
    allowed_domains = ["daily-sun.com"]
    
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

    custom_settings = {
        "CONCURRENT_REQUESTS": 32,
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.25,
        "AUTOTHROTTLE_MAX_DELAY": 2.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 16.0,
        "AUTOTHROTTLE_DEBUG": False,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [404],
    }

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.daily-sun.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.start_time = datetime.now()
        self.dhaka_tz = pytz.timezone('Asia/Dhaka')
        
        self._parse_cli_arguments(kwargs)
        self._initialize_configuration()
        self._setup_database()
        self._initialize_statistics()
        
        self.logger.info(f"DailySunSpider initialized with categories: {self.categories}")
        self.logger.info(f"Date range: {self.start_date} to {self.end_date}")
        self.logger.info(f"Max pages per category: {self.max_pages}")

    def _parse_cli_arguments(self, kwargs: Dict) -> None:
        try:
            self.start_date = datetime.strptime(
                kwargs.get('start_date', '2024-01-01'), '%Y-%m-%d'
            )
            self.end_date = datetime.strptime(
                kwargs.get('end_date', '2024-06-01'), '%Y-%m-%d'
            )
        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            self.start_date = datetime(2024, 1, 1)
            self.end_date = datetime(2024, 6, 1)

        try:
            self.max_pages = int(kwargs.get('max_pages', 100))
            self.max_pages = min(max(self.max_pages, 1), 5000)
        except (ValueError, TypeError):
            self.max_pages = 100

        self.db_path = kwargs.get('db_path', 'news_articles.db')
        
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

        enable_stats_value = kwargs.get('enable_stats', 'true')
        self.enable_stats = str(enable_stats_value).lower() == 'true'

    def _initialize_configuration(self) -> None:
        self.start_urls = [
            f"https://www.daily-sun.com/api/catpagination/online/{category}"
            for category in self.categories
        ]
        
        self.continue_scraping = {category: True for category in self.categories}
        self.processed_urls: Set[str] = set()
        self.duplicate_urls: Set[str] = set()
        
        self.pagination_state = {
            category: {'current_page': 1, 'consecutive_empty': 0, 'max_empty': 3}
            for category in self.categories
        }

    def _setup_database(self) -> None:
        self._db_lock = threading.Lock()
        self._local = threading.local()

    def _get_db_connection(self):
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.execute('PRAGMA journal_mode=WAL')
            self._local.connection.execute('PRAGMA synchronous=NORMAL')
            self._local.connection.execute('PRAGMA cache_size=10000')
            self._local.connection.execute('PRAGMA temp_store=MEMORY')
        return self._local.connection

    def _initialize_statistics(self) -> None:
        self.stats = {
            'requests_made': defaultdict(int),
            'articles_scraped': defaultdict(int),
            'articles_skipped': defaultdict(int),
            'errors': defaultdict(int),
            'total_requests': 0,
            'total_articles': 0,
            'total_duplicates': 0,
            'categories_completed': 0,
            'start_time': self.start_time,
        }
        
        if self.enable_stats:
            self._start_statistics_thread()

    def _start_statistics_thread(self) -> None:
        def log_stats():
            while True:
                time.sleep(60)
                if hasattr(self, '_should_stop_stats') and self._should_stop_stats:
                    break
                self._log_statistics()
        
        self._stats_thread = threading.Thread(target=log_stats, daemon=True)
        self._stats_thread.start()

    def _log_statistics(self) -> None:
        runtime = datetime.now() - self.start_time
        total_articles = sum(self.stats['articles_scraped'].values())
        total_requests = self.stats['total_requests']
        
        self.logger.info(f"=== DailySunSpider Statistics (Runtime: {runtime}) ===")
        self.logger.info(f"Total Requests: {total_requests}")
        self.logger.info(f"Total Articles: {total_articles}")
        self.logger.info(f"Total Duplicates: {self.stats['total_duplicates']}")
        
        if total_requests > 0:
            self.logger.info(f"Success Rate: {(total_articles/total_requests)*100:.1f}%")
        
        for category in self.categories:
            scraped = self.stats['articles_scraped'][category]
            skipped = self.stats['articles_skipped'][category]
            errors = self.stats['errors'][category]
            self.logger.info(f"  {category}: {scraped} articles, {skipped} skipped, {errors} errors")

    def is_url_in_db(self, url: str) -> bool:
        if url in self.processed_urls:
            return True
        
        if url in self.duplicate_urls:
            return True
        
        try:
            with self._db_lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,))
                result = cursor.fetchone() is not None
                
                if result:
                    self.duplicate_urls.add(url)
                    self.stats['total_duplicates'] += 1
                else:
                    self.processed_urls.add(url)
                
                return result
        except sqlite3.Error as e:
            self.logger.error(f"Database error checking URL {url}: {e}")
            return False

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        for start_url in self.start_urls:
            category = start_url.split("/")[-1]
            
            self.stats['requests_made'][category] += 1
            self.stats['total_requests'] += 1
            
            yield scrapy.Request(
                url=start_url,
                headers=self.headers,
                callback=self.parse_api,
                meta={
                    "page": 1,
                    "category": category,
                    "dont_cache": True
                },
                errback=self.handle_error,
                dont_filter=True
            )

    def parse_api(self, response) -> Generator[scrapy.Request, None, None]:
        category = response.meta["category"]
        page = response.meta["page"]
        
        try:
            if response.status != 200:
                self.logger.warning(f"Non-200 status {response.status} for {category} page {page}")
                self.stats['errors'][category] += 1
                return

            if not response.text.strip():
                self.logger.warning(f"Empty response for {category} page {page}")
                self._handle_empty_page(category, page)
                return

            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {category} page {page}: {e}")
                self.stats['errors'][category] += 1
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
                    yield request

            self.logger.debug(f"{category} page {page}: {articles_found} articles processed")

            # Handle pagination
            if (self.continue_scraping[category] and 
                page < self.max_pages and 
                articles_found > 0):
                
                self.pagination_state[category]['consecutive_empty'] = 0
                yield self._generate_next_page_request(category, page)
            else:
                if articles_found == 0:
                    self._handle_empty_page(category, page)
                else:
                    self.logger.info(f"Completed category '{category}' - processed {page} pages")
                    self.continue_scraping[category] = False
                    self.stats['categories_completed'] += 1

        except Exception as e:
            self.logger.error(f"Unexpected error parsing {category} page {page}: {e}")
            self.stats['errors'][category] += 1

    def _process_article(self, article: Dict[str, Any], category: str) -> Optional[scrapy.Request]:
        try:
            n_id = article.get("n_id")
            created_at = article.get("created_at")
            n_head = article.get("n_head")

            if not n_id or not created_at:
                self.logger.debug(f"Missing required fields in article: {article}")
                return None

            # Check date range
            try:
                publish_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                
                if publish_date < self.start_date:
                    self.logger.info(f"Stopping {category}: Article date {publish_date} < Start date {self.start_date}")
                    return None
                
                if publish_date > self.end_date:
                    self.logger.debug(f"Skipping future article: {publish_date} > {self.end_date}")
                    return None
                    
            except ValueError as e:
                self.logger.warning(f"Invalid date format '{created_at}': {e}")
                return None

            # Construct article URL
            post_url = f"https://www.daily-sun.com/post/{n_id}"

            # Check for duplicates
            if self.is_url_in_db(post_url):
                self.stats['articles_skipped'][category] += 1
                self.logger.debug(f"Skipping duplicate URL: {post_url}")
                return None

            # Generate article request
            self.stats['requests_made'][category] += 1
            self.stats['total_requests'] += 1
            
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
                    "dont_cache": True
                },
                errback=self.handle_error,
                dont_filter=False
            )

        except Exception as e:
            self.logger.error(f"Error processing article {article}: {e}")
            self.stats['errors'][category] += 1
            return None

    def _handle_empty_page(self, category: str, page: int) -> None:
        self.pagination_state[category]['consecutive_empty'] += 1
        
        if self.pagination_state[category]['consecutive_empty'] >= self.pagination_state[category]['max_empty']:
            self.logger.info(f"Stopping {category} after {self.pagination_state[category]['consecutive_empty']} consecutive empty pages")
            self.continue_scraping[category] = False
            self.stats['categories_completed'] += 1

    def _generate_next_page_request(self, category: str, page: int) -> scrapy.Request:
        next_page = page + 1
        next_url = f"https://www.daily-sun.com/api/catpagination/online/{category}"
        
        # Add page parameter to URL for DailySun API
        if next_page > 1:
            next_url += f"?page={next_page}"
        
        self.stats['requests_made'][category] += 1
        self.stats['total_requests'] += 1
        
        return scrapy.Request(
            url=next_url,
            headers=self.headers,
            callback=self.parse_api,
            meta={
                "page": next_page,
                "category": category,
                "dont_cache": True
            },
            errback=self.handle_error,
            dont_filter=True
        )

    def parse_post(self, response) -> Optional[ArticleItem]:
        if response.status != 200:
            self.logger.warning(f"Non-200 status {response.status} for article: {response.url}")
            self.stats['errors'][response.meta['category']] += 1
            return None

        try:
            item = self._extract_article_data(response)
            if item and self._validate_article(item, response.meta['category']):
                self.stats['articles_scraped'][response.meta['category']] += 1
                self.stats['total_articles'] += 1
                return item
            else:
                self.stats['articles_skipped'][response.meta['category']] += 1
                return None
                
        except Exception as e:
            self.logger.error(f"Error parsing article {response.url}: {e}")
            self.stats['errors'][response.meta['category']] += 1
            return None

    def _extract_article_data(self, response) -> Optional[ArticleItem]:
        item = ArticleItem()
        
        # Basic metadata from request meta
        item["headline"] = response.meta.get("headline", "No headline")
        item["url"] = response.meta["post_url"]
        item["publication_date"] = response.meta["publish_date"]
        item["paper_name"] = "daily-sun"
        item["category"] = response.meta["category"]
        
        # Extract article body with enhanced fallback strategies
        item["article_body"] = self._extract_article_body(response)
        
        return item

    def _extract_article_body(self, response) -> str:
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
            return meta_desc
        
        self.logger.warning(f"Could not extract article body from {response.url}")
        return "No content available"

    def _extract_from_nextjs_script(self, response) -> Optional[str]:
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
                plain_text = re.sub(r'\s+', ' ', plain_text.strip())
                
                return plain_text if len(plain_text) > 50 else None
                
        except (json.JSONDecodeError, IndexError, TypeError) as e:
            self.logger.debug(f"NextJS script extraction failed for {response.url}: {e}")
            
        return None

    def _extract_from_jsonld(self, response) -> Optional[str]:
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

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        
        # Remove HTML entities
        text = html.unescape(text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common unwanted patterns
        text = re.sub(r'\[.*?\]', '', text)  # Remove [bracketed] content
        text = re.sub(r'\(.*?\)', '', text)  # Remove (parenthetical) content if too long
        
        return text.strip()

    def _validate_article(self, item: ArticleItem, category: str) -> bool:
        if not item.get('headline') or not item.get('article_body'):
            return False
        
        if len(item['headline']) < 5 or len(item['article_body']) < 50:
            return False
        
        # Check for placeholder content
        if item['article_body'] in ['No content available', 'No article body']:
            return False
        
        return True

    def handle_error(self, failure):
        request = failure.request
        category = request.meta.get('category', 'unknown')
        
        self.logger.error(f"Request failed for {category}: {failure.value}")
        self.stats['errors'][category] += 1

    def close(self, reason):
        self._should_stop_stats = True
        
        if hasattr(self, '_stats_thread'):
            self._stats_thread.join(timeout=1)
        
        self._log_final_statistics(reason)
        
        if hasattr(self, '_local') and hasattr(self._local, 'connection'):
            try:
                self._local.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing database connection: {e}")

    def _log_final_statistics(self, reason: str) -> None:
        runtime = datetime.now() - self.start_time
        total_articles = sum(self.stats['articles_scraped'].values())
        total_requests = self.stats['total_requests']
        
        self.logger.info(f"=== DailySunSpider Final Statistics ===")
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total Runtime: {runtime}")
        self.logger.info(f"Total Requests: {total_requests}")
        self.logger.info(f"Total Articles Scraped: {total_articles}")
        self.logger.info(f"Total Duplicates Skipped: {self.stats['total_duplicates']}")
        self.logger.info(f"Categories Completed: {self.stats['categories_completed']}/{len(self.categories)}")
        
        if total_requests > 0:
            success_rate = (total_articles / total_requests) * 100
            self.logger.info(f"Overall Success Rate: {success_rate:.1f}%")
        
        if runtime.total_seconds() > 0:
            rate = total_articles / (runtime.total_seconds() / 60)
            self.logger.info(f"Articles per minute: {rate:.1f}")
        
        self.logger.info("=== Per-Category Statistics ===")
        for category in sorted(self.categories):
            scraped = self.stats['articles_scraped'][category]
            skipped = self.stats['articles_skipped'][category]
            errors = self.stats['errors'][category]
            total_cat = scraped + skipped + errors
            
            if total_cat > 0:
                success_rate = (scraped / total_cat) * 100
                self.logger.info(f"{category}: {scraped} scraped, {skipped} skipped, {errors} errors ({success_rate:.1f}% success)")