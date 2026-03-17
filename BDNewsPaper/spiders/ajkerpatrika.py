"""
Ajker Patrika Spider (Bangla) - Hybrid API + HTML
==================================================
Scrapes articles from Ajker Patrika (ajkerpatrika.com) - Popular Bangla News Portal

Features:
    - API-based article discovery (api.ajkerpatrika.com)
    - HTML scraping for full article content
    - Pagination support
    - Date filtering
"""

import json
import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector
from w3lib.html import remove_tags


class AjkerPatrikaSpider(BaseNewsSpider):
    """
    Spider for Ajker Patrika (Popular Bangla News Portal).
    
    Uses a hybrid approach:
    - API for article discovery (api.ajkerpatrika.com/api/v2/home)
    - HTML scraping for full article content
    
    Usage:
        scrapy crawl ajkerpatrika
        scrapy crawl ajkerpatrika -a max_pages=10
    """
    
    name = 'ajkerpatrika'
    paper_name = 'Ajker Patrika'
    allowed_domains = ['ajkerpatrika.com', 'api.ajkerpatrika.com', 'www.ajkerpatrika.com']
    language = 'Bangla'
    
    # API endpoints
    API_BASE = 'https://api.ajkerpatrika.com/api/v2'
    HOME_API = f'{API_BASE}/home'
    SITE_BASE = 'https://www.ajkerpatrika.com'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = False  # API returns mixed categories
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.4,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 6,
        'AUTOTHROTTLE_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json, text/html',
            'Accept-Language': 'bn,en;q=0.9',
        },
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        self.logger.info(f"Ajker Patrika spider initialized (hybrid API + HTML mode)")
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.ajkerpatrika.com/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

        # Supplementary: News sitemap for date-filtered discovery
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.ajkerpatrika.com/news-sitemap.xml',
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

    def _generate_fallback_requests(self) -> Generator[Request, None, None]:
        """Generate initial request to API."""
        
        self.logger.info(f"Fetching articles from API: {self.HOME_API}")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=self.HOME_API,
            callback=self.parse_api,
            meta={'page': 1},
            errback=self.handle_request_failure,
        )
    
    def parse_api(self, response: Response) -> Generator:
        """Parse API response for article list."""
        page = response.meta.get('page', 1)
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse API JSON: {e}")
            return
        
        results = data.get('results', [])
        next_url = data.get('next')
        
        self.logger.info(f"API page {page}: found {len(results)} articles")
        
        if not results:
            self.logger.info("No more articles from API")
            return
        
        for article in results:
            news_slug = article.get('news_slug', '')
            if not news_slug:
                continue
            
            # Build article URL
            # Pattern: /{category}/{subcategory}/{slug} or /{category}/{slug}
            categories = article.get('categories', [])
            subcategories = article.get('subcategories', [])
            
            if subcategories:
                cat_slug = subcategories[0].get('slug', 'news')
            elif categories:
                cat_slug = categories[0].get('slug', 'news')
            else:
                cat_slug = 'news'
            
            article_url = f"{self.SITE_BASE}/{cat_slug}/{news_slug}"
            
            if self.is_url_in_db(article_url):
                continue
            
            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            
            # Store metadata from API for use in article parsing
            meta = {
                'api_id': article.get('id'),
                'api_title': article.get('title', ''),
                'api_excerpt': article.get('excerpt', ''),
                'category': categories[0].get('name', '') if categories else 'General',
                'image_url': self._extract_image_url(article),
                'tags': [t.get('name', '') for t in article.get('tags', []) if t.get('name')],
            }
            
            yield Request(
                url=article_url,
                callback=self.parse_article,
                meta=meta,
                errback=self.handle_request_failure,
            )
        
        # Pagination - request next page if available
        if next_url and page < self.max_pages:
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_api,
                meta={'page': page + 1},
                errback=self.handle_request_failure,
            )
    

    # ================================================================
    # RSS Feed Parsing (Primary Source)
    # ================================================================

    def parse_rss(self, response):
        """Parse RSS feed XML to extract articles."""
        sel = Selector(response)
        sel.remove_namespaces()
        items = sel.xpath('//item')

        self.logger.info(f"RSS feed: Found {len(items)} items")

        rss_yielded = 0

        for item in items:
            headline = item.xpath('title/text()').get('').strip()
            url = item.xpath('link/text()').get('').strip()
            pub_date_str = item.xpath('pubDate/text()').get('').strip()
            author = item.xpath('creator/text()').get('').strip()
            body_html = item.xpath('encoded/text()').get('')
            description = item.xpath('description/text()').get('').strip()
            category = item.xpath('category/text()').get('General').strip()

            if not url:
                continue

            self._rss_urls_seen.add(url)

            if self.is_url_in_db(url):
                continue

            # Clean HTML from body
            body = ''
            if body_html:
                body = remove_tags(body_html).strip()

            # Date filtering
            if pub_date_str:
                parsed_date = self._parse_date_string(pub_date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Search query filter
            if headline and body:
                if not self.filter_by_search_query(headline, body):
                    continue

            if headline and body and len(body) > 100:
                # Full article available from RSS
                self.stats['articles_found'] += 1
                self.stats['articles_processed'] += 1
                rss_yielded += 1

                yield self.create_article_item(
                    url=url,
                    headline=unescape(headline),
                    article_body=body,
                    publication_date=pub_date_str if pub_date_str else None,
                    author=author if author else None,
                    category=category,
                )
            elif headline and url:
                # RSS item lacks full body -- visit article page
                self.stats['articles_found'] += 1
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_article,
                    meta={'category': category},
                    errback=self.handle_request_failure,
                )

        self.logger.info(f"RSS feed: Yielded {rss_yielded} complete articles directly")

        # If RSS returned few items, also launch category fallback
        if len(items) < 5:
            self.logger.info("RSS returned few items, launching category fallback")
            yield from self._generate_fallback_requests()

    def _rss_failed(self, failure):
        """If RSS fails, fall back to existing scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to category scraping.")
        self.stats['errors'] += 1
        yield from self._generate_fallback_requests()


    # ================================================================
    # Sitemap Parsing (Supplementary Source)
    # ================================================================

    def parse_sitemap(self, response):
        """Parse news sitemap XML for date-filtered article discovery."""
        sel = Selector(response)
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            lastmod = url_node.xpath('lastmod/text()').get('').strip()
            pub_date = url_node.xpath('news/publication_date/text()').get('').strip()

            if not loc:
                continue

            # Skip if already seen via RSS
            if hasattr(self, '_rss_urls_seen') and loc in self._rss_urls_seen:
                continue

            if self.is_url_in_db(loc):
                continue

            # Date filter on lastmod or pub_date
            date_str = pub_date or lastmod
            if date_str:
                parsed_date = self._parse_date_string(date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            sitemap_count += 1

            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={'category': 'General'},
                errback=self.handle_request_failure,
            )

        self.logger.info(f"Sitemap: Queued {sitemap_count} articles for scraping")

    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse article page for full content."""
        url = response.url
        
        # Get headline - prefer API data, fallback to HTML
        headline = response.meta.get('api_title', '')
        if not headline:
            headline = (
                response.css('meta[property="og:title"]::attr(content)').get() or
                response.css('h1::text').get() or
                ''
            )
        
        if not headline:
            self.logger.warning(f"No headline for article: {url}")
            return
        
        headline = unescape(headline.strip())
        # Clean headline - remove site suffix
        headline = re.sub(r'\s*\|\s*Ajker Patrika\s*$', '', headline, flags=re.IGNORECASE).strip()
        
        # Extract article body from HTML
        body_parts = response.css('article p::text, .article-content p::text, .story-body p::text').getall()
        
        if not body_parts:
            body_parts = response.css('.content p::text, p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        # Use excerpt if body too short
        if len(article_body) < 100:
            excerpt = response.meta.get('api_excerpt', '')
            if excerpt:
                article_body = excerpt
        
        if len(article_body) < 50:
            self.logger.debug(f"Article too short: {url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date
        pub_date = None
        date_text = (
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            response.css('.date::text').get() or
            response.css('time::attr(datetime)').get() or
            ''
        )
        
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Extract category from meta or HTML
        category = response.meta.get('category', 'General')
        
        # Extract image from API meta
        image_url = response.meta.get('image_url')
        if not image_url:
            image_url = response.css('meta[property="og:image"]::attr(content)').get()
        
        # Extract author
        author = self.extract_author(response)
        
        # Tags from API
        tags = response.meta.get('tags', [])
        keywords = ', '.join(tags) if tags else None
        
        self.stats['articles_processed'] += 1
        
        yield self.create_article_item(
            url=url,
            headline=headline,
            article_body=article_body,
            publication_date=pub_date.isoformat() if pub_date else None,
            category=category,
            author=author,
            image_url=image_url,
            keywords=keywords,
        )
    
    def _extract_image_url(self, article: dict) -> Optional[str]:
        """Extract image URL from API article data."""
        blog_image = article.get('blog_image', {})
        if blog_image and isinstance(blog_image, dict):
            return blog_image.get('download_url')
        return None
