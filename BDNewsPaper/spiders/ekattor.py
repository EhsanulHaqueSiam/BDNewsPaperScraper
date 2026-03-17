"""
Ekattor TV Spider (Bangla)
==========================
Scrapes articles from Ekattor TV (ekattor.tv)

Features:
    - News sitemap as primary source (117 URLs with dates, titles, keywords)
    - Category-based scraping as fallback
    - Date filtering (client-side)
    - Search query filtering
"""

import re
from html import unescape
from typing import Generator

import scrapy
from scrapy.http import Request, Response
from scrapy.selector import Selector

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class EkattorTVSpider(BaseNewsSpider):
    """
    Spider for Ekattor TV (TV News Portal).

    Uses news sitemap as primary source, HTML scraping as fallback.
    URL Pattern: ekattor.tv/{category}/{id}/title-slug

    Usage:
        scrapy crawl ekattor -a categories=politics,national
        scrapy crawl ekattor -a max_pages=10
    """
    
    name = 'ekattor'
    paper_name = 'Ekattor TV'
    allowed_domains = ['ekattor.tv', 'www.ekattor.tv']
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
        'country': 'country',
        'capital': 'capital',
        'tech': 'tech',
        'technology': 'tech',
        'lifestyle': 'lifestyle',
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
        self._sitemap_urls_seen = set()
        self.logger.info(f"Ekattor TV spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: news sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: News sitemap (117 URLs with dates, titles, keywords)
        sitemap_url = "https://ekattor.tv/news-sitemap.xml"
        self.logger.info(f"Fetching news sitemap: {sitemap_url}")
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
                url = f"https://ekattor.tv/{cat_slug}"

                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1

                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            default_cats = ['national', 'politics', 'sports', 'international']
            for cat in default_cats:
                cat_slug = self.CATEGORIES.get(cat, cat)
                url = f"https://ekattor.tv/{cat_slug}"

                self.logger.info(f"Crawling category: {cat} -> {url}")
                self.stats['requests_made'] += 1

                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )

    # ================================================================
    # Sitemap Parsing (Primary Source)
    # ================================================================

    def parse_sitemap(self, response: Response) -> Generator:
        """Parse news sitemap XML to extract article URLs."""
        sel = Selector(response)
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            pub_date_text = url_node.xpath('//publication_date/text()').get('').strip() or \
                            url_node.xpath('lastmod/text()').get('').strip()

            if not loc:
                continue

            if 'ekattor.tv' not in loc:
                continue

            # Only follow article-like URLs (with numeric IDs)
            if not re.search(r'/\d+/', loc):
                continue

            self._sitemap_urls_seen.add(loc)

            if self.is_url_in_db(loc):
                continue

            # Date filter
            if pub_date_text:
                parsed_date = self._parse_date_string(pub_date_text)
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
        
        # Find article links - Ekattor uses /category/id/slug pattern
        article_links = response.css('a::attr(href)').getall()
        
        # Filter to article links
        article_links = [l for l in article_links if 'ekattor.tv' in l and re.search(r'/\d+/', l)]
        
        # Deduplicate
        article_links = list(set(article_links))
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail
        if not article_links:
            self.logger.info("CSS selectors failed, using universal link discovery")
            article_links = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
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
            next_page = page + 1
            next_url = f"https://ekattor.tv/{cat_slug}?page={next_page}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={'category': category, 'cat_slug': cat_slug, 'page': next_page},
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
        
        headline = (
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return
        
        headline = unescape(headline.strip())
        
        body_parts = response.css('.news-content p::text, .content p::text, article p::text').getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return
        
        if not self.filter_by_search_query(headline, article_body):
            return
        
        pub_date = None
        date_text = (
            response.css('.date::text').get() or
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            ''
        )
        
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
