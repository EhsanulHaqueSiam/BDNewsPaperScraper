"""
NTV BD English Spider
=====================
Scrapes articles from NTV BD English (en.ntvbd.com)

Features:
    - Sitemap index as primary source (48 sub-sitemaps)
    - Category-based HTML scraping as fallback
    - Date filtering (client-side)
    - Video news source with articles
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response
from scrapy.selector import Selector
from w3lib.html import remove_tags

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class NTVBDSpider(BaseNewsSpider):
    """
    Spider for NTV BD English.

    Uses sitemap as primary source, with HTML scraping fallback.
    News portal with video and text content.

    Usage:
        scrapy crawl ntvbd -a categories=bangladesh,sports,world
        scrapy crawl ntvbd -a max_pages=10
    """

    name = 'ntvbd'
    paper_name = 'NTV BD'
    allowed_domains = ['en.ntvbd.com', 'ntvbd.com']
    language = 'English'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # Category slug mappings
    CATEGORIES = {
        'national': 'bangladesh',
        'bangladesh': 'bangladesh',
        'international': 'world',
        'world': 'world',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'business': 'business',
        'economy': 'business',
        'education': 'education',
        'health': 'health',
        'lifestyle': 'lifestyle',
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
        self.logger.info(f"NTV BD spider initialized")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: sitemap index first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: Sitemap index (48 sub-sitemaps, fresh)
        self.stats['requests_made'] += 1
        yield Request(
            url='https://ntvbd.com/sitemap.xml',
            callback=self.parse_sitemap_index,
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
                url = f"https://en.ntvbd.com/{cat_slug}"
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            default_cats = ['bangladesh', 'world', 'sports', 'business']
            for cat in default_cats:
                url = f"https://en.ntvbd.com/{cat}"
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_slug': cat, 'page': 1},
                    errback=self.handle_request_failure,
                )

    # ================================================================
    # Sitemap Parsing (Primary Source)
    # ================================================================

    def parse_sitemap_index(self, response: Response) -> Generator:
        """Parse sitemap index XML to find the most recent sub-sitemap."""
        sel = Selector(response, type='xml')
        sel.remove_namespaces()

        # Extract all sub-sitemap URLs
        sitemaps = sel.xpath('//sitemap')

        self.logger.info(f"Sitemap index: Found {len(sitemaps)} sub-sitemaps")

        if not sitemaps:
            # Maybe it's a flat sitemap, not an index
            self.logger.info("No sub-sitemaps found, trying as flat sitemap")
            yield from self.parse_sitemap(response)
            return

        # Collect sub-sitemaps with their lastmod dates
        sitemap_entries = []
        for sm in sitemaps:
            loc = sm.xpath('loc/text()').get('').strip()
            lastmod = sm.xpath('lastmod/text()').get('').strip()
            if loc:
                sitemap_entries.append((loc, lastmod))

        # Sort by lastmod descending to get most recent first
        sitemap_entries.sort(key=lambda x: x[1] if x[1] else '', reverse=True)

        # Fetch the most recent sub-sitemaps (limit to top 3 to avoid excessive requests)
        fetched = 0
        for loc, lastmod in sitemap_entries:
            if fetched >= 3:
                break

            self.logger.info(f"Fetching sub-sitemap: {loc} (lastmod: {lastmod})")
            self.stats['requests_made'] += 1
            fetched += 1

            yield Request(
                url=loc,
                callback=self.parse_sitemap,
                headers={'Accept': 'application/xml, text/xml'},
                errback=self.handle_request_failure,
                meta={'source': 'sitemap'},
            )

    def parse_sitemap(self, response: Response) -> Generator:
        """Parse sitemap XML to extract article URLs."""
        sel = Selector(response, type='xml')
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            lastmod = url_node.xpath('lastmod/text()').get('').strip()

            if not loc:
                continue

            if 'ntvbd.com' not in loc:
                continue

            # Skip non-article URLs (category pages, main pages)
            # Articles typically have a path with content segments
            path = loc.split('ntvbd.com/')[-1] if 'ntvbd.com/' in loc else ''
            if not path or path.count('/') < 1:
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
                meta={'category': 'General', 'source': 'sitemap'},
                errback=self.handle_request_failure,
            )

        self.logger.info(f"Sitemap: Yielded {sitemap_count} article requests")

    # ================================================================
    # HTML Scraping (Fallback)
    # ================================================================

    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)

        # Find article links
        article_links = response.css('a::attr(href)').getall()
        # Filter to article links - pattern: en.ntvbd.com/category/slug
        article_links = [l for l in article_links if 'en.ntvbd.com/' in l and '/' in l.split('en.ntvbd.com/')[-1]]

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
            if url in self._sitemap_urls_seen:
                continue

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
            next_url = f"https://en.ntvbd.com/{cat_slug}?page={next_page}"

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
            return

        headline = unescape(headline.strip())

        body_parts = response.css('article p::text, .content p::text, .news-content p::text').getall()
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
