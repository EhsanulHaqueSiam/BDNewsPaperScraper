"""
The Bangladesh Today Spider
===========================
Scrapes news articles from The Bangladesh Today using HTML pagination.

Features:
    - HTML-based pagination (no API available)
    - Bengali date parsing support
    - Category-based scraping
"""

from datetime import datetime
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.bengalidate_to_englishdate import convert_bengali_date_to_english
from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class BangladeshTodaySpider(BaseNewsSpider):
    """
    The Bangladesh Today news scraper using HTML pagination.
    
    Note: This spider uses HTML scraping as no API is available.
    Dates are in Bengali and converted using the bengalidate module.
    
    Usage:
        scrapy crawl bangladesh_today -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl bangladesh_today -a categories=1,93,97
    """
    
    name = "bangladesh_today"
    paper_name = "The Bangladesh Today"
    allowed_domains = ["thebangladeshtoday.com"]
    
    # API capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True  # Supports category filtering via category ID
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }
    
    # Category mappings (ID to name)
    CATEGORY_MAP = {
        1: "Bangladesh",
        93: "Nationwide", 
        94: "Entertainment",
        97: "International",
        95: "Sports",
        96: "Feature",
    }
    
    # Default categories to scrape
    DEFAULT_CATEGORY_IDS = [1, 93, 97]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup categories
        self._setup_categories()
        
        self.logger.info(f"Categories: {self.selected_category_ids}")
    
    def _setup_categories(self) -> None:
        """Setup categories based on filter - accepts any category ID or name."""
        if self.categories:
            category_ids = []
            for cat in self.categories:
                if cat.isdigit():
                    # Accept any numeric category ID
                    category_ids.append(int(cat))
                else:
                    # Try to find by name, or use the string as-is for URL
                    found = False
                    for cid, cname in self.CATEGORY_MAP.items():
                        if cname.lower() == cat.lower():
                            category_ids.append(cid)
                            found = True
                            break
                    if not found:
                        self.logger.info(f"Category '{cat}' not in map, will try as URL slug")
            
            if category_ids:
                self.selected_category_ids = category_ids
                self.logger.info(f"Using user-provided categories: {self.selected_category_ids}")
            else:
                self.selected_category_ids = self.DEFAULT_CATEGORY_IDS.copy()
        else:
            self.selected_category_ids = self.DEFAULT_CATEGORY_IDS.copy()
    
    # ================================================================
    # Request Generation
    # ================================================================
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests for all categories."""
        if self.should_stop:
            return
        
        for cat_id in self.selected_category_ids:
            url = f"https://thebangladeshtoday.com/?cat={cat_id}&paged=1"
            self.stats['requests_made'] += 1
            
            yield Request(
                url,
                callback=self.parse_category,
                errback=self.handle_request_failure,
                meta={
                    'category_id': cat_id,
                    'page_no': 1,
                    'category_name': self.CATEGORY_MAP.get(cat_id, "Unknown"),
                },
            )
    
    # ================================================================
    # Category Page Parsing
    # ================================================================
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page and extract article links."""
        if self.should_stop:
            return
        
        cat_id = response.meta['category_id']
        page_no = response.meta['page_no']
        cat_name = response.meta['category_name']
        
        # Extract article links
        article_links = response.xpath("//a[@class='ct-link']/@href").getall()
        
        if not article_links:
            self.logger.info(f"No articles on page {page_no} for {cat_name}")
            return
        
        valid_articles = 0
        for link in article_links:
            if self.should_stop:
                break
            
            full_url = response.urljoin(link)
            
            if full_url in self.processed_urls:
                continue
            
            if self.is_url_in_db(full_url):
                continue
            
            self.processed_urls.add(full_url)
            valid_articles += 1
            self.stats['articles_found'] += 1
            
            yield Request(
                full_url,
                callback=self.parse_article,
                errback=self.handle_request_failure,
                meta={
                    'category_id': cat_id,
                    'category_name': cat_name,
                    'url': full_url,
                },
            )
        
        # Pagination
        if not self.should_stop and valid_articles > 0 and page_no < self.max_pages:
            next_url = f"https://thebangladeshtoday.com/?cat={cat_id}&paged={page_no + 1}"
            self.stats['requests_made'] += 1
            
            yield Request(
                next_url,
                callback=self.parse_category,
                errback=self.handle_request_failure,
                meta={
                    'category_id': cat_id,
                    'page_no': page_no + 1,
                    'category_name': cat_name,
                },
            )
    
    # ================================================================
    # Article Parsing
    # ================================================================
    
    def parse_article(self, response: Response) -> Optional[NewsArticleItem]:
        """Parse article page."""
        if self.should_stop:
            return None
        
        url = response.meta.get('url', response.url)
        cat_name = response.meta.get('category_name', "Unknown")
        
        # Extract publication date (Bengali)
        pub_date_str = response.xpath(
            "/html/body/section[3]/div/div[1]/div/div[2]/span/text()"
        ).get()
        
        pub_date = "Unknown"
        if pub_date_str:
            try:
                article_date = convert_bengali_date_to_english(pub_date_str.strip())
                
                if article_date:
                    if article_date.tzinfo is None:
                        article_date = self.dhaka_tz.localize(article_date)
                    
                    # Date validation
                    if self.is_before_start_date(article_date):
                        self.should_stop = True
                        self.stats['date_filtered'] += 1
                        return None
                    
                    if article_date > self.end_date:
                        self.stats['date_filtered'] += 1
                        return None
                    
                    pub_date = article_date.strftime('%Y-%m-%d %H:%M:%S')
                    
            except Exception as e:
                self.logger.debug(f"Bengali date conversion error: {e}")
        
        # Extract headline
        headline = response.xpath(
            "//h1[@class='ct-headline']/span[@class='ct-span']/text()"
        ).get()
        headline = headline.strip() if headline else "Unknown"
        
        # Extract subtitle
        sub_title = response.xpath(
            "//h2[contains(@class, 'subtitle')]/text() | "
            "//div[@class='ct-subtitle']//text()"
        ).get()
        sub_title = sub_title.strip() if sub_title else None
        
        # Extract article body
        paragraphs = response.xpath(
            "//span[@class='ct-span oxy-stock-content-styles']/p/text()"
        ).getall()
        
        if not paragraphs:
            paragraphs = response.xpath(
                "//div[contains(@class, 'content')]//p/text() | "
                "//div[contains(@class, 'article')]//p/text()"
            ).getall()
        
        if not paragraphs:
            paragraphs = response.xpath("//p/text()[normalize-space()]").getall()
        
        article_body = " ".join(p.strip() for p in paragraphs if p.strip())
        
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
            category=cat_name,
        )
