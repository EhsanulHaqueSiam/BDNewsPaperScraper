"""
Artho Suchak Spider (Bangla)
============================
Scrapes articles from Artho Suchak (arthosuchak.com)

Features:
    - WordPress REST API support ⚡
    - Business/Economics news in Bangla
    - Date filtering (server-side via API)
    - Pagination support
"""

import json
import re
from html import unescape
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlencode

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector
from w3lib.html import remove_tags


class ArthoSuchakSpider(BaseNewsSpider):
    """
    Spider for Artho Suchak using WordPress REST API.
    
    Bangla business and economics news portal.
    
    Usage:
        scrapy crawl arthosuchak
        scrapy crawl arthosuchak -a max_pages=10
    """
    
    name = 'arthosuchak'
    paper_name = 'Artho Suchak'
    allowed_domains = ['arthosuchak.com']
    language = 'Bangla'
    
    # API capabilities
    supports_api_date_filter = True
    supports_api_category_filter = True
    
    # WordPress API base
    API_BASE = 'https://arthosuchak.com/wp-json/wp/v2'
    POSTS_PER_PAGE = 20
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 6,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        self.logger.info("Artho Suchak spider initialized (WordPress API)")
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://arthosuchak.com/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

        # Supplementary: News sitemap for date-filtered discovery
        self.stats['requests_made'] += 1
        yield Request(
            url='https://arthosuchak.com/sitemap.xml',
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

    def _generate_fallback_requests(self) -> Generator[Request, None, None]:
        """Generate initial API requests."""
        
        params = self._build_date_params()
        url = self._build_api_url(params)
        
        self.logger.info(f"Crawling posts: {url}")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=url,
            callback=self.parse_api_response,
            meta={'category': 'Business', 'page': 1, 'params': params},
            errback=self.handle_request_failure,
        )
    
    def _build_date_params(self) -> Dict[str, Any]:
        """Build API parameters with date filters."""
        params = {
            'per_page': self.POSTS_PER_PAGE,
            'page': 1,
            '_embed': 1,
        }
        
        if self.start_date:
            params['after'] = self.start_date.strftime('%Y-%m-%dT%H:%M:%S')
        if self.end_date:
            params['before'] = self.end_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        return params
    
    def _build_api_url(self, params: Dict[str, Any]) -> str:
        """Build the API URL with query parameters."""
        query = urlencode(params)
        return f"{self.API_BASE}/posts?{query}"
    
    def parse_api_response(self, response: Response) -> Generator:
        """Parse WordPress REST API response."""
        category = response.meta.get('category', 'Business')
        page = response.meta.get('page', 1)
        params = response.meta.get('params', {})
        
        try:
            posts = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse API response: {response.url}")
            return
        
        if not posts:
            self.logger.info(f"No more posts at page {page}")
            return
        
        self.logger.info(f"Found {len(posts)} posts in page {page}")
        
        for post in posts:
            article = self._parse_post(post, category)
            if article:
                yield article
        
        # Pagination
        if len(posts) >= self.POSTS_PER_PAGE and page < self.max_pages:
            next_params = params.copy()
            next_params['page'] = page + 1
            next_url = self._build_api_url(next_params)
            
            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={'category': category, 'page': page + 1, 'params': next_params},
                errback=self.handle_request_failure,
            )
    
    def _parse_post(self, post: Dict[str, Any], category: str) -> Optional[NewsArticleItem]:
        """Parse a single post from API response."""
        try:
            url = post.get('link', '')
            if not url or self.is_url_in_db(url):
                return None
            
            self.stats['articles_found'] += 1
            
            # Extract headline
            title_data = post.get('title', {})
            headline = title_data.get('rendered', '') if isinstance(title_data, dict) else str(title_data)
            headline = self._clean_html(headline)
            
            if not headline:
                return None
            
            # Extract body
            content_data = post.get('content', {})
            content = content_data.get('rendered', '') if isinstance(content_data, dict) else str(content_data)
            article_body = self._clean_html(content)
            
            if len(article_body) < 100:
                return None
            
            if not self.filter_by_search_query(headline, article_body):
                return None
            
            # Parse date
            pub_date = None
            date_str = post.get('date_gmt') or post.get('date')
            if date_str:
                pub_date = self._parse_date_string(date_str)
            
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                return None
            
            # Extract image
            image_url = None
            embedded = post.get('_embedded', {})
            featured_media = embedded.get('wp:featuredmedia', [])
            if featured_media:
                image_url = featured_media[0].get('source_url')
            
            # Extract author
            author = None
            authors = embedded.get('author', [])
            if authors:
                author = authors[0].get('name')
            
            self.stats['articles_processed'] += 1
            
            return self.create_article_item(
                url=url,
                headline=headline,
                article_body=article_body,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=category,
                author=author,
                image_url=image_url,
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing post: {e}")
            self.stats['errors'] += 1
            return None
    

    def parse_article(self, response):
        """Parse individual article page (fallback for RSS/sitemap items without full body)."""
        item = self.parse_article_auto(response)
        if item:
            item['category'] = response.meta.get('category', 'General')
            self.stats['articles_processed'] += 1
            yield item

    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean up content."""
        if not html_content:
            return ''
        
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = unescape(text)
        try:
            text = text.encode().decode('unicode-escape')
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        text = re.sub(r'\s+', ' ', text).strip()
        return text

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

