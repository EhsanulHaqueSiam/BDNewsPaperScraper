import scrapy
import json
import sqlite3
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
import pytz

from BDNewsPaper.items import ArticleItem


class DailyStarSpider(scrapy.Spider):
    name = "thedailystar"
    allowed_domains = ["thedailystar.net"]
    
    DEFAULT_CATEGORIES = {
        "bangladesh": "283517/3758266,3758256,3758241,3758236,3758231,3758226,3758221,3758216,3758211,3758191,3758151,3758146,3758126,3758121,3757891,3758061,3758056,3756996",
        "investigative-stories": "283541/3702396,3623811,3572756,3572761,3572191,3571361,3511731,3507671",
        "sports": "283517/3758266,3758256,3758241,3758236,3758231,3758226,3758221,3758216,3758211,3758191,3758151,3758146,3758126,3758121,3757891,3758061,3758056,3756996",
        "business": "2/3758176,3757931,3757926,3758186,3758166,3758161,3757916,3757911,3757906,3757446,3757306,3757741,3757736,3757896,3757886,3757271,3757261,3757901,3757396,3757341,3757301,3757256,3757251,3756926,3756911,3757726,3757721,3757701,3757676,3756556,3755041,3754296,3754276,3753386,3743596,3503666,3502291,3464146",
        "entertainment": "283449/3758206,3758246,3758196,3757596,3758181,3752971,3729961,3747171,3735641,3530211,3520611,3520606,3493576,3484971,3757551,3757326,3757316,3757291,3756606,3756311,3756306,3755801,3755651,3755721,3757626,3757536,3757201,3756611,3756546,3756521,3756296,3755836,3755606,3755561,3756636,3756626,3755841,3755541",
        "star-multimedia": "17/3755026,3753386,3754176,3755951,3752116,3751151,3748101,3747206,3746566,3745471,3530211,3522621,3520611,3506731,3520606,3493576,3493566,3493561,3474186,3743596,3503666,3502291,3464146,3451826,3444341,3434766,3412636,3411846,3406691,3744751,3742626,3742341,3742286,3636561,3601776,3558866,3551016,3545476,3448351,3443461,3400846,3394701,3392551",
        "environment": "21/3758171,3757746,3757401,3757266,3756566,3756221,3756186,3755846,3753116,3748351,3745556,3745391,3745026,3744691,3744636,3744236,3735681,3733471",
    }

    custom_settings = {
        "CONCURRENT_REQUESTS": 64,
        "DOWNLOAD_DELAY": 0.25,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.1,
        "AUTOTHROTTLE_MAX_DELAY": 3.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 32.0,
        "AUTOTHROTTLE_DEBUG": False,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [404],
        "DUPEFILTER_DEBUG": False,
    }

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.thedailystar.net",
        "referer": "https://www.thedailystar.net",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.start_time = datetime.now()
        self.dhaka_tz = pytz.timezone('Asia/Dhaka')
        
        self._parse_cli_arguments(kwargs)
        self._initialize_configuration()
        self._setup_database()
        self._initialize_statistics()
        
        self.logger.info(f"DailyStarSpider initialized with categories: {list(self.categories.keys())}")
        self.logger.info(f"Date range: {self.start_date} to {self.end_date}")
        self.logger.info(f"Max pages per category: {self.max_pages}")

    def _parse_cli_arguments(self, kwargs: Dict) -> None:
        try:
            self.start_date = datetime.strptime(
                kwargs.get('start_date', '2024-01-01'), '%Y-%m-%d'
            )
            self.end_date = datetime.strptime(
                kwargs.get('end_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'
            )
        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            self.start_date = datetime(2024, 1, 1)
            self.end_date = datetime.now()

        try:
            self.max_pages = int(kwargs.get('max_pages', 100))
            self.max_pages = min(max(self.max_pages, 1), 10000)
        except (ValueError, TypeError):
            self.max_pages = 100

        self.db_path = kwargs.get('db_path', 'news_articles.db')
        
        categories_str = kwargs.get('categories', '')
        if categories_str:
            requested_categories = [cat.strip() for cat in categories_str.split(',')]
            self.categories = {
                cat: self.DEFAULT_CATEGORIES[cat] 
                for cat in requested_categories 
                if cat in self.DEFAULT_CATEGORIES
            }
            if not self.categories:
                self.logger.warning("No valid categories found, using all categories")
                self.categories = self.DEFAULT_CATEGORIES
        else:
            self.categories = self.DEFAULT_CATEGORIES

        enable_stats_value = kwargs.get('enable_stats', 'true')
        self.enable_stats = str(enable_stats_value).lower() == 'true'

    def _initialize_configuration(self) -> None:
        self.start_urls = ["https://www.thedailystar.net/views/ajax"]
        self.stop_scraping = {category: False for category in self.categories}
        self.processed_urls: Set[str] = set()
        self.duplicate_urls: Set[str] = set()
        
        self.pagination_state = {
            category: {'current_page': 0, 'consecutive_empty': 0, 'max_empty': 3}
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
        
        self.logger.info(f"=== DailyStarSpider Statistics (Runtime: {runtime}) ===")
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

    def start_requests(self):
        for category, view_args in self.categories.items():
            for page in range(0, min(self.max_pages, 50)):
                if not self.stop_scraping[category]:
                    payload = {
                        "page": str(page),
                        "view_name": "category_load_more_news",
                        "view_display_id": "panel_pane_1",
                        "view_args": view_args,
                    }
                    
                    self.stats['requests_made'][category] += 1
                    self.stats['total_requests'] += 1
                    
                    yield scrapy.FormRequest(
                        url=self.start_urls[0],
                        formdata=payload,
                        headers=self.headers,
                        callback=self.parse_ajax,
                        meta={
                            "category": category,
                            "page": page,
                            "view_args": view_args,
                            "dont_cache": True
                        },
                        errback=self.handle_error,
                        dont_filter=True
                    )

    def parse_ajax(self, response):
        category = response.meta['category']
        page = response.meta['page']
        view_args = response.meta['view_args']
        
        try:
            if response.status != 200:
                self.logger.warning(f"Non-200 status {response.status} for {category} page {page}")
                self.stats['errors'][category] += 1
                return
            
            if not response.text.strip():
                self.logger.warning(f"Empty response for {category} page {page}")
                self._handle_empty_page(category, page, view_args)
                return
            
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {category} page {page}: {e}")
                self.stats['errors'][category] += 1
                return
            
            if not isinstance(data, list):
                self.logger.warning(f"Unexpected JSON structure for {category} page {page}")
                self.stats['errors'][category] += 1
                return
            
            articles_found = 0
            for item in data:
                if not isinstance(item, dict) or item.get("command") != "insert":
                    continue
                
                html_fragment = item.get("data")
                if not html_fragment:
                    continue
                
                try:
                    selector = scrapy.Selector(text=html_fragment)
                    links = selector.xpath('//a[@href and contains(@href, "/news/")]/@href').getall()
                    
                    for link in links:
                        if not link:
                            continue
                        
                        full_link = response.urljoin(link)
                        if not self._is_valid_url(full_link):
                            continue
                        
                        if not self.is_url_in_db(full_link):
                            articles_found += 1
                            yield scrapy.Request(
                                url=full_link,
                                callback=self.parse_news,
                                meta={
                                    "category": category,
                                    "dont_cache": True
                                },
                                errback=self.handle_error,
                                dont_filter=False
                            )
                        else:
                            self.stats['articles_skipped'][category] += 1
                
                except Exception as e:
                    self.logger.error(f"Error processing HTML fragment for {category}: {e}")
                    continue
            
            if articles_found == 0:
                self._handle_empty_page(category, page, view_args)
            else:
                self.pagination_state[category]['consecutive_empty'] = 0
                self._generate_next_page_request(category, page, view_args)
            
            self.logger.debug(f"{category} page {page}: {articles_found} new articles found")
            
        except Exception as e:
            self.logger.error(f"Unexpected error parsing {category} page {page}: {e}")
            self.stats['errors'][category] += 1

    def _handle_empty_page(self, category: str, page: int, view_args: str) -> None:
        self.pagination_state[category]['consecutive_empty'] += 1
        
        if self.pagination_state[category]['consecutive_empty'] >= self.pagination_state[category]['max_empty']:
            self.logger.info(f"Stopping {category} after {self.pagination_state[category]['consecutive_empty']} consecutive empty pages")
            self.stop_scraping[category] = True
            self.stats['categories_completed'] += 1
        else:
            self._generate_next_page_request(category, page, view_args)

    def _generate_next_page_request(self, category: str, page: int, view_args: str) -> None:
        next_page = page + 1
        if next_page < self.max_pages and not self.stop_scraping[category]:
            payload = {
                "page": str(next_page),
                "view_name": "category_load_more_news",
                "view_display_id": "panel_pane_1",
                "view_args": view_args,
            }
            
            self.stats['requests_made'][category] += 1
            self.stats['total_requests'] += 1
            
            return scrapy.FormRequest(
                url=self.start_urls[0],
                formdata=payload,
                headers=self.headers,
                callback=self.parse_ajax,
                meta={
                    "category": category,
                    "page": next_page,
                    "view_args": view_args,
                    "dont_cache": True
                },
                errback=self.handle_error,
                dont_filter=True
            )

    def _is_valid_url(self, url: str) -> bool:
        return (
            bool(url) and 
            isinstance(url, str) and 
            '/news/' in url and 
            'thedailystar.net' in url and
            not url.endswith('.pdf') and
            not url.endswith('.jpg') and
            not url.endswith('.png')
        )

    def parse_news(self, response):
        if response.status != 200:
            self.logger.warning(f"Non-200 status {response.status} for article: {response.url}")
            self.stats['errors'][response.meta['category']] += 1
            return

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
        
        item['headline'] = self._extract_headline(response)
        item['article_body'] = self._extract_article_body(response)
        item['publication_date'] = self._extract_publication_date(response)
        item['url'] = response.url
        item['paper_name'] = "thedailystar"
        item['category'] = response.meta['category']
        
        return item

    def _extract_headline(self, response) -> Optional[str]:
        selectors = [
            "//h1/text()",
            "//h1//text()",
            "//title/text()",
            "//meta[@property='og:title']/@content"
        ]
        
        for selector in selectors:
            headline = response.xpath(selector).get()
            if headline and headline.strip():
                headline = headline.strip()
                if ' - The Daily Star' in headline:
                    headline = headline.replace(' - The Daily Star', '')
                return headline
        
        return None

    def _extract_article_body(self, response) -> Optional[str]:
        body_selectors = [
            "//div[@class='pb-20 clearfix']//p/text()",
            "//div[contains(@class, 'article-content')]//p/text()",
            "//div[contains(@class, 'story-content')]//p/text()",
            "//div[contains(@class, 'news-content')]//p/text()"
        ]
        
        for selector in body_selectors:
            paragraphs = response.xpath(selector).getall()
            if paragraphs:
                body = " ".join(p.strip() for p in paragraphs if p.strip())
                if len(body) > 50:
                    return body
        
        return None

    def _extract_publication_date(self, response) -> Optional[str]:
        date_selectors = [
            "//div[contains(@class, 'date')]/text()[1]",
            "//span[contains(@class, 'date')]/text()",
            "//time/@datetime",
            "//meta[@property='article:published_time']/@content"
        ]
        
        for selector in date_selectors:
            date_text = response.xpath(selector).get()
            if date_text and date_text.strip():
                return date_text.strip()
        
        return None

    def _validate_article(self, item: ArticleItem, category: str) -> bool:
        if not item.get('headline') or not item.get('article_body'):
            return False
        
        if len(item['headline']) < 10 or len(item['article_body']) < 100:
            return False
        
        if item.get('publication_date'):
            try:
                pub_date = self._parse_publication_date(item['publication_date'])
                if pub_date:
                    if pub_date < self.start_date or pub_date > self.end_date + timedelta(days=1):
                        return False
                    
                    if pub_date < self.start_date:
                        self.logger.info(f"Stopping {category} - reached start date limit")
                        self.stop_scraping[category] = True
                        return False
            except Exception as e:
                self.logger.debug(f"Date validation error: {e}")
        
        return True

    def _parse_publication_date(self, date_str: str) -> Optional[datetime]:
        date_formats = [
            "%a %b %d, %Y %I:%M %p",
            "%B %d, %Y %I:%M %p",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

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
        
        self.logger.info(f"=== DailyStarSpider Final Statistics ===")
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
        for category in sorted(self.categories.keys()):
            scraped = self.stats['articles_scraped'][category]
            skipped = self.stats['articles_skipped'][category]
            errors = self.stats['errors'][category]
            total_cat = scraped + skipped + errors
            
            if total_cat > 0:
                success_rate = (scraped / total_cat) * 100
                self.logger.info(f"{category}: {scraped} scraped, {skipped} skipped, {errors} errors ({success_rate:.1f}% success)")