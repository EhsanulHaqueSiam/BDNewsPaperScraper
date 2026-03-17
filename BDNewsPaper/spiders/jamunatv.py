"""
Jamuna TV Spider (Bangla)
=========================
Scrapes articles from jamuna.tv — a major Bangladeshi TV news channel.

Features:
    - News sitemap as primary source (news_sitemap.xml with dates, titles)
    - Category-based HTML scraping as fallback
    - Cloudflare-protected: uses Scrapling for TLS impersonation
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


class JamunaTVSpider(BaseNewsSpider):
    """
    Spider for Jamuna TV (TV News Portal).

    Primary: News sitemap at /news_sitemap.xml (URLs with dates and titles).
    Fallback: Category HTML pages.

    URL Pattern: jamuna.tv/{category}/{id}

    Usage:
        scrapy crawl jamunatv
        scrapy crawl jamunatv -a categories=bangladesh,sports,economy
        scrapy crawl jamunatv -a start_date=2026-03-01
    """

    name = 'jamunatv'
    paper_name = 'Jamuna TV'
    allowed_domains = ['jamuna.tv', 'www.jamuna.tv']
    language = 'Bangla'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'bangladesh',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'economy': 'economy',
        'business': 'business',
        'technology': 'technology',
        'tech': 'technology',
        'lifestyle': 'lifestyle',
        'health': 'health',
        'opinion': 'opinion',
        'viral': 'viral',
        'art-and-literature': 'art-and-literature',
    }
    DEFAULT_CATEGORIES = ['bangladesh', 'international', 'sports', 'economy']

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sitemap_urls_seen = set()
        self.logger.info("Jamuna TV spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default (sitemap)'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: news sitemap primary, category fallback."""
        self.stats['requests_made'] = 0

        # Primary: News sitemap
        sitemap_url = "https://jamuna.tv/news_sitemap.xml"
        self.logger.info(f"Fetching news sitemap: {sitemap_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=sitemap_url,
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self._sitemap_failed,
            meta={'source': 'sitemap', 'scrapling': True},
        )

    def _sitemap_failed(self, failure):
        """If sitemap fails, fall back to category-based HTML scraping."""
        self.logger.warning(f"Sitemap failed: {failure.value}. Falling back to categories.")
        self.stats['errors'] += 1
        yield from self._generate_category_requests()

    def _generate_category_requests(self) -> Generator[Request, None, None]:
        """Generate requests for category pages (fallback mode)."""
        cats = self.categories if self.categories else self.DEFAULT_CATEGORIES
        for category in cats:
            cat_lower = category.lower().strip()
            cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
            url = f"https://jamuna.tv/{cat_slug}"

            self.logger.info(f"Crawling category: {category} -> {url}")
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_category,
                meta={
                    'category': category,
                    'cat_slug': cat_slug,
                    'page': 1,
                    'scrapling': True,
                },
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

        self.logger.info(f"News sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            pub_date_text = (
                url_node.xpath('.//publication_date/text()').get('').strip() or
                url_node.xpath('lastmod/text()').get('').strip()
            )
            title = url_node.xpath('.//title/text()').get('').strip()

            if not loc or 'jamuna.tv' not in loc:
                continue

            # Only article URLs with numeric IDs
            if not re.search(r'/\d+$', loc):
                continue

            if loc in self._sitemap_urls_seen:
                continue
            self._sitemap_urls_seen.add(loc)

            if self.is_url_in_db(loc):
                continue

            # Date filter
            pub_date = None
            if pub_date_text:
                pub_date = self._parse_date_string(pub_date_text)
                if pub_date and not self.is_date_in_range(pub_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Extract category from URL (e.g., /national/653258 -> national)
            category = 'General'
            url_match = re.search(r'jamuna\.tv/([^/]+)/\d+', loc)
            if url_match:
                category = url_match.group(1)

            # Category filter
            if self.categories:
                cat_lower = category.lower()
                matching = any(
                    cat_lower == c.lower() or
                    self.CATEGORIES.get(c.lower(), '') == cat_lower
                    for c in self.categories
                )
                if not matching:
                    continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            sitemap_count += 1

            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={
                    'category': category,
                    'sitemap_title': title,
                    'sitemap_pub_date': pub_date.isoformat() if pub_date else None,
                    'scrapling': True,
                },
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

        # Find article links with numeric IDs
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            response.urljoin(l) for l in article_links
            if re.search(r'/\d+$', l) and ('jamuna.tv' in l or l.startswith('/'))
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
                meta={'category': category, 'scrapling': True},
                errback=self.handle_request_failure,
            )

        # Pagination
        if found_count > 0 and page < self.max_pages:
            next_page = page + 1
            next_url = f"https://jamuna.tv/{cat_slug}?page={next_page}"
            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={
                    'category': category,
                    'cat_slug': cat_slug,
                    'page': next_page,
                    'scrapling': True,
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

                if not pub_date and response.meta.get('sitemap_pub_date'):
                    pub_date = self.parse_article_date(response.meta['sitemap_pub_date'])

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
            response.meta.get('sitemap_title') or
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return

        headline = unescape(headline.strip())

        # Article body
        body_parts = response.css(
            '.news-content p::text, '
            '.content p::text, '
            '.article-content p::text, '
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

        # Date
        pub_date = None
        if response.meta.get('sitemap_pub_date'):
            pub_date = self.parse_article_date(response.meta['sitemap_pub_date'])

        if not pub_date:
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
