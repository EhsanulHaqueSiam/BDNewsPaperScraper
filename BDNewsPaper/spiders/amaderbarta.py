"""
Amader Barta Spider (Bangla)
=============================
Scrapes articles from Amader Barta (amaderbarta.com)

Features:
    - RSS feed as primary source (WordPress, full content:encoded)
    - Sitemap as secondary source
    - HTML scraping as fallback
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
from w3lib.html import remove_tags

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class AmaderBartaSpider(BaseNewsSpider):
    """
    Spider for Amader Barta (amaderbarta.com).

    Uses RSS feed as primary source with sitemap and HTML fallback.
    WordPress-based site with standard RSS structure.

    Usage:
        scrapy crawl amaderbarta
        scrapy crawl amaderbarta -a max_pages=10
    """

    name = 'amaderbarta'
    paper_name = 'Amader Barta'
    allowed_domains = ['amaderbarta.com', 'www.amaderbarta.com']
    language = 'Bangla'

    supports_api_date_filter = False
    supports_api_category_filter = False

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        self.logger.info("Amader Barta spider initialized")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: RSS feed first, then sitemap fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://amaderbarta.com/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss', 'scrapling': True},
        )

    def _rss_failed(self, failure):
        """If RSS fails, fall back to sitemap then homepage."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Trying sitemap.")
        self.stats['errors'] += 1

        self.stats['requests_made'] += 1
        yield Request(
            url='https://amaderbarta.com/sitemap.xml',
            callback=self.parse_sitemap,
            errback=self._sitemap_failed,
            meta={'scrapling': True},
        )

    def _sitemap_failed(self, failure):
        """If sitemap also fails, fall back to homepage."""
        self.logger.warning(f"Sitemap failed: {failure.value}. Falling back to homepage.")
        self.stats['errors'] += 1

        self.stats['requests_made'] += 1
        yield Request(
            url='https://amaderbarta.com/',
            callback=self.parse_homepage,
            meta={'scrapling': True},
            errback=self.handle_request_failure,
        )

    # ================================================================
    # RSS Feed Parsing (Primary Source)
    # ================================================================

    def parse_rss(self, response: Response) -> Generator:
        """Parse RSS feed XML to extract articles."""
        sel = Selector(response, type='xml')
        sel.remove_namespaces()
        items = sel.xpath('//item')

        self.logger.info(f"RSS feed: Found {len(items)} items")

        rss_yielded = 0

        for item in items:
            title = item.xpath('title/text()').get('').strip()
            link = item.xpath('link/text()').get('').strip()
            pub_date_str = item.xpath('pubDate/text()').get('').strip()
            author = item.xpath('creator/text()').get('').strip()
            body_html = item.xpath('encoded/text()').get('')
            description = item.xpath('description/text()').get('').strip()
            category = item.xpath('category/text()').get('General').strip()

            if not link:
                continue

            self._rss_urls_seen.add(link)

            if self.is_url_in_db(link):
                continue

            # Clean HTML from body
            body = ''
            if body_html:
                body = remove_tags(body_html).strip()
                # Remove "The post ... appeared first on ..." WordPress suffix
                body = re.sub(
                    r'\s*The post .+ appeared first on .+\.\s*$', '', body
                ).strip()
            elif description:
                body = remove_tags(description).strip()
                body = re.sub(
                    r'\s*The post .+ appeared first on .+\.\s*$', '', body
                ).strip()

            # Date filtering
            if pub_date_str:
                parsed_date = self._parse_rss_date(pub_date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Search query filter
            if title and body:
                if not self.filter_by_search_query(title, body):
                    continue

            if title and body and len(body) > 100:
                self.stats['articles_found'] += 1
                self.stats['articles_processed'] += 1
                rss_yielded += 1

                pub_date_iso = None
                if pub_date_str:
                    pd = self._parse_rss_date(pub_date_str)
                    if pd:
                        pub_date_iso = pd.isoformat()

                yield self.create_article_item(
                    url=link,
                    headline=unescape(title),
                    article_body=body,
                    publication_date=pub_date_iso,
                    author=author if author else None,
                    category=category,
                )
            elif title and link:
                self.stats['articles_found'] += 1
                self.stats['requests_made'] += 1
                yield Request(
                    url=link,
                    callback=self.parse_article,
                    meta={'category': category, 'scrapling': True},
                    errback=self.handle_request_failure,
                )

        self.logger.info(f"RSS: Yielded {rss_yielded} full articles from feed")

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

    # ================================================================
    # Sitemap Parsing (Secondary Source)
    # ================================================================

    def parse_sitemap(self, response: Response) -> Generator:
        """Parse sitemap XML for article URLs."""
        sel = Selector(response, type='xml')
        sel.remove_namespaces()

        # Check if this is a sitemap index
        sitemaps = sel.xpath('//sitemap/loc/text()').getall()
        if sitemaps:
            for sitemap_url in sitemaps:
                if 'post' in sitemap_url.lower() or 'news' in sitemap_url.lower():
                    self.stats['requests_made'] += 1
                    yield Request(
                        url=sitemap_url,
                        callback=self.parse_sitemap,
                        meta={'scrapling': True},
                        errback=self.handle_request_failure,
                    )
            return

        # Parse article URLs from sitemap
        urls = sel.xpath('//url/loc/text()').getall()
        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        for url in urls:
            url = url.strip()
            if not url or url in self._rss_urls_seen:
                continue
            if self.is_url_in_db(url):
                continue
            # Skip non-article pages
            if url.rstrip('/') == 'https://amaderbarta.com':
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            yield Request(
                url=url,
                callback=self.parse_article,
                meta={'category': 'Sitemap', 'scrapling': True},
                errback=self.handle_request_failure,
            )

    # ================================================================
    # HTML Scraping (Fallback)
    # ================================================================

    def parse_homepage(self, response: Response) -> Generator:
        """Parse homepage for article links."""
        article_links = self.discover_links(response, limit=50)

        self.logger.info(f"Found {len(article_links)} articles on homepage")

        for url in article_links:
            if url in self._rss_urls_seen:
                continue
            if self.is_url_in_db(url):
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_article,
                meta={'category': 'General', 'scrapling': True},
                errback=self.handle_request_failure,
            )

    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url

        # Try universal extraction first
        fallback = self.extract_article_fallback(response)
        if fallback and fallback.get('headline') and fallback.get('article_body'):
            if len(fallback.get('article_body', '')) >= 100:
                pub_date = self.parse_article_date(
                    str(fallback.get('publication_date', ''))
                ) if fallback.get('publication_date') else None
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

        # Manual extraction fallback (WordPress patterns)
        headline = (
            response.css('h1.entry-title::text').get() or
            response.css('h1.post-title::text').get() or
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return

        headline = unescape(headline.strip())

        body_parts = response.css(
            '.entry-content p::text, .post-content p::text, '
            '.article-body p::text, article p::text'
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
            response.css('.entry-date::text').get() or
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
