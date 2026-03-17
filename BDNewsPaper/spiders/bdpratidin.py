"""
BD Pratidin Spider
==================
Scrapes English news articles from BD Pratidin using HTML pagination.

Features:
    - HTML-based pagination (no API available)
    - Date extraction from URL
    - Category-based scraping
"""

import re
from datetime import datetime
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector
from w3lib.html import remove_tags
from html import unescape


class BDPratidinSpider(BaseNewsSpider):
    """
    BD Pratidin English edition scraper using HTML pagination.
    
    Note: This spider uses HTML scraping as no API is available.
    Date filtering is done by extracting dates from article URLs.
    
    Usage:
        scrapy crawl BDpratidin -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl BDpratidin -a categories=national,sports
    """
    
    name = "BDpratidin"
    paper_name = "BD Pratidin"
    allowed_domains = ["en.bd-pratidin.com"]
    
    # API capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True  # Supports category filtering via URL
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }
    
    # Default categories
    DEFAULT_CATEGORIES = [
        "national", "international", "sports", "showbiz", "economy", "shuvosangho",
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        
        # Setup categories
        self._setup_categories()
        
        self.logger.info(f"Categories: {self.selected_categories}")
    
    def _setup_categories(self) -> None:
        """Setup categories based on filter - accepts any category slug."""
        if self.categories:
            # Accept any category provided by user
            self.selected_categories = [cat.lower().strip() for cat in self.categories]
            self.logger.info(f"Using user-provided categories: {self.selected_categories}")
        else:
            self.selected_categories = self.DEFAULT_CATEGORIES.copy()
    
    # ================================================================
    # Request Generation
    # ================================================================
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.bd-pratidin.com/rss.xml',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

        # Supplementary: News sitemap for date-filtered discovery
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.bd-pratidin.com/sitemap.xml',
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

    def _generate_fallback_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate fallback category requests."""
        if self.should_stop:
            return
        
        for category in self.selected_categories:
            url = f"https://en.bd-pratidin.com/{category}?page=1"
            self.stats['requests_made'] += 1
            
            yield scrapy.Request(
                url,
                callback=self.parse_category,
                errback=self.handle_request_failure,
                meta={"category": category, "page_number": 1},
            )
    
    # ================================================================
    # Category Page Parsing
    # ================================================================
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page and extract article links."""
        if self.should_stop:
            return
        
        category = response.meta["category"]
        page_number = response.meta["page_number"]
        
        # Extract article links
        news_links = response.xpath(
            "//div[@class='col-12']//a[@class='stretched-link']/@href"
        ).getall()
        
        if not news_links:
            self.logger.info(f"No links on page {page_number} for {category}")
            return
        
        valid_links = 0
        for link in news_links:
            if self.should_stop:
                break
            
            full_url = response.urljoin(link)
            
            if full_url in self.processed_urls:
                continue
            
            if self.is_url_in_db(full_url):
                continue
            
            # Extract and validate date from URL
            date_obj = self._extract_date_from_url(full_url)
            
            if date_obj:
                if self.is_before_start_date(date_obj):
                    self.logger.info(f"Stopping {category}: reached start date")
                    self.should_stop = True
                    return
                
                if date_obj > self.end_date:
                    self.stats['date_filtered'] += 1
                    continue
            
            self.processed_urls.add(full_url)
            valid_links += 1
            self.stats['articles_found'] += 1
            
            yield scrapy.Request(
                full_url,
                callback=self.parse_article,
                errback=self.handle_request_failure,
                meta={
                    "category": category,
                    "date": date_obj.strftime("%Y-%m-%d %H:%M:%S") if date_obj else "Unknown",
                },
            )
        
        # Pagination
        if not self.should_stop and valid_links > 0 and page_number < self.max_pages:
            next_url = f"https://en.bd-pratidin.com/{category}?page={page_number + 1}"
            self.stats['requests_made'] += 1
            
            yield scrapy.Request(
                next_url,
                callback=self.parse_category,
                errback=self.handle_request_failure,
                meta={"category": category, "page_number": page_number + 1},
            )
    
    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Extract date from article URL."""
        try:
            match = re.search(r"/(\d{4}/\d{2}/\d{2})/", url)
            if match:
                date_str = match.group(1)  # e.g., '2024/12/14'
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
                return self.dhaka_tz.localize(date_obj)
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Date extraction error for {url}: {e}")
        
        return None
    
    # ================================================================
    # Article Parsing
    # ================================================================
    

    # ================================================================
    # RSS Feed Parsing (Primary Source)
    # ================================================================

    def parse_rss(self, response):
        """Parse RSS feed XML to extract articles."""
        sel = Selector(response)
        sel.remove_namespaces()
        items = sel.xpath('//item')

        self.logger.info(f"RSS feed: Found {len(items)} items")

        rss_yielded = 0

        for item in items:
            headline = item.xpath('title/text()').get('').strip()
            url = item.xpath('link/text()').get('').strip()
            pub_date_str = item.xpath('pubDate/text()').get('').strip()
            author = item.xpath('creator/text()').get('').strip()
            body_html = item.xpath('encoded/text()').get('')
            description = item.xpath('description/text()').get('').strip()
            category = item.xpath('category/text()').get('General').strip()

            if not url:
                continue

            self._rss_urls_seen.add(url)

            if self.is_url_in_db(url):
                continue

            # Clean HTML from body
            body = ''
            if body_html:
                body = remove_tags(body_html).strip()

            # Date filtering
            if pub_date_str:
                parsed_date = self._parse_date_string(pub_date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Search query filter
            if headline and body:
                if not self.filter_by_search_query(headline, body):
                    continue

            if headline and body and len(body) > 100:
                # Full article available from RSS
                self.stats['articles_found'] += 1
                self.stats['articles_processed'] += 1
                rss_yielded += 1

                yield self.create_article_item(
                    url=url,
                    headline=unescape(headline),
                    article_body=body,
                    publication_date=pub_date_str if pub_date_str else None,
                    author=author if author else None,
                    category=category,
                )
            elif headline and url:
                # RSS item lacks full body -- visit article page
                self.stats['articles_found'] += 1
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_article,
                    meta={'category': category},
                    errback=self.handle_request_failure,
                )

        self.logger.info(f"RSS feed: Yielded {rss_yielded} complete articles directly")

        # If RSS returned few items, also launch category fallback
        if len(items) < 5:
            self.logger.info("RSS returned few items, launching category fallback")
            yield from self._generate_fallback_requests()

    def _rss_failed(self, failure):
        """If RSS fails, fall back to existing scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to category scraping.")
        self.stats['errors'] += 1
        yield from self._generate_fallback_requests()


    # ================================================================
    # Sitemap Parsing (Supplementary Source)
    # ================================================================

    def parse_sitemap(self, response):
        """Parse news sitemap XML for date-filtered article discovery."""
        sel = Selector(response)
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            lastmod = url_node.xpath('lastmod/text()').get('').strip()
            pub_date = url_node.xpath('news/publication_date/text()').get('').strip()

            if not loc:
                continue

            # Skip if already seen via RSS
            if hasattr(self, '_rss_urls_seen') and loc in self._rss_urls_seen:
                continue

            if self.is_url_in_db(loc):
                continue

            # Date filter on lastmod or pub_date
            date_str = pub_date or lastmod
            if date_str:
                parsed_date = self._parse_date_string(date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            sitemap_count += 1

            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={'category': 'General'},
                errback=self.handle_request_failure,
            )

        self.logger.info(f"Sitemap: Queued {sitemap_count} articles for scraping")

    def parse_article(self, response: Response) -> Optional[NewsArticleItem]:
        """Parse article page."""
        if self.should_stop:
            return None
        
        # Extract headline
        headline = response.xpath("//h1/text()").get()
        headline = headline.strip() if headline else "Unknown"
        
        # Extract subtitle
        sub_title = response.xpath(
            "//h2[contains(@class, 'subtitle')]/text() | "
            "//p[@class='lead']/text()"
        ).get()
        sub_title = sub_title.strip() if sub_title else None
        
        # Extract article body
        paragraphs = response.xpath(
            "//div[@class='col-12']//div[@class='mt-3']//article//p/text()"
        ).getall()
        
        if not paragraphs:
            paragraphs = response.xpath("//article//p/text()").getall()
        
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
            url=response.url,
            publication_date=response.meta.get("date", "Unknown"),
            category=response.meta.get("category", "Unknown"),
        )
