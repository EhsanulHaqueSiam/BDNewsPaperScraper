"""
Daily Ittefaq Spider
====================
Scrapes English news articles from Daily Ittefaq using their AJAX API.

Features:
    - AJAX API for article listing
    - Category-based scraping
    - Keyword search support
    - Client-side date validation
"""

import json
from datetime import datetime
from typing import Generator, Optional
from urllib.parse import quote

import scrapy
from scrapy.http import JsonRequest, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class IttefaqSpider(BaseNewsSpider):
    """
    Daily Ittefaq English edition scraper using AJAX API.
    
    Note: Date filtering is performed client-side as the API 
    doesn't support date range filtering.
    
    Usage:
        scrapy crawl ittefaq -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl ittefaq -a categories=Bangladesh,Sports
        scrapy crawl ittefaq -a search_query="politics"
    """
    
    name = "ittefaq"
    paper_name = "The Daily Ittefaq"
    allowed_domains = ["ittefaq.com.bd", "en.ittefaq.com.bd"]
    
    # API capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    supports_keyword_search = True
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }
    
    BASE_URL = "https://en.ittefaq.com.bd"
    BASE_API_URL = "https://en.ittefaq.com.bd/api/theme_engine/get_ajax_contents"
    SEARCH_URL = "https://en.ittefaq.com.bd/search"
    ARTICLES_PER_PAGE = 250
    MAX_ARTICLES = 5000
    
    # Category mappings (widget_id, page_id for API)
    # Discovered from website structure
    CATEGORIES = {
        "Bangladesh": {"widget": 28, "page_id": 1098, "path": "bangladesh"},
        "International": {"widget": 29, "page_id": 1099, "path": "international"},
        "Sports": {"widget": 30, "page_id": 1100, "path": "sports"},
        "Business": {"widget": 31, "page_id": 1101, "path": "business"},
        "Entertainment": {"widget": 32, "page_id": 1102, "path": "entertainment"},
        "Opinion": {"widget": 33, "page_id": 1103, "path": "opinion"},
    }
    
    DEFAULT_CATEGORIES = ["Bangladesh"]
    
    API_HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_start = {}
        
        # Search query support
        self.search_query = kwargs.get('search_query', '')
        
        # Setup categories
        self._setup_categories()
        
        self.logger.info(f"Categories: {list(self.category_map.keys())}")
        if self.search_query:
            self.logger.info(f"Search query: {self.search_query}")
    
    def _setup_categories(self) -> None:
        """Setup category mappings based on filter."""
        if self.categories:
            self.category_map = {}
            for cat in self.categories:
                for key, value in self.CATEGORIES.items():
                    if key.lower() == cat.lower():
                        self.category_map[key] = value
                        break
            
            if not self.category_map:
                self.logger.warning("No valid categories found, using Bangladesh only")
                self.category_map = {"Bangladesh": self.CATEGORIES["Bangladesh"]}
        else:
            self.category_map = {
                cat: self.CATEGORIES[cat] 
                for cat in self.DEFAULT_CATEGORIES
            }
    
    def _get_api_url(self, widget: int, page_id: int, start: int, count: int) -> str:
        """Build API URL with category support."""
        return (
            f"{self.BASE_API_URL}?widget={widget}&start={start}&count={count}"
            f"&page_id={page_id}&subpage_id=0&author=0&tags=&archive_time=&filter="
        )
    
    # ================================================================
    # Request Generation
    # ================================================================
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial requests for all categories or search."""
        if self.should_stop:
            return
        
        if self.search_query:
            # Search mode
            yield self._make_search_request()
        else:
            # Category-based scraping
            for category, info in self.category_map.items():
                self.current_start[category] = 0
                yield self._make_category_request(category, info, start=0)
    
    def _make_category_request(self, category: str, info: dict, start: int) -> JsonRequest:
        """Create API request for a category."""
        widget = info["widget"]
        page_id = info["page_id"]
        path = info["path"]
        
        api_url = self._get_api_url(widget, page_id, start, self.ARTICLES_PER_PAGE)
        self.stats['requests_made'] += 1
        
        headers = self.API_HEADERS.copy()
        headers["Referer"] = f"{self.BASE_URL}/{path}"
        
        return JsonRequest(
            api_url,
            headers=headers,
            callback=self.parse_api,
            errback=self.handle_request_failure,
            meta={
                'category': category,
                'category_info': info,
                'current_start': start,
            },
        )
    
    def _make_search_request(self) -> scrapy.Request:
        """Create search request."""
        search_url = f"{self.SEARCH_URL}?q={quote(self.search_query)}"
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            search_url,
            callback=self.parse_search_results,
            errback=self.handle_request_failure,
            meta={'category': f'search:{self.search_query}'},
        )
    
    # ================================================================
    # Search Results Parsing
    # ================================================================
    
    def parse_search_results(self, response: Response) -> Generator:
        """Parse search results page."""
        articles = response.css('.media, .search-result, article, .news-item')
        
        self.logger.info(f"Search results: Found {len(articles)} articles")
        
        for article in articles:
            link = article.css('a::attr(href)').get()
            if not link:
                continue
            
            full_url = response.urljoin(link)
            
            if full_url in self.processed_urls:
                continue
            
            if self.is_url_in_db(full_url):
                continue
            
            self.processed_urls.add(full_url)
            self.stats['articles_found'] += 1
            
            yield scrapy.Request(
                full_url,
                callback=self.parse_article,
                errback=self.handle_request_failure,
                meta={
                    'url': full_url,
                    'category': 'Search',
                },
            )
    
    # ================================================================
    # API Response Parsing
    # ================================================================
    
    def parse_api(self, response: Response) -> Generator:
        """Parse API response and extract article links."""
        if self.should_stop:
            return
        
        category = response.meta.get('category', 'Unknown')
        category_info = response.meta.get('category_info', {})
        current_start = response.meta.get('current_start', 0)
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.stats['errors'] += 1
            return
        
        html_content = data.get("html", "")
        if not html_content:
            return
        
        selector = scrapy.Selector(text=html_content)
        links = selector.xpath("//h2[@class='title']//a[@class='link_overlay']/@href").getall()
        
        self.logger.info(f"Category '{category}' offset {current_start}: Found {len(links)} articles")
        
        if not links:
            return
        
        valid_links = 0
        for link in links:
            if self.should_stop:
                break
            
            full_url = response.urljoin(link)
            
            if full_url in self.processed_urls:
                continue
            
            if self.is_url_in_db(full_url):
                continue
            
            self.processed_urls.add(full_url)
            valid_links += 1
            self.stats['articles_found'] += 1
            
            yield scrapy.Request(
                full_url,
                callback=self.parse_article,
                errback=self.handle_request_failure,
                meta={
                    'url': full_url,
                    'category': category,
                },
            )
        
        # Pagination
        next_start = current_start + self.ARTICLES_PER_PAGE
        
        if not self.should_stop and next_start < self.MAX_ARTICLES and valid_links > 0:
            self.current_start[category] = next_start
            yield self._make_category_request(category, category_info, next_start)
    
    # ================================================================
    # Article Parsing
    # ================================================================
    
    def parse_article(self, response: Response) -> Optional[NewsArticleItem]:
        """Parse article page."""
        if self.should_stop:
            return None
        
        url = response.meta.get('url', response.url)
        
        # Extract publication date
        pub_date_str = response.xpath(
            "//span[@class='tts_time' and @itemprop='datePublished']/@content"
        ).get()
        
        pub_date = "Unknown"
        if pub_date_str:
            try:
                article_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                
                if article_date.tzinfo is None:
                    article_date = self.dhaka_tz.localize(article_date)
                else:
                    article_date = article_date.astimezone(self.dhaka_tz)
                
                # Date validation
                if self.is_before_start_date(article_date):
                    self.should_stop = True
                    self.stats['date_filtered'] += 1
                    return None
                
                if article_date > self.end_date:
                    self.stats['date_filtered'] += 1
                    return None
                
                pub_date = article_date.strftime("%Y-%m-%d %H:%M:%S")
                
            except (ValueError, TypeError) as e:
                self.logger.debug(f"Date parse error: {e}")
        
        # Extract category - prefer from meta (request), fallback to page
        category = response.meta.get('category')
        if not category or category == 'Unknown':
            page_category = response.xpath("//h2[@class='secondary_logo']//span/text()").get()
            category = page_category.strip() if page_category else "Unknown"
        
        # Extract headline
        headline = response.xpath("//h1/text()").get()
        headline = headline.strip() if headline else "Unknown"
        
        # Extract subtitle
        sub_title = response.xpath("//h2[@class='subtitle mb10']/text()").get()
        sub_title = sub_title.strip() if sub_title else None
        
        # Extract article body
        paragraphs = response.xpath(
            "//article[@class='jw_detail_content_holder content mb16']"
            "//div[@itemprop='articleBody']//p/text()"
        ).getall()
        
        if not paragraphs:
            paragraphs = response.xpath(
                "//div[@itemprop='articleBody']//text()[normalize-space()]"
            ).getall()
        
        article_body = " ".join(t.strip() for t in paragraphs if t.strip())
        
        if not article_body or len(article_body) < 50:
            self.stats['errors'] += 1
            return None
        
        self.stats['articles_processed'] += 1
        
        return self.create_article_item(
            headline=headline,
            sub_title=sub_title,
            article_body=article_body,
            url=url,
            publication_date=pub_date,
            category=category,
        )
