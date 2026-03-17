"""
Bangladesh Journal Spider (Bangla)
===================================
Scrapes articles from Bangladesh Journal (bdjournalism.com)

Features:
    - HTML scraping (site currently unreachable; spider ready for when it returns)
    - Universal fallback extraction (JSON-LD, generic selectors)
    - Date filtering (client-side)
    - Search query filtering

Note:
    As of 2026-03, bdjournalism.com is unreachable (ECONNREFUSED).
    This spider is prepared for when the site comes back online.
"""

import re
from html import unescape
from typing import Generator

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class BDJournalismSpider(BaseNewsSpider):
    """
    Spider for Bangladesh Journal (bdjournalism.com).

    Uses HTML scraping with universal fallback extraction.
    Will attempt RSS feed first, then homepage scraping.

    Usage:
        scrapy crawl bdjournalism
        scrapy crawl bdjournalism -a max_pages=10
    """

    name = 'bdjournalism'
    paper_name = 'Bangladesh Journal'
    allowed_domains = ['bdjournalism.com', 'www.bdjournalism.com']
    language = 'Bangla'

    supports_api_date_filter = False
    supports_api_category_filter = False

    CATEGORIES = {
        'national': 'national',
        'politics': 'politics',
        'international': 'international',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'economy': 'economy',
    }

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Bangladesh Journal spider initialized")

    def start_requests(self) -> Generator[Request, None, None]:
        """Try RSS feed first, then fall back to homepage."""
        self.stats['requests_made'] = 0

        # Try RSS feed first (common WordPress endpoint)
        self.stats['requests_made'] += 1
        yield Request(
            url='https://bdjournalism.com/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss', 'scrapling': True},
        )

    def _rss_failed(self, failure):
        """If RSS fails, fall back to homepage scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to HTML scraping.")
        self.stats['errors'] += 1

        self.stats['requests_made'] += 1
        yield Request(
            url='https://bdjournalism.com/',
            callback=self.parse_homepage,
            meta={'scrapling': True},
            errback=self.handle_request_failure,
        )

    # ================================================================
    # RSS Feed Parsing
    # ================================================================

    def parse_rss(self, response: Response) -> Generator:
        """Parse RSS feed if available."""
        from datetime import datetime
        from scrapy.selector import Selector
        from w3lib.html import remove_tags

        sel = Selector(response, type='xml')
        sel.remove_namespaces()
        items = sel.xpath('//item')

        self.logger.info(f"RSS feed: Found {len(items)} items")

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

            if self.is_url_in_db(link):
                continue

            body = ''
            if body_html:
                body = remove_tags(body_html).strip()
            elif description:
                body = remove_tags(description).strip()

            if pub_date_str:
                parsed_date = self._parse_date_string(pub_date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            if title and body:
                if not self.filter_by_search_query(title, body):
                    continue

            if title and body and len(body) > 100:
                self.stats['articles_found'] += 1
                self.stats['articles_processed'] += 1

                pub_date_iso = None
                if pub_date_str:
                    pd = self._parse_date_string(pub_date_str)
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

    # ================================================================
    # HTML Scraping (Fallback)
    # ================================================================

    def parse_homepage(self, response: Response) -> Generator:
        """Parse homepage for article links."""
        article_links = self.discover_links(response, limit=50)

        self.logger.info(f"Found {len(article_links)} articles on homepage")

        for url in article_links:
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

        # Manual extraction fallback
        headline = (
            response.css('h1.entry-title::text').get() or
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
            '.article-content p::text, article p::text'
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
