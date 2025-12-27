"""
Barta24 Spider (Bangla) - API-Based
====================================
Scrapes articles from Barta24 (barta24.com) - Popular Bangla News Portal

Features:
    - API-based scraping (backoffice.barta24.com)
    - Direct JSON data extraction
    - No JavaScript rendering needed
    - Category filtering support
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


class Barta24Spider(BaseNewsSpider):
    """
    Spider for Barta24 (Popular Bangla News Portal).
    
    Uses Barta24's API for efficient JSON-based scraping.
    
    API Endpoints:
        - Latest articles: backoffice.barta24.com/api/home-json-bn/generateLatest.json
        - Article details: backoffice.barta24.com/api/content-details/{id}
    
    Usage:
        scrapy crawl barta24
        scrapy crawl barta24 -a max_pages=10
    """
    
    name = 'barta24'
    paper_name = 'Barta24'
    allowed_domains = ['barta24.com', 'backoffice.barta24.com']
    language = 'Bangla'
    
    # API endpoints
    API_BASE = 'https://backoffice.barta24.com/api'
    LATEST_API = f'{API_BASE}/home-json-bn/generateLatest.json'
    CDN_BASE = 'https://cdn.barta24.com'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = False  # API returns mixed categories
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json',
            'Accept-Language': 'bn,en;q=0.9',
        },
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Barta24 spider initialized (API mode)")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial request to latest articles API."""
        self.stats['requests_made'] = 0
        
        self.logger.info(f"Fetching latest articles from API: {self.LATEST_API}")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=self.LATEST_API,
            callback=self.parse_latest_api,
            errback=self.handle_request_failure,
        )
    
    def parse_latest_api(self, response: Response) -> Generator:
        """Parse latest articles JSON API response."""
        try:
            articles = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return
        
        if not isinstance(articles, list):
            self.logger.error("Expected list of articles from API")
            return
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not articles:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
            articles = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(articles)} articles from API")
        
        for article in articles:
            content_id = article.get('ContentID')
            if not content_id:
                continue
            
            # Build article URL for deduplication check
            article_url = f"https://barta24.com/details/{article.get('categorySlug', 'news')}/{content_id}"
            
            if self.is_url_in_db(article_url):
                continue
            
            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            
            # Request full article details
            details_url = f"{self.API_BASE}/content-details/{content_id}"
            
            yield Request(
                url=details_url,
                callback=self.parse_article_api,
                meta={
                    'article_url': article_url,
                    'category': article.get('categorySlug', ''),
                    'preview_headline': article.get('DetailsHeading', ''),
                },
                errback=self.handle_request_failure,
            )
    
    def parse_article_api(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse article details from API."""
        article_url = response.meta.get('article_url', response.url)
        category = response.meta.get('category', 'General')
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse article JSON: {e}")
            return
        
        # API returns {"data": [article_data, related...]}
        if not isinstance(data, dict) or 'data' not in data:
            self.logger.warning(f"Unexpected API response format")
            return
        
        articles_data = data.get('data', [])
        if not articles_data:
            return
        
        article = articles_data[0]  # First item is the main article
        
        # Extract headline
        headline = article.get('DetailsHeading', '') or response.meta.get('preview_headline', '')
        if not headline:
            self.logger.warning(f"No headline for article")
            return
        
        headline = unescape(headline.strip())
        
        # Extract article body from ContentDetails (array of HTML paragraphs)
        content_details = article.get('ContentDetails', [])
        if isinstance(content_details, list):
            body_parts = []
            for part in content_details:
                if isinstance(part, str):
                    cleaned = self._clean_html(part)
                    if cleaned:
                        body_parts.append(cleaned)
            article_body = '\n\n'.join(body_parts)
        else:
            article_body = ''
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {article_url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date
        pub_date = None
        date_str = article.get('created_at', '')
        if date_str:
            pub_date = self._parse_date_string(date_str)
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Extract author
        author = article.get('WriterName', '')
        
        # Extract category (use API category name if available)
        category = article.get('CategoryName', '') or article.get('CategorySlug', '') or category
        
        # Extract image
        image_path = article.get('ImageBgPath', '') or article.get('ImageSmPath', '')
        image_url = f"{self.CDN_BASE}/{image_path}" if image_path else None
        
        # Extract keywords
        keywords = article.get('Keywords', '')
        
        self.stats['articles_processed'] += 1
        
        yield self.create_article_item(
            url=article_url,
            headline=headline,
            article_body=article_body,
            publication_date=pub_date.isoformat() if pub_date else None,
            category=category,
            author=author if author else None,
            image_url=image_url,
            keywords=keywords if keywords else None,
        )
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML content to extract text."""
        if not html:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        text = unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date from API format (ISO 8601)."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Handle ISO format with timezone (e.g., "2025-12-26T06:37:03.000000Z")
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
