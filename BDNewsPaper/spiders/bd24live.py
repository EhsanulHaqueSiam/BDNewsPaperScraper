"""
BD24Live Spider (English)
=========================
Scrapes articles from BD24Live (bd24live.com)

Features:
    - RSS feed as primary source (~10 items, WordPress)
    - Category-based HTML scraping as fallback
    - Date filtering (client-side)
    - English news portal
"""

from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response
from scrapy.selector import Selector
from w3lib.html import remove_tags

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class BD24LiveSpider(BaseNewsSpider):
    """
    Spider for BD24Live (English News Portal).

    Uses RSS feed as primary source, with HTML scraping fallback.

    Usage:
        scrapy crawl bd24live -a categories=national,politics
        scrapy crawl bd24live -a max_pages=10
    """

    name = 'bd24live'
    paper_name = 'BD24Live'
    allowed_domains = ['bd24live.com', 'www.bd24live.com']
    language = 'English'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'world': 'worldnews',
        'international': 'worldnews',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'education': 'education',
        'business': 'business',
        'technology': 'technology',
        'science': 'science',
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
        self._rss_urls_seen = set()
        self.logger.info("BD24Live spider initialized")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests: RSS feed first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed (WordPress, ~10 items, fresh)
        self.stats['requests_made'] += 1
        yield Request(
            url='https://bd24live.com/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

    def _rss_failed(self, failure):
        """If RSS fails, fall back to category-based HTML scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to category scraping.")
        self.stats['errors'] += 1
        yield from self._generate_category_requests()

    def _generate_category_requests(self) -> Generator[Request, None, None]:
        """Generate requests for category pages (fallback mode)."""
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                url = f"https://www.bd24live.com/category/{cat_slug}/"
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Default categories
            for cat in ['national', 'worldnews', 'sports', 'entertainment']:
                url = f"https://www.bd24live.com/category/{cat}/"
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_slug': cat, 'page': 1},
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
                    meta={'category': category},
                    errback=self.handle_request_failure,
                )

        self.logger.info(f"RSS: Yielded {rss_yielded} full articles from feed")

        # RSS has only ~10 items, supplement with category scraping
        yield from self._generate_category_requests()

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

    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)

        # Extract article links
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            l for l in article_links
            if 'bd24live.com/' in l
            and '/category/' not in l
            and l.endswith('/')
            and len(l.split('/')) > 4  # Filter main domain and category pages
        ]
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
            if not url.startswith('http'):
                url = f"https://www.bd24live.com{url}"

            if url in self._rss_urls_seen:
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
            next_page_link = response.css('a.next::attr(href), a[rel="next"]::attr(href)').get()
            if next_page_link:
                if not next_page_link.startswith('http'):
                    next_page_link = f"https://www.bd24live.com{next_page_link}"

                self.stats['requests_made'] += 1
                yield Request(
                    url=next_page_link,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': page + 1},
                    errback=self.handle_request_failure,
                )

    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url

        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )

        if not headline:
            return

        headline = unescape(headline.strip())

        # Extract body
        body_parts = response.css(
            'article p::text, '
            '.entry-content p::text, '
            '.post-content p::text, '
            '.article-content p::text'
        ).getall()

        if not body_parts:
            body_parts = response.css('p::text').getall()

        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())

        if len(article_body) < 100:
            return

        # Search filter
        if not self.filter_by_search_query(headline, article_body):
            return

        # Parse date
        pub_date = None
        date_text = response.css('meta[property="article:published_time"]::attr(content)').get()
        if not date_text:
            date_text = response.css('time::attr(datetime)').get()

        if date_text:
            pub_date = self._parse_date_string(date_text.strip())

        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return

        category = response.meta.get('category', 'General')
        image_url = response.css('meta[property="og:image"]::attr(content)').get()

        # Extract author
        author = self.extract_author(response)

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
