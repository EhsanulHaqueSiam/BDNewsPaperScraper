"""
Somoyer TV Spider (Bangla)
==========================
Scrapes articles from Somoyer TV (somoyertv.com) using WordPress REST API

Features:
    - 24-hour live TV news portal
    - WordPress REST API
    - Server-side date filtering
"""

import json
import re
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, Generator, List, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class SomoyerTVSpider(BaseNewsSpider):
    """
    Spider for Somoyer TV (24 Hours Live TV News).
    
    Uses WordPress REST API for efficient scraping.
    
    Usage:
        scrapy crawl somoyertv
        scrapy crawl somoyertv -a from_date=2024-01-01
    """
    
    name = 'somoyertv'
    paper_name = 'Somoyer TV'
    allowed_domains = ['somoyertv.com']
    language = 'Bangla'
    
    # API capabilities
    supports_api_date_filter = True
    supports_api_category_filter = True
    
    # API endpoints
    API_BASE = 'https://somoyertv.com/wp-json/wp/v2'
    POSTS_ENDPOINT = f'{API_BASE}/posts'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Somoyer TV spider initialized (WordPress API)")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial API requests."""
        self.stats['requests_made'] = 0
        
        params = ['per_page=20', 'page=1', '_embed=1']
        
        # Add date range if specified
        if self.from_date:
            after_date = self.from_date.strftime('%Y-%m-%dT00:00:00')
            params.append(f'after={after_date}')
        
        if self.to_date:
            before_date = (self.to_date + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00')
            params.append(f'before={before_date}')
        
        url = f"{self.POSTS_ENDPOINT}?{'&'.join(params)}"
        
        self.logger.info(f"Starting API request: {url}")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=url,
            callback=self.parse_api_response,
            meta={'page': 1},
            errback=self.handle_request_failure,
        )
    
    def parse_api_response(self, response: Response) -> Generator:
        """Parse WordPress REST API response."""
        page = response.meta.get('page', 1)
        
        try:
            posts = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse API response as JSON")
            return
        
        if not posts:
            self.logger.info(f"No more posts found on page {page}")
            return
        
        self.logger.info(f"Processing {len(posts)} posts from page {page}")
        
        for post in posts:
            item = self._parse_post(post)
            if item:
                yield item
        
        # Pagination
        total_pages = int(response.headers.get('X-WP-TotalPages', 1))
        if page < min(total_pages, self.max_pages):
            next_page = page + 1
            next_url = re.sub(r'page=\d+', f'page={next_page}', response.url)
            
            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={'page': next_page},
                errback=self.handle_request_failure,
            )
    
    def _parse_post(self, post: Dict[str, Any]) -> Optional[NewsArticleItem]:
        """Parse individual post from API response."""
        try:
            url = post.get('link', '')
            if not url or self.is_url_in_db(url):
                return None
            
            self.stats['articles_found'] += 1
            
            # Extract headline
            headline = post.get('title', {}).get('rendered', '')
            headline = self._clean_html(headline)
            
            if not headline:
                return None
            
            # Extract body
            content = post.get('content', {}).get('rendered', '')
            article_body = self._clean_html(content)
            
            if len(article_body) < 100:
                return None
            
            if not self.filter_by_search_query(headline, article_body):
                return None
            
            # Parse date
            pub_date = None
            date_str = post.get('date', '')
            if date_str:
                try:
                    pub_date = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
                    pub_date = self.dhaka_tz.localize(pub_date)
                except ValueError:
                    pass
            
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                return None
            
            # Extract category from embedded data
            category = 'General'
            embedded = post.get('_embedded', {})
            terms = embedded.get('wp:term', [[]])
            if terms and terms[0]:
                category = terms[0][0].get('name', 'General')
            
            # Extract image
            image_url = None
            featured_media = embedded.get('wp:featuredmedia', [{}])
            if featured_media:
                image_url = featured_media[0].get('source_url', '')
            
            self.stats['articles_processed'] += 1
            
            return self.create_article_item(
                url=url,
                headline=headline,
                article_body=article_body,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=category,
                image_url=image_url,
            )
        except Exception as e:
            self.logger.error(f"Error parsing post: {e}")
            self.stats['errors'] += 1
            return None
    
    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content to plain text."""
        if not html_content:
            return ''
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
