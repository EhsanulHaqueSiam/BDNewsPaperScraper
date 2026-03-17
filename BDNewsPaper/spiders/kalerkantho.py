"""
Kaler Kantho Spider (Bangla)
============================
Scrapes articles from kalerkantho.com — a TOP 5 Bangla newspaper.

Features:
    - RSS feed as primary source (title, link, pubDate)
    - Sitemap index with daily sitemaps as secondary
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


class KalerKanthoSpider(BaseNewsSpider):
    """
    Spider for Kaler Kantho (Top Bangla Newspaper).

    Primary: RSS feed at /rss.xml (latest articles with title + link + pubDate).
    Secondary: Daily sitemap index at /sitemap.xml.
    Fallback: Category HTML pages.

    Usage:
        scrapy crawl kalerkantho
        scrapy crawl kalerkantho -a categories=national,politics,sports
        scrapy crawl kalerkantho -a start_date=2026-03-01
    """

    name = 'kalerkantho'
    paper_name = 'Kaler Kantho'
    allowed_domains = ['kalerkantho.com', 'www.kalerkantho.com']
    language = 'Bangla'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # Category slug mappings (kalerkantho uses /online/{category} URL pattern)
    CATEGORIES = {
        'national': 'online/national',
        'bangladesh': 'online/national',
        'politics': 'online/Politics',
        'country-news': 'online/country-news',
        'country': 'online/country-news',
        'saradesh': 'online/country-news',
        'international': 'online/world',
        'world': 'online/world',
        'sports': 'online/sport',
        'sport': 'online/sport',
        'business': 'online/business',
        'economy': 'online/business',
        'entertainment': 'online/entertainment',
        'tech': 'online/info-tech',
        'technology': 'online/info-tech',
        'lifestyle': 'online/lifestyle',
        'education': 'online/campus',
        'campus': 'online/campus',
        'opinion': 'online/opinion',
        'editorial': 'online/editorial',
        'crime': 'online/crime',
    }
    DEFAULT_CATEGORIES = ['national', 'politics', 'sports', 'business']

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sitemap_urls_seen = set()
        self.logger.info("Kaler Kantho spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default (RSS)'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: RSS primary, sitemap secondary, HTML fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed (fast, latest articles)
        rss_url = "https://www.kalerkantho.com/rss.xml"
        self.logger.info(f"Fetching RSS feed: {rss_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=rss_url,
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss', 'scrapling': True},
        )

        # Secondary: Today's sitemap for broader coverage
        today = datetime.now().strftime('%Y-%m-%d')
        sitemap_url = f"https://www.kalerkantho.com/daily-sitemap/{today}/sitemap.xml"
        self.logger.info(f"Fetching daily sitemap: {sitemap_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=sitemap_url,
            callback=self.parse_daily_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap', 'scrapling': True},
        )

    def _rss_failed(self, failure):
        """If RSS fails, fall back to category-based HTML scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to category scraping.")
        self.stats['errors'] += 1
        yield from self._generate_category_requests()

    def _generate_category_requests(self) -> Generator[Request, None, None]:
        """Generate requests for category pages (fallback mode)."""
        cats = self.categories if self.categories else self.DEFAULT_CATEGORIES
        for category in cats:
            cat_lower = category.lower().strip()
            cat_slug = self.CATEGORIES.get(cat_lower, f'online/{cat_lower}')
            url = f"https://www.kalerkantho.com/{cat_slug}"

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
    # RSS Parsing (Primary)
    # ================================================================

    def parse_rss(self, response: Response) -> Generator:
        """Parse RSS feed and yield article requests."""
        selector = scrapy.Selector(response, type='xml')
        selector.remove_namespaces()

        items = selector.xpath('//item')
        if not items:
            self.logger.warning(f"No items in RSS feed: {response.url}")
            yield from self._generate_category_requests()
            return

        self.logger.info(f"Found {len(items)} items in RSS feed")

        for item in items:
            title = item.xpath('title/text()').get()
            link = item.xpath('link/text()').get()
            pub_date_str = item.xpath('pubDate/text()').get()

            if not link:
                continue

            link = link.strip()

            if self.is_url_in_db(link):
                continue

            # Parse and filter by date
            pub_date = self._parse_rss_date(pub_date_str)
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                continue

            # Extract category from URL (e.g., /online/country-news/... -> country-news)
            category = 'General'
            url_match = re.search(r'kalerkantho\.com/online/([^/]+)', link)
            if url_match:
                category = url_match.group(1)

            # If categories specified, filter
            if self.categories:
                cat_lower = category.lower()
                matching = any(
                    cat_lower == c.lower() or
                    self.CATEGORIES.get(c.lower(), '').endswith(cat_lower)
                    for c in self.categories
                )
                if not matching:
                    continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            yield Request(
                url=link,
                callback=self.parse_article,
                meta={
                    'category': category,
                    'rss_title': unescape(title.strip()) if title else None,
                    'rss_pub_date': pub_date.isoformat() if pub_date else None,
                    'scrapling': True,
                },
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Sitemap Parsing (Secondary)
    # ================================================================

    def parse_daily_sitemap(self, response: Response) -> Generator:
        """Parse daily sitemap XML for article URLs."""
        sel = Selector(response)
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Daily sitemap: Found {len(urls)} URLs")

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            lastmod = url_node.xpath('lastmod/text()').get('').strip()

            if not loc or 'kalerkantho.com' not in loc:
                continue

            # Only article URLs (contain date pattern like /2026/03/17/)
            if not re.search(r'/\d{4}/\d{2}/\d{2}/', loc):
                continue

            if loc in self._sitemap_urls_seen:
                continue
            self._sitemap_urls_seen.add(loc)

            if self.is_url_in_db(loc):
                continue

            # Date filter from lastmod
            if lastmod:
                parsed_date = self._parse_date_string(lastmod)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Extract category from URL
            category = 'General'
            url_match = re.search(r'kalerkantho\.com/online/([^/]+)', loc)
            if url_match:
                category = url_match.group(1)

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={'category': category, 'scrapling': True},
                errback=self.handle_request_failure,
            )

    # ================================================================
    # Category Page Parsing (Fallback)
    # ================================================================

    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)

        # Find article links with date pattern
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            response.urljoin(l) for l in article_links
            if re.search(r'/\d{4}/\d{2}/\d{2}/\d+', l)
        ]
        article_links = list(set(article_links))

        # Robust fallback: universal link discovery
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
            next_url = f"https://www.kalerkantho.com/{cat_slug}?page={next_page}"
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

        # Try universal fallback extraction first (JSON-LD + generic selectors)
        fallback = self.extract_article_fallback(response)
        if fallback and fallback.get('headline') and fallback.get('article_body'):
            if len(fallback.get('article_body', '')) >= 100:
                pub_date = self.parse_article_date(
                    str(fallback.get('publication_date', ''))
                ) if fallback.get('publication_date') else None

                # Use RSS date as fallback
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

        # Manual extraction for Kaler Kantho (Next.js SSR site)
        headline = (
            response.meta.get('rss_title') or
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return

        headline = unescape(headline.strip())

        # Article body - Kaler Kantho uses various content selectors
        body_parts = response.css(
            '.news-content p::text, '
            '.some_class p::text, '
            '.content-details p::text, '
            'article p::text, '
            '.article-content p::text'
        ).getall()

        if not body_parts:
            body_parts = response.css('p::text').getall()

        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())

        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return

        if not self.filter_by_search_query(headline, article_body):
            return

        # Date extraction
        pub_date = None
        if response.meta.get('rss_pub_date'):
            pub_date = self.parse_article_date(response.meta['rss_pub_date'])

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
