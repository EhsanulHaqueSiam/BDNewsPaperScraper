"""
MyTV Spider (Bangla)
====================
Scrapes articles from MyTV (mytvbd.tv)

Features:
    - RSS feed as primary source (full article content)
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
from w3lib.html import remove_tags

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class MyTVSpider(BaseNewsSpider):
    """
    Spider for MyTV (mytvbd.tv).

    Uses RSS feed as primary source, with HTML scraping fallback.

    Usage:
        scrapy crawl mytvbd
        scrapy crawl mytvbd -a categories=national,sports
        scrapy crawl mytvbd -a max_pages=10
    """

    name = 'mytvbd'
    paper_name = 'MyTV'
    allowed_domains = ['mytvbd.tv', 'www.mytvbd.tv']
    language = 'Bangla'

    supports_api_date_filter = False
    supports_api_category_filter = True

    CATEGORIES = {
        'national': 'জাতীয়',
        'politics': 'রাজনীতি',
        'international': 'আন্তর্জাতিক',
        'sports': 'খেলাধুলা',
        'entertainment': 'বিনোদন',
        'economy': 'অর্থনীতি',
        'country': 'সারাদেশ',
        'religion': 'ধর্ম',
        'jobs': 'চাকুরী',
    }

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        self.logger.info("MyTV spider initialized")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: RSS feed first, then HTML fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://mytvbd.tv/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss', 'scrapling': True},
        )

    def _rss_failed(self, failure):
        """If RSS fails, fall back to homepage scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to HTML scraping.")
        self.stats['errors'] += 1
        yield from self._generate_homepage_requests()

    def _generate_homepage_requests(self) -> Generator[Request, None, None]:
        """Generate requests for homepage (fallback mode)."""
        self.stats['requests_made'] += 1
        yield Request(
            url='https://mytvbd.tv/',
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
            elif description:
                body = remove_tags(description).strip()

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
                # Full article available from RSS
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
                # RSS item lacks full body -- visit article page
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
    # HTML Scraping (Fallback)
    # ================================================================

    def parse_homepage(self, response: Response) -> Generator:
        """Parse homepage for article links."""
        article_links = response.css('a::attr(href)').getall()

        # Filter to article links (numeric ID pattern: mytvbd.tv/NNNN)
        article_links = [
            response.urljoin(l) for l in article_links
            if re.search(r'/\d+$', l) and 'mytvbd.tv' in response.urljoin(l)
        ]

        # Deduplicate
        article_links = list(set(article_links))

        if not article_links:
            self.logger.info("CSS selectors failed, using universal link discovery")
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

        # Manual extraction fallback
        headline = (
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return

        headline = unescape(headline.strip())

        body_parts = response.css('article p::text, .content p::text, .news-content p::text').getall()
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
