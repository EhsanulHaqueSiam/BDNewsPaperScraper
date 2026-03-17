"""
The Business Post Spider (English)
==================================
Scrapes articles from thebusinesspost.net — a Bangladeshi English-language
business news outlet.

Note: As of March 2026, thebusinesspost.net domain has expired and redirects
to a third-party site. This spider is pre-built to work once the domain is
restored. It probes for RSS/sitemap on startup and falls back to category
HTML scraping.

Features:
    - RSS/Sitemap probing (auto-discovers feeds on startup)
    - Category-based HTML scraping as fallback
    - Universal fallback extraction (JSON-LD + generic selectors)
    - Date filtering (client-side)
    - Search query filtering
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response
from scrapy.selector import Selector

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class TheBusinessPostSpider(BaseNewsSpider):
    """
    Spider for The Business Post (English Business Newspaper).

    Primary: RSS/Sitemap probing (auto-discovers feeds).
    Fallback: Category HTML pages.

    Usage:
        scrapy crawl thebusinesspost
        scrapy crawl thebusinesspost -a categories=economy,national,politics
        scrapy crawl thebusinesspost -a start_date=2026-03-01
    """

    name = 'thebusinesspost'
    paper_name = 'The Business Post'
    allowed_domains = ['thebusinesspost.net', 'www.thebusinesspost.net']
    language = 'English'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # Category slug mappings (typical English business newspaper)
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'sport': 'sports',
        'business': 'business',
        'economy': 'economy',
        'finance': 'finance',
        'stock': 'stock-market',
        'stock-market': 'stock-market',
        'banking': 'banking',
        'trade': 'trade',
        'entertainment': 'entertainment',
        'tech': 'technology',
        'technology': 'technology',
        'opinion': 'opinion',
        'editorial': 'editorial',
    }
    DEFAULT_CATEGORIES = ['business', 'economy', 'national', 'politics']

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._feed_found = False
        self.logger.info("The Business Post spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: probe feeds then category pages."""
        self.stats['requests_made'] = 0

        # Probe for RSS/Sitemap feeds
        feed_endpoints = [
            '/feed', '/rss', '/rss.xml', '/sitemap.xml',
            '/news-sitemap.xml', '/news_sitemap.xml',
            '/wp-json/wp/v2/posts?per_page=20',
        ]

        for endpoint in feed_endpoints:
            url = f"https://www.thebusinesspost.net{endpoint}"
            self.stats['requests_made'] += 1
            yield Request(
                url=url,
                callback=self.parse_feed_probe,
                errback=self.handle_request_failure,
                meta={'endpoint': endpoint},
                dont_filter=True,
            )

        # Category pages as primary source
        yield from self._generate_category_requests()

    def _generate_category_requests(self) -> Generator[Request, None, None]:
        """Generate requests for category pages."""
        cats = self.categories if self.categories else self.DEFAULT_CATEGORIES
        for category in cats:
            cat_lower = category.lower().strip()
            cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
            url = f"https://www.thebusinesspost.net/{cat_slug}"

            self.logger.info(f"Crawling category: {category} -> {url}")
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_category,
                meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Feed Probe
    # ================================================================

    def parse_feed_probe(self, response: Response) -> Generator:
        """Probe for RSS/sitemap/WP-API feeds."""
        content_type = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
        endpoint = response.meta.get('endpoint', '')

        # Check if this is XML (RSS/Sitemap)
        is_xml = 'xml' in content_type or response.text.strip().startswith('<?xml')
        # Check if this is WP REST API JSON
        is_json = 'json' in content_type and endpoint.startswith('/wp-json')

        if response.status == 200 and is_xml:
            self._feed_found = True
            self.logger.info(f"Found working XML feed at {endpoint}")

            if 'sitemap' in endpoint:
                yield from self._parse_sitemap_feed(response)
            else:
                yield from self._parse_rss_feed(response)

        elif response.status == 200 and is_json:
            self._feed_found = True
            self.logger.info(f"Found working WP REST API at {endpoint}")
            yield from self._parse_wp_api(response)

    def _parse_rss_feed(self, response: Response) -> Generator:
        """Parse RSS feed."""
        selector = scrapy.Selector(response, type='xml')
        selector.remove_namespaces()
        items = selector.xpath('//item')

        self.logger.info(f"RSS feed: Found {len(items)} items")

        for item in items:
            link = item.xpath('link/text()').get()
            title = item.xpath('title/text()').get()
            pub_date_str = item.xpath('pubDate/text()').get()

            if not link:
                continue
            link = link.strip()

            if self.is_url_in_db(link):
                continue

            pub_date = self._parse_rss_date(pub_date_str)
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            yield Request(
                url=link,
                callback=self.parse_article,
                meta={
                    'category': 'General',
                    'rss_title': unescape(title.strip()) if title else None,
                    'rss_pub_date': pub_date.isoformat() if pub_date else None,
                },
                errback=self.handle_request_failure,
            )

    def _parse_sitemap_feed(self, response: Response) -> Generator:
        """Parse sitemap XML."""
        sel = Selector(response)
        sel.remove_namespaces()

        # Check if this is a sitemap index
        sub_sitemaps = sel.xpath('//sitemap/loc/text()').getall()
        if sub_sitemaps:
            for sitemap_loc in sub_sitemaps[:5]:
                yield Request(
                    url=sitemap_loc.strip(),
                    callback=self._parse_sitemap_feed,
                    errback=self.handle_request_failure,
                )
            return

        urls = sel.xpath('//url')
        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            if not loc or not self.is_valid_article_url(loc):
                continue
            if self.is_url_in_db(loc):
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={'category': 'General'},
                errback=self.handle_request_failure,
            )

    def _parse_wp_api(self, response: Response) -> Generator:
        """Parse WordPress REST API response."""
        import json
        try:
            posts = json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            return

        for post in posts:
            link = post.get('link', '')
            if not link or self.is_url_in_db(link):
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            yield Request(
                url=link,
                callback=self.parse_article,
                meta={'category': 'General'},
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Category Page Parsing
    # ================================================================

    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)

        # Find article links
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            response.urljoin(l) for l in article_links
            if re.search(r'/\d+', l) and (
                'thebusinesspost.net' in l or l.startswith('/')
            )
        ]
        article_links = list(set(article_links))

        # Robust fallback
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

        if found_count > 0 and page < self.max_pages:
            next_page = page + 1
            next_url = f"https://www.thebusinesspost.net/{cat_slug}?page={next_page}"
            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={
                    'category': category,
                    'cat_slug': cat_slug,
                    'page': next_page,
                },
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Article Parsing
    # ================================================================

    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url

        # Try universal fallback extraction first
        fallback = self.extract_article_fallback(response)
        if fallback and fallback.get('headline') and fallback.get('article_body'):
            if len(fallback.get('article_body', '')) >= 100:
                pub_date = self.parse_article_date(
                    str(fallback.get('publication_date', ''))
                ) if fallback.get('publication_date') else None

                if not pub_date and response.meta.get('rss_pub_date'):
                    pub_date = self.parse_article_date(response.meta['rss_pub_date'])

                if pub_date and not self.is_date_in_range(pub_date):
                    self.stats['date_filtered'] += 1
                    return

                if not self.filter_by_search_query(
                    fallback['headline'], fallback['article_body']
                ):
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

        # Manual extraction
        headline = (
            response.meta.get('rss_title') or
            response.css('h1::text').get() or
            response.css('h1.entry-title::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return

        headline = unescape(headline.strip())

        body_parts = response.css(
            '.entry-content p::text, '
            '.article-content p::text, '
            '.post-content p::text, '
            '.story-body p::text, '
            'article p::text'
        ).getall()

        if not body_parts:
            body_parts = response.css('p::text').getall()

        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())

        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return

        if not self.filter_by_search_query(headline, article_body):
            return

        pub_date = None
        if response.meta.get('rss_pub_date'):
            pub_date = self.parse_article_date(response.meta['rss_pub_date'])

        if not pub_date:
            date_text = (
                response.css('meta[property="article:published_time"]::attr(content)').get() or
                response.css('time[datetime]::attr(datetime)').get() or
                response.css('.post-date::text').get() or
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

    # ================================================================
    # Helper Methods
    # ================================================================

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS pubDate format (RFC 822)."""
        if not date_str:
            return None

        date_str = date_str.strip()

        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%d %b %Y %H:%M:%S %z',
            '%Y-%m-%dT%H:%M:%S%z',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return self._parse_date_string(date_str)
