"""
Barta24 Spider (Bangla) - API-Based
====================================
Scrapes articles from Barta24 (barta24.com) - Popular Bangla News Portal

Features:
    - API-based scraping (backoffice.barta24.com)
    - Direct JSON data extraction
    - No JavaScript rendering needed
    - Category filtering support
"""

import json
import re
from html import unescape
from typing import Generator

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector
from w3lib.html import remove_tags


class Barta24Spider(BaseNewsSpider):
    """
    Spider for Barta24 (Popular Bangla News Portal).
    
    Uses Barta24's API for efficient JSON-based scraping.
    
    API Endpoints:
        - Latest articles: backoffice.barta24.com/api/home-json-bn/generateLatest.json
        - Article details: backoffice.barta24.com/api/content-details/{id}
    
    Usage:
        scrapy crawl barta24
        scrapy crawl barta24 -a max_pages=10
    """
    
    name = 'barta24'
    paper_name = 'Barta24'
    allowed_domains = ['barta24.com', 'backoffice.barta24.com']
    language = 'Bangla'
    
    # API endpoints
    API_BASE = 'https://backoffice.barta24.com/api'
    LATEST_API = f'{API_BASE}/home-json-bn/generateLatest.json'
    CDN_BASE = 'https://cdn.barta24.com'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = False  # API returns mixed categories
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json',
            'Accept-Language': 'bn,en;q=0.9',
        },
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        self.logger.info(f"Barta24 spider initialized (API mode)")
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.barta24.com/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

        # Supplementary: News sitemap for date-filtered discovery
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.barta24.com/news-sitemap.xml',
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

    def _generate_fallback_requests(self) -> Generator[Request, None, None]:
        """Generate initial request to latest articles API."""
        
        self.logger.info(f"Fetching latest articles from API: {self.LATEST_API}")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=self.LATEST_API,
            callback=self.parse_latest_api,
            errback=self.handle_request_failure,
        )
    
    def parse_latest_api(self, response: Response) -> Generator:
        """Parse latest articles JSON API response."""
        try:
            articles = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return
        
        if not isinstance(articles, list):
            self.logger.error("Expected list of articles from API")
            return
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not articles:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
            articles = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(articles)} articles from API")
        
        for article in articles:
            content_id = article.get('ContentID')
            if not content_id:
                continue
            
            # Build article URL for deduplication check
            article_url = f"https://barta24.com/details/{article.get('categorySlug', 'news')}/{content_id}"
            
            if self.is_url_in_db(article_url):
                continue
            
            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            
            # Request full article details
            details_url = f"{self.API_BASE}/content-details/{content_id}"
            
            yield Request(
                url=details_url,
                callback=self.parse_article_api,
                meta={
                    'article_url': article_url,
                    'category': article.get('categorySlug', ''),
                    'preview_headline': article.get('DetailsHeading', ''),
                },
                errback=self.handle_request_failure,
            )
    

    def parse_article(self, response):
        """Parse individual article page (fallback for RSS/sitemap items without full body)."""
        item = self.parse_article_auto(response)
        if item:
            item['category'] = response.meta.get('category', 'General')
            self.stats['articles_processed'] += 1
            yield item

    def parse_article_api(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse article details from API."""
        article_url = response.meta.get('article_url', response.url)
        category = response.meta.get('category', 'General')
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse article JSON: {e}")
            return
        
        # API returns {"data": [article_data, related...]}
        if not isinstance(data, dict) or 'data' not in data:
            self.logger.warning(f"Unexpected API response format")
            return
        
        articles_data = data.get('data', [])
        if not articles_data:
            return
        
        article = articles_data[0]  # First item is the main article
        
        # Extract headline
        headline = article.get('DetailsHeading', '') or response.meta.get('preview_headline', '')
        if not headline:
            self.logger.warning(f"No headline for article")
            return
        
        headline = unescape(headline.strip())
        
        # Extract article body from ContentDetails (array of HTML paragraphs)
        content_details = article.get('ContentDetails', [])
        if isinstance(content_details, list):
            body_parts = []
            for part in content_details:
                if isinstance(part, str):
                    cleaned = self._clean_html(part)
                    if cleaned:
                        body_parts.append(cleaned)
            article_body = '\n\n'.join(body_parts)
        else:
            article_body = ''
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {article_url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date
        pub_date = None
        date_str = article.get('created_at', '')
        if date_str:
            pub_date = self._parse_date_string(date_str)
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Extract author
        author = article.get('WriterName', '')
        
        # Extract category (use API category name if available)
        category = article.get('CategoryName', '') or article.get('CategorySlug', '') or category
        
        # Extract image
        image_path = article.get('ImageBgPath', '') or article.get('ImageSmPath', '')
        image_url = f"{self.CDN_BASE}/{image_path}" if image_path else None
        
        # Extract keywords
        keywords = article.get('Keywords', '')
        
        self.stats['articles_processed'] += 1
        
        yield self.create_article_item(
            url=article_url,
            headline=headline,
            article_body=article_body,
            publication_date=pub_date.isoformat() if pub_date else None,
            category=category,
            author=author if author else None,
            image_url=image_url,
            keywords=keywords if keywords else None,
        )
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML content to extract text."""
        if not html:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        text = unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

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

