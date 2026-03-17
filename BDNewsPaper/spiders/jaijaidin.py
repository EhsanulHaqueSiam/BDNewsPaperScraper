"""
Jai Jai Din Spider (Bangla)
===========================
Scrapes articles from jaijaidinbd.com — a Bangladeshi daily newspaper.

Note: As of March 2026, jaijaidinbd.com hosting is suspended. This spider
is pre-built to work once the site is restored. It uses category-based HTML
scraping as the primary method since no RSS/sitemap was available when the
site was last accessible.

Features:
    - Category-based HTML scraping (primary)
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

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class JaiJaiDinSpider(BaseNewsSpider):
    """
    Spider for Jai Jai Din (Bangla Daily Newspaper).

    Primary: Category HTML pages (no reliable RSS/sitemap discovered).
    Fallback: Universal link discovery + auto extraction.

    Usage:
        scrapy crawl jaijaidin
        scrapy crawl jaijaidin -a categories=national,sports,politics
        scrapy crawl jaijaidin -a start_date=2026-03-01
    """

    name = 'jaijaidin'
    paper_name = 'Jai Jai Din'
    allowed_domains = ['jaijaidinbd.com', 'www.jaijaidinbd.com']
    language = 'Bangla'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # Category slug mappings (common Bangla newspaper patterns)
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'sport': 'sports',
        'entertainment': 'entertainment',
        'economy': 'economy',
        'business': 'economy',
        'technology': 'technology',
        'tech': 'technology',
        'lifestyle': 'lifestyle',
        'education': 'education',
        'opinion': 'opinion',
        'country': 'country-news',
    }
    DEFAULT_CATEGORIES = ['national', 'politics', 'sports', 'economy']

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Jai Jai Din spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category pages."""
        self.stats['requests_made'] = 0

        # Try RSS/sitemap first (in case site restores them)
        for endpoint in ['/rss.xml', '/sitemap.xml', '/news_sitemap.xml', '/feed']:
            url = f"https://www.jaijaidinbd.com{endpoint}"
            self.stats['requests_made'] += 1
            yield Request(
                url=url,
                callback=self.parse_feed_probe,
                errback=self.handle_request_failure,
                meta={'endpoint': endpoint, 'dont_redirect': True},
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
            url = f"https://www.jaijaidinbd.com/{cat_slug}"

            self.logger.info(f"Crawling category: {category} -> {url}")
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_category,
                meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Feed Probe (discover RSS/Sitemap if restored)
    # ================================================================

    def parse_feed_probe(self, response: Response) -> Generator:
        """Probe for RSS/sitemap feeds in case site restores them."""
        content_type = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
        endpoint = response.meta.get('endpoint', '')

        if response.status == 200 and ('xml' in content_type or response.text.strip().startswith('<?xml')):
            self.logger.info(f"Found working feed at {endpoint}! Parsing...")

            if 'sitemap' in endpoint:
                yield from self._parse_sitemap_probe(response)
            else:
                yield from self._parse_rss_probe(response)

    def _parse_rss_probe(self, response: Response) -> Generator:
        """Parse RSS feed if discovered."""
        selector = scrapy.Selector(response, type='xml')
        selector.remove_namespaces()
        items = selector.xpath('//item')

        for item in items:
            link = item.xpath('link/text()').get()
            if link and self.is_valid_article_url(link.strip()):
                link = link.strip()
                if not self.is_url_in_db(link):
                    self.stats['articles_found'] += 1
                    self.stats['requests_made'] += 1
                    yield Request(
                        url=link,
                        callback=self.parse_article,
                        meta={'category': 'General'},
                        errback=self.handle_request_failure,
                    )

    def _parse_sitemap_probe(self, response: Response) -> Generator:
        """Parse sitemap if discovered."""
        from scrapy.selector import Selector
        sel = Selector(response)
        sel.remove_namespaces()

        for loc in sel.xpath('//url/loc/text()').getall():
            loc = loc.strip()
            if loc and self.is_valid_article_url(loc) and not self.is_url_in_db(loc):
                self.stats['articles_found'] += 1
                self.stats['requests_made'] += 1
                yield Request(
                    url=loc,
                    callback=self.parse_article,
                    meta={'category': 'General'},
                    errback=self.handle_request_failure,
                )

    # ================================================================
    # Category Page Parsing (Primary)
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
            if re.search(r'/\d+', l) and ('jaijaidinbd.com' in l or l.startswith('/'))
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

        # Pagination
        if found_count > 0 and page < self.max_pages:
            next_page = page + 1
            next_url = f"https://www.jaijaidinbd.com/{cat_slug}?page={next_page}"
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
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return

        headline = unescape(headline.strip())

        body_parts = response.css(
            '.news-content p::text, '
            '.content p::text, '
            '.article-body p::text, '
            '.details-content p::text, '
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
        date_text = (
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            response.css('time[datetime]::attr(datetime)').get() or
            response.css('.date::text').get() or
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
