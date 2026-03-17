"""
bdnews24 Bangla Spider
======================
Scrapes articles from bdnews24 Bangla (bangla.bdnews24.com)

Features:
    - Category-based scraping
    - Date filtering (client-side)
    - Search query filtering
"""

from html import unescape
from typing import Generator

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector


class BdNews24BanglaSpider(BaseNewsSpider):
    """
    Spider for bdnews24 Bangla edition.
    
    Uses HTML scraping with category navigation.
    
    Usage:
        scrapy crawl bdnews24_bangla -a categories=bangladesh,politics,sports
        scrapy crawl bdnews24_bangla -a max_pages=10
        scrapy crawl bdnews24_bangla -a start_date=2024-01-01
    """
    
    name = 'bdnews24_bangla'
    paper_name = 'bdnews24 Bangla'
    allowed_domains = ['bangla.bdnews24.com']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category slug mappings
    CATEGORIES = {
        'bangladesh': 'bangladesh',
        'national': 'bangladesh',
        'politics': 'politics',
        'international': 'world',
        'world': 'world',
        'sports': 'sport',
        'sport': 'sport',
        'entertainment': 'entertainment',
        'business': 'economy',
        'economy': 'economy',
        'tech': 'tech',
        'technology': 'tech',
        'lifestyle': 'lifestyle',
        'health': 'health',
        'education': 'education',
        'opinion': 'opinion',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"bdnews24 Bangla spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Supplementary: News sitemap for date-filtered discovery
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.bdnews24.com/sitemap.xml',
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

        # Fallback: Category-based scraping
        yield from self._generate_fallback_requests()

    def _generate_fallback_requests(self) -> Generator[Request, None, None]:
        """Generate fallback category requests."""
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                url = f"https://bangla.bdnews24.com/{cat_slug}"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            default_cats = ['bangladesh', 'politics', 'sport', 'economy']
            for cat in default_cats:
                url = f"https://bangla.bdnews24.com/{cat}"
                
                self.logger.info(f"Crawling category: {cat} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_slug': cat, 'page': 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)
        
        # Find article links - bdnews24 uses unique hash IDs in URLs
        article_links = response.css('a::attr(href)').getall()
        article_links = [l for l in article_links if 'bangla.bdnews24.com/' in l and len(l.split('/')[-1]) > 8]
        
        # Deduplicate
        article_links = list(set(article_links))
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not article_links:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
            article_links = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            return
        
        found_count = 0
        
        for url in article_links:
            if self.is_url_in_db(url):
                continue
            
            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            found_count += 1
            
            yield Request(
                url=url,
                callback=self.parse_article,
                meta={'category': category},
                errback=self.handle_request_failure,
            )
        
        # Pagination
        if found_count > 0 and page < self.max_pages:
            next_link = response.css('a.next::attr(href), a[rel="next"]::attr(href)').get()
            if next_link:
                self.stats['requests_made'] += 1
                yield Request(
                    url=next_link,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': page + 1},
                    errback=self.handle_request_failure,
                )
    

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

    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        headline = (
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        body_parts = response.css('article p::text, .article-content p::text, .content p::text').getall()
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        if not self.filter_by_search_query(headline, article_body):
            return
        
        pub_date = None
        date_text = response.css('meta[property="article:published_time"]::attr(content)').get()
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        author = self.extract_author(response)
        category = response.meta.get('category', 'General')
        image_url = response.css('meta[property="og:image"]::attr(content)').get()
        
        self.stats['articles_processed'] += 1
        
        yield self.create_article_item(
            url=url,
            headline=headline,
            article_body=article_body,
            publication_date=pub_date.isoformat() if pub_date else None,
            category=category,
            author=author,
            image_url=image_url,
        )
