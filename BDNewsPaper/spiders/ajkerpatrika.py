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
        self.logger.info(f"Ajker Patrika spider initialized (hybrid API + HTML mode)")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial request to API."""
        self.stats['requests_made'] = 0
        
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
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Handle ISO format with timezone
        if 'T' in date_str:
            try:
                clean_date = date_str.replace('Z', '+00:00')
                dt = datetime.fromisoformat(clean_date)
                return dt
            except ValueError:
                pass
        
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt) if dt.tzinfo is None else dt
            except ValueError:
                continue
        
        return None
