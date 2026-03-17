"""
Bangla News 24 Spider (Bangla)
==============================
Scrapes articles from banglanews24.com — a major Bangladeshi online news portal.

Features:
    - RSS feed as primary source (/rss.xml with title, link, pubDate)
    - Daily sitemap as secondary source
    - Category-based HTML scraping as fallback
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


class BanglaNews24Spider(BaseNewsSpider):
    """
    Spider for Bangla News 24 (Online News Portal).

    Primary: RSS feed at /rss.xml (latest articles with title + link + pubDate).
    Secondary: Daily sitemaps.
    Fallback: Category HTML pages.

    URL Pattern: banglanews24.com/{category}/news/bd/{id}.details

    Usage:
        scrapy crawl banglanews24
        scrapy crawl banglanews24 -a categories=national,politics,sports
        scrapy crawl banglanews24 -a start_date=2026-03-01
    """

    name = 'banglanews24'
    paper_name = 'Bangla News 24'
    allowed_domains = ['banglanews24.com', 'www.banglanews24.com']
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
        'sport': 'sports',
        'business': 'economics-business',
        'economy': 'economics-business',
        'economics': 'economics-business',
        'entertainment': 'entertainment',
        'tech': 'information-technology',
        'technology': 'information-technology',
        'lifestyle': 'lifestyle',
        'feature': 'feature',
        'saradesh': 'saradesh',
        'country': 'saradesh',
        'chittagong': 'daily-chittagong',
        'art-literature': 'art-literature',
        'education': 'education',
    }
    DEFAULT_CATEGORIES = ['national', 'politics', 'sports', 'economics-business']

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sitemap_urls_seen = set()
        self.logger.info("Bangla News 24 spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default (RSS)'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: RSS primary, sitemap secondary, HTML fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        rss_url = "https://www.banglanews24.com/rss.xml"
        self.logger.info(f"Fetching RSS feed: {rss_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=rss_url,
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

        # Secondary: Today's daily sitemap
        today = datetime.now().strftime('%Y-%m-%d')
        sitemap_url = f"https://www.banglanews24.com/daily-sitemap/{today}/sitemap.xml"
        self.logger.info(f"Fetching daily sitemap: {sitemap_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=sitemap_url,
            callback=self.parse_daily_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

    def _rss_failed(self, failure):
        """If RSS fails, fall back to category-based HTML scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to categories.")
        self.stats['errors'] += 1
        yield from self._generate_category_requests()

    def _generate_category_requests(self) -> Generator[Request, None, None]:
        """Generate requests for category pages (fallback mode)."""
        cats = self.categories if self.categories else self.DEFAULT_CATEGORIES
        for category in cats:
            cat_lower = category.lower().strip()
            cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
            url = f"https://www.banglanews24.com/category/{cat_slug}"

            self.logger.info(f"Crawling category: {category} -> {url}")
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_category,
                meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
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

            # Extract category from URL (e.g., /national/news/bd/... -> national)
            category = 'General'
            url_match = re.search(r'banglanews24\.com/([^/]+)/', link)
            if url_match:
                url_cat = url_match.group(1)
                if url_cat not in ('rss', 'www', 'category', 'daily-sitemap'):
                    category = url_cat

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

            yield Request(
                url=link,
                callback=self.parse_article,
                meta={
                    'category': category,
                    'rss_title': unescape(title.strip()) if title else None,
                    'rss_pub_date': pub_date.isoformat() if pub_date else None,
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

            if not loc or 'banglanews24.com' not in loc:
                continue

            # Only article URLs (contain .details or numeric ID)
            if '.details' not in loc and not re.search(r'/\d+', loc):
                continue

            if loc in self._sitemap_urls_seen:
                continue
            self._sitemap_urls_seen.add(loc)

            if self.is_url_in_db(loc):
                continue

            if lastmod:
                parsed_date = self._parse_date_string(lastmod)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Extract category from URL
            category = 'General'
            url_match = re.search(r'banglanews24\.com/([^/]+)/', loc)
            if url_match:
                url_cat = url_match.group(1)
                if url_cat not in ('daily-sitemap', 'category'):
                    category = url_cat

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={'category': category},
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

        # Find article links with .details pattern
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            response.urljoin(l) for l in article_links
            if '.details' in l or re.search(r'/\d+\.details', l)
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
            next_url = f"https://www.banglanews24.com/category/{cat_slug}?page={next_page}"
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
            response.css('.news-title::text').get() or
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
            '.details-content p::text, '
            '.article-body p::text, '
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
