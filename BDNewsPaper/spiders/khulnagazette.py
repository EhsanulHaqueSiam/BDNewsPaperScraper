"""
Khulna Gazette Spider (Bangla)
==============================
Scrapes articles from Khulna Gazette (khulnagazette.com)

Features:
    - WordPress REST API support ⚡
    - Regional news from Khulna division
    - Date filtering (server-side via API)
    - Pagination support
"""

import json
import re
from datetime import datetime
from html import unescape
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlencode

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class KhulnaGazetteSpider(BaseNewsSpider):
    """
    Spider for Khulna Gazette using WordPress REST API.
    
    Regional Bangla news from Khulna division.
    
    Usage:
        scrapy crawl khulnagazette
        scrapy crawl khulnagazette -a max_pages=10
    """
    
    name = 'khulnagazette'
    paper_name = 'Khulna Gazette'
    allowed_domains = ['khulnagazette.com']
    language = 'Bangla'
    
    # API capabilities
    supports_api_date_filter = True
    supports_api_category_filter = True
    
    # WordPress API base
    API_BASE = 'https://khulnagazette.com/wp-json/wp/v2'
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
        self.logger.info("Khulna Gazette spider initialized (WordPress API)")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial API requests."""
        self.stats['requests_made'] = 0
        
        params = self._build_date_params()
        url = self._build_api_url(params)
        
        self.logger.info(f"Crawling posts: {url}")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=url,
            callback=self.parse_api_response,
            meta={'category': 'General', 'page': 1, 'params': params},
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
        category = response.meta.get('category', 'General')
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
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse WordPress date format."""
        if not date_str:
            return None
        
        formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.split('+')[0].split('Z')[0], fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
