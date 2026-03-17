"""
Rising BD Spider (Bangla)
=========================
Scrapes articles from Rising BD (risingbd.com)

Features:
    - RSS feed for article URL discovery (primary)
    - Category-based HTML scraping (fallback)
    - Date filtering (client-side)
    - Search query filtering
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response
from w3lib.html import remove_tags

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class RisingBDSpider(BaseNewsSpider):
    """
    Spider for Rising BD (Bangla Newspaper).

    Primary: RSS feed for article URL discovery, then visits pages for full content.
    Fallback: HTML scraping with category navigation.

    Usage:
        scrapy crawl risingbd -a categories=national,politics,sports
        scrapy crawl risingbd -a max_pages=10
        scrapy crawl risingbd -a start_date=2024-01-01
    """

    name = 'risingbd'
    paper_name = 'Rising BD'
    allowed_domains = ['risingbd.com', 'www.risingbd.com']
    language = 'Bangla'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # RSS feed URL
    RSS_URL = 'https://www.risingbd.com/rss/rss.xml'

    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'business': 'economy',
        'economy': 'economy',
        'tech': 'tech',
        'technology': 'tech',
        'lifestyle': 'lifestyle',
        'health': 'health',
        'education': 'campus',
        'campus': 'campus',
        'crime': 'crime',
        'travel': 'travel',
        'probash': 'probash',
    }

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Rising BD spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate requests: RSS feed first, then category pages."""
        self.stats['requests_made'] = 0

        # Always fetch the RSS feed for broad article discovery
        self.logger.info(f"Fetching RSS feed: {self.RSS_URL}")
        self.stats['requests_made'] += 1
        yield Request(
            url=self.RSS_URL,
            callback=self.parse_rss,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            },
            errback=self.handle_request_failure,
        )

        # Also crawl category pages for additional coverage
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()

                if cat_lower in self.CATEGORIES:
                    cat_slug = self.CATEGORIES[cat_lower]
                else:
                    cat_slug = cat_lower

                url = f"https://www.risingbd.com/{cat_slug}"

                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1

                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl default categories as supplement
            default_cats = ['national', 'politics', 'sports', 'economy']
            for cat in default_cats:
                cat_slug = self.CATEGORIES.get(cat, cat)
                url = f"https://www.risingbd.com/{cat_slug}"

                self.logger.info(f"Crawling category: {cat} -> {url}")
                self.stats['requests_made'] += 1

                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )

    # ================================================================
    # RSS Parsing (Primary URL discovery)
    # ================================================================

    def parse_rss(self, response: Response) -> Generator:
        """Parse RSS feed to discover article URLs, then visit each for full content."""
        # Use scrapy.Selector to parse RSS XML with namespace removal
        selector = scrapy.Selector(response, type='xml')
        selector.remove_namespaces()

        items = selector.xpath('//item')

        if not items:
            self.logger.warning(f"No items found in RSS feed: {response.url}")
            return

        self.logger.info(f"Found {len(items)} items in RSS feed: {response.url}")

        for item in items:
            link = item.xpath('link/text()').get()
            if not link:
                continue

            link = link.strip()

            # Ensure full URL
            if link.startswith('/'):
                link = f"https://www.risingbd.com{link}"

            # Skip if already in DB
            if self.is_url_in_db(link):
                continue

            # Get title and pub date from RSS for pre-filtering
            title = item.xpath('title/text()').get()
            title = unescape(title.strip()) if title else ''

            pub_date_str = item.xpath('pubDate/text()').get()
            pub_date = self._parse_rss_date(pub_date_str)

            # Date filter
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                continue

            # Extract category from URL path
            category = 'General'
            url_match = re.search(r'risingbd\.com/([^/]+)', link)
            if url_match:
                url_category = url_match.group(1)
                if url_category not in ('rss', 'www', 'news'):
                    category = url_category

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            # Visit article page for full content
            yield Request(
                url=link,
                callback=self.parse_article,
                meta={
                    'category': category,
                    'rss_title': title,
                    'rss_pub_date': pub_date,
                },
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'bn,en;q=0.9',
                },
                errback=self.handle_request_failure,
            )

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS pubDate format (RFC 822)."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # RFC 822 formats commonly used in RSS
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',    # Mon, 17 Mar 2026 10:30:00 +0600
            '%a, %d %b %Y %H:%M:%S %Z',     # Mon, 17 Mar 2026 10:30:00 GMT
            '%d %b %Y %H:%M:%S %z',          # 17 Mar 2026 10:30:00 +0600
            '%Y-%m-%dT%H:%M:%S%z',           # 2026-03-17T10:30:00+06:00
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback to base spider's date parser
        return self._parse_date_string(date_str)
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)
        
        # Find article links with numeric IDs
        article_links = response.css('a::attr(href)').getall()
        
        # Filter to article links (contain risingbd.com and numeric IDs)
        article_links = [l for l in article_links if 'risingbd.com' in l and re.search(r'/\d+$', l)]
        
        # Deduplicate
        article_links = list(set(article_links))
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail
        if not article_links:
            self.logger.info(f"CSS selectors failed, using universal link discovery for {category}")
            article_links = self.discover_links(response, limit=50)
        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
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
            next_url = f"https://www.risingbd.com/{cat_slug}?page={next_page}"
            
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
        
        # Original CSS selector approach (fallback)
        headline = (
            response.css('h1::text').get() or
            response.css('h1.title::text').get() or
            response.css('.news-title::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return
        
        headline = unescape(headline.strip())
        
        body_parts = response.css('.news-content p::text, .content p::text, article p::text').getall()
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date
        pub_date = None
        date_text = (
            response.css('.date::text').get() or
            response.css('.time::text').get() or
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            ''
        )
        
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Extract author
        author = self.extract_author(response)
        
        # Extract category
        category = response.meta.get('category', 'General')
        
        # Extract image
        image_url = (
            response.css('.news-image img::attr(src)').get() or
            response.css('article img::attr(src)').get() or
            response.css('meta[property="og:image"]::attr(content)').get()
        )
        
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
