"""
Dainik Amader Shomoy Spider (Bangla)
====================================
Scrapes articles from Amader Shomoy (amadershomoy.com)

Features:
    - Sitemap as primary source (302 article URLs)
    - Category-based scraping as fallback
    - Date filtering (client-side)
    - Bangla newspaper
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator

import scrapy
from scrapy.http import Request, Response
from scrapy.selector import Selector

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class DainikAmaderShomoySpider(BaseNewsSpider):
    """
    Spider for Amader Shomoy (Bangla Daily).

    Uses sitemap as primary source, HTML scraping as fallback.
    URL pattern: www.amadershomoy.com/{category}/article/{ID}/{slug}

    Usage:
        scrapy crawl amadershomoy -a categories=national,politics
        scrapy crawl amadershomoy -a max_pages=10
    """

    name = 'amadershomoy'
    paper_name = 'Amader Shomoy'
    allowed_domains = ['amadershomoy.com', 'www.amadershomoy.com']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'economy': 'economy',
        'business': 'economy',
        'opinion': 'opinion',
        'country': 'country',
        'religion': 'religion',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sitemap_urls_seen = set()
        self.logger.info("Amader Shomoy spider initialized")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: Sitemap (302 article URLs)
        sitemap_url = "https://amadershomoy.com/sitemap.xml"
        self.logger.info(f"Fetching sitemap: {sitemap_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=sitemap_url,
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self._sitemap_failed,
            meta={'source': 'sitemap'},
        )

    def _sitemap_failed(self, failure):
        """If sitemap fails, fall back to category-based HTML scraping."""
        self.logger.warning(f"Sitemap failed: {failure.value}. Falling back to category scraping.")
        self.stats['errors'] += 1
        yield from self._generate_category_requests()

    def _generate_category_requests(self) -> Generator[Request, None, None]:
        """Generate requests for category pages (fallback mode)."""
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                url = f"https://www.amadershomoy.com/{cat_slug}/"

                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1

                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Default: main page for latest articles
            url = "https://www.amadershomoy.com/"
            self.stats['requests_made'] += 1
            yield Request(
                url=url,
                callback=self.parse_category,
                meta={'category': 'General', 'cat_slug': '', 'page': 1},
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Sitemap Parsing (Primary Source)
    # ================================================================

    def parse_sitemap(self, response: Response) -> Generator:
        """Parse sitemap XML to extract article URLs."""
        sel = Selector(response)
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            lastmod = url_node.xpath('lastmod/text()').get('').strip()

            if not loc:
                continue

            if 'amadershomoy.com' not in loc:
                continue

            # Filter for article URLs matching /{category}/article/{ID}/{slug}
            if not re.search(r'/article/\d+/', loc):
                continue

            self._sitemap_urls_seen.add(loc)

            if self.is_url_in_db(loc):
                continue

            # Date filter on lastmod
            if lastmod:
                parsed_date = self._parse_date_string(lastmod)
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

        # Also launch category fallback for broader coverage
        if sitemap_count < 5:
            self.logger.info("Sitemap returned few items, launching category fallback")
            yield from self._generate_category_requests()

    # ================================================================
    # Category Page Parsing (Fallback)
    # ================================================================
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)
        
        # Extract article links - site uses /{category}/article/{ID}/{slug} pattern
        article_links = response.css('a[href*="/article/"]::attr(href)').getall()
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
            if not url.startswith('http'):
                url = f"https://www.amadershomoy.com{url}"
            
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
            next_page_link = response.css('a.next::attr(href), a[rel="next"]::attr(href)').get()
            if next_page_link:
                if not next_page_link.startswith('http'):
                    next_page_link = f"https://www.amadershomoy.com{next_page_link}"
                
                self.stats['requests_made'] += 1
                yield Request(
                    url=next_page_link,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': page + 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # ROBUST FALLBACK: Try universal extraction first
        fallback = self.extract_article_fallback(response)
        if fallback and fallback.get('headline') and fallback.get('article_body'):
            if len(fallback.get('article_body', '')) >= 100:
                pub_date = self.parse_article_date(str(fallback.get('publication_date', ''))) if fallback.get('publication_date') else None
                if pub_date and not self.is_date_in_range(pub_date):
                    self.stats['date_filtered'] += 1
                    return
                if not self.filter_by_search_query(fallback['headline'], fallback['article_body']):
                    return
                self.stats['articles_processed'] += 1
                yield self.create_article_item(
                    url=url,
                    headline=fallback['headline'],
                    article_body=fallback['article_body'],
                    author=fallback.get('author') or self.extract_author(response),
                    publication_date=pub_date.isoformat() if pub_date else None,
                    image_url=fallback.get('image_url'),
                    category=response.meta.get('category', 'General'),
                )
                return
        
        # Original extraction
        
        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('h1.test::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        # Extract body - site uses .description class
        body_parts = response.css('.description p::text, .description::text').getall()
        
        if not body_parts:
            body_parts = response.css('article p::text, .content p::text, p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        # Search filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Parse date - site uses .publish-time class
        pub_date = None
        date_text = (
            response.css('p.publish-time::text').get() or
            response.css('.publish-time::text').get() or
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            response.css('time::attr(datetime)').get()
        )
        
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        category = response.meta.get('category', 'General')
        image_url = response.css('meta[property="og:image"]::attr(content)').get()
        
        # Extract author
        author = self.extract_author(response)
        
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
