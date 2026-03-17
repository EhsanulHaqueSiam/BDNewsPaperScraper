"""
Jago News 24 Spider (Bangla)
============================
Scrapes articles from Jago News 24 (jagonews24.com)

Features:
    - RSS feed-based scraping (primary) with full article body from content:encoded
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


class JagoNews24Spider(BaseNewsSpider):
    """
    Spider for Jago News 24 (Bangla Newspaper).

    Primary: RSS feeds with full article body in content:encoded.
    Fallback: HTML scraping with category navigation.

    Usage:
        scrapy crawl jagonews24 -a categories=national,politics,sports
        scrapy crawl jagonews24 -a max_pages=10
        scrapy crawl jagonews24 -a start_date=2024-01-01
    """

    name = 'jagonews24'
    paper_name = 'Jago News 24'
    allowed_domains = ['jagonews24.com', 'www.jagonews24.com']
    language = 'Bangla'

    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True

    # RSS feed URLs
    RSS_FEEDS = {
        'main': 'https://www.jagonews24.com/rss/rss.xml',
        'national': 'https://www.jagonews24.com/rss/national.xml',
        'politics': 'https://www.jagonews24.com/rss/politics.xml',
        'sports': 'https://www.jagonews24.com/rss/sports.xml',
        'entertainment': 'https://www.jagonews24.com/rss/entertainment.xml',
        'economy': 'https://www.jagonews24.com/rss/economy.xml',
    }

    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'cricket': 'sports/cricket',
        'football': 'sports/football',
        'entertainment': 'entertainment',
        'bollywood': 'entertainment/bollywood',
        'hollywood': 'entertainment/hollywood',
        'business': 'economy',
        'economy': 'economy',
        'tech': 'technology',
        'technology': 'technology',
        'lifestyle': 'lifestyle',
        'health': 'health',
        'education': 'education',
        'religion': 'religion',
        'opinion': 'opinion',
        'probash': 'probash',
        'country': 'country',
    }

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Jago News 24 spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to RSS feeds (primary) with HTML fallback."""
        self.stats['requests_made'] = 0

        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()

                # Try RSS feed first if available for this category
                if cat_lower in self.RSS_FEEDS:
                    rss_url = self.RSS_FEEDS[cat_lower]
                    self.logger.info(f"Fetching RSS for category: {category} -> {rss_url}")
                    self.stats['requests_made'] += 1
                    yield Request(
                        url=rss_url,
                        callback=self.parse_rss,
                        meta={'category': category},
                        errback=self.handle_request_failure,
                    )
                else:
                    # Fall back to HTML category page
                    cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                    url = f"https://www.jagonews24.com/{cat_slug}"
                    self.logger.info(f"Crawling category (HTML): {category} -> {url}")
                    self.stats['requests_made'] += 1
                    yield Request(
                        url=url,
                        callback=self.parse_category,
                        meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                        errback=self.handle_request_failure,
                    )
        else:
            # Default: fetch all RSS feeds for broad coverage
            for feed_name, rss_url in self.RSS_FEEDS.items():
                self.logger.info(f"Fetching RSS feed: {feed_name} -> {rss_url}")
                self.stats['requests_made'] += 1
                yield Request(
                    url=rss_url,
                    callback=self.parse_rss,
                    meta={'category': feed_name},
                    errback=self.handle_request_failure,
                )

    # ================================================================
    # RSS Parsing (Primary)
    # ================================================================

    def parse_rss(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse RSS feed and create items directly from content:encoded."""
        rss_category = response.meta.get('category', 'General')

        # Use scrapy.Selector to parse RSS XML with namespace removal
        selector = scrapy.Selector(response, type='xml')
        selector.remove_namespaces()

        items = selector.xpath('//item')

        if not items:
            self.logger.warning(f"No items found in RSS feed: {response.url}")
            return

        self.logger.info(f"Found {len(items)} items in RSS feed: {response.url}")

        for item in items:
            # Extract fields from RSS item
            title = item.xpath('title/text()').get()
            link = item.xpath('link/text()').get()
            pub_date_str = item.xpath('pubDate/text()').get()
            content_encoded = item.xpath('encoded/text()').get()
            description = item.xpath('description/text()').get()

            if not link:
                continue

            link = link.strip()

            # Skip if already in DB
            if self.is_url_in_db(link):
                continue

            # Clean title
            title = unescape(title.strip()) if title else ''
            if not title:
                continue

            # Parse publication date
            pub_date = self._parse_rss_date(pub_date_str)

            # Date filter
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                continue

            # Extract article body from content:encoded (full HTML body)
            article_body = ''
            if content_encoded:
                article_body = remove_tags(content_encoded).strip()
                # Normalize whitespace
                article_body = re.sub(r'\s+', ' ', article_body).strip()

            # Fall back to description if content:encoded is empty
            if not article_body and description:
                article_body = remove_tags(description).strip()
                article_body = re.sub(r'\s+', ' ', article_body).strip()

            if len(article_body) < 100:
                self.logger.debug(f"RSS article too short, skipping: {link}")
                continue

            # Search query filter
            if not self.filter_by_search_query(title, article_body):
                continue

            # Extract category from URL path (e.g., /sports/cricket/1102896 -> sports)
            category = rss_category
            url_match = re.search(r'jagonews24\.com/([^/]+)', link)
            if url_match:
                url_category = url_match.group(1)
                if url_category not in ('rss', 'www'):
                    category = url_category

            # Extract image from content:encoded HTML
            image_url = None
            if content_encoded:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_encoded)
                if img_match:
                    image_url = img_match.group(1)

            self.stats['articles_found'] += 1
            self.stats['articles_processed'] += 1

            yield self.create_article_item(
                url=link,
                headline=title,
                article_body=article_body,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=category,
                image_url=image_url,
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
        
        # Filter to only article links (contain /national/, /politics/, etc. with ID)
        article_links = [l for l in article_links if re.search(r'/\d+$', l) and 'jagonews24.com' in l]
        
        # Deduplicate
        article_links = list(set(article_links))
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not article_links:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
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
        
        # Pagination - use archive page with date or page parameter
        if found_count > 0 and page < self.max_pages:
            next_page = page + 1
            next_url = f"https://www.jagonews24.com/{cat_slug}?page={next_page}"
            
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
        
        # Original extraction
        
        # Extract headline
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
        
        # Extract article body
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
        if not author:
            author_text = response.css('.author::text, .byline::text, .reporter::text').get()
            if author_text:
                author = author_text.strip()
        
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
