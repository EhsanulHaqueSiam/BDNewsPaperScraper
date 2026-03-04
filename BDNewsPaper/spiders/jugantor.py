"""
Jugantor Spider (Bangla)
========================
Scrapes articles from Jugantor (jugantor.com) - Leading Bangla newspaper

Features:
    - Clean JSON API for latest/popular news
    - AJAX endpoint with limit/offset pagination
    - Category ID filtering
    - Date filtering (client-side)
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


class JugantorSpider(BaseNewsSpider):
    """
    Spider for Jugantor (Bangla Newspaper).
    
    Uses efficient AJAX API endpoint for JSON data.
    
    Usage:
        scrapy crawl jugantor -a categories=politics,national,sports
        scrapy crawl jugantor -a max_pages=20
        scrapy crawl jugantor -a start_date=2024-01-01
    """
    
    name = 'jugantor'
    paper_name = 'Jugantor'
    allowed_domains = ['jugantor.com', 'www.jugantor.com']
    language = 'Bangla'
    
    # AJAX API endpoint discovered from browser
    # Format: /ajax/load/latestnews/{limit}/{offset}/{category_id}
    API_BASE = 'https://www.jugantor.com/ajax/load/latestnews'
    
    # Items per API call
    ITEMS_PER_PAGE = 20
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category ID mappings (0 = all categories)
    CATEGORIES = {
        'all': 0,
        'national': 1,
        'politics': 2,
        'country-news': 3,
        'countrywide': 3,
        'capital': 4,
        'dhaka': 4,
        'international': 5,
        'world': 5,
        'entertainment': 6,
        'sports': 7,
        'business': 8,
        'economy': 8,
        'opinion': 9,
        'editorial': 10,
        'education': 11,
        'health': 12,
        'lifestyle': 13,
        'tech': 14,
        'technology': 14,
        'religion': 15,
        'feature': 16,
        'interview': 17,
        'crime': 18,
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
        },
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Jugantor (Bangla) spider initialized")
        self.logger.info(f"Categories: {self.categories or 'all'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to AJAX API."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip().replace('-', '').replace('_', '')
                
                if cat_lower in self.CATEGORIES:
                    cat_id = self.CATEGORIES[cat_lower]
                else:
                    # Try as numeric ID
                    try:
                        cat_id = int(cat_lower)
                    except ValueError:
                        self.logger.warning(f"Unknown category: {category}")
                        continue
                
                # API: /ajax/load/latestnews/{limit}/{offset}/{category_id}
                url = f"{self.API_BASE}/{self.ITEMS_PER_PAGE}/0/{cat_id}"
                
                self.logger.info(f"Crawling category: {category} (ID: {cat_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_api_response,
                    meta={
                        'category': category,
                        'cat_id': cat_id,
                        'offset': 0,
                    },
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl all categories (cat_id=0)
            url = f"{self.API_BASE}/{self.ITEMS_PER_PAGE}/0/0"
            
            self.logger.info("Crawling all categories")
            self.stats['requests_made'] += 1
            
            yield Request(
                url=url,
                callback=self.parse_api_response,
                meta={
                    'category': 'all',
                    'cat_id': 0,
                    'offset': 0,
                },
                errback=self.handle_request_failure,
            )
    
    def parse_api_response(self, response: Response) -> Generator:
        """Parse JSON API response with article data."""
        category = response.meta.get('category', 'all')
        cat_id = response.meta.get('cat_id', 0)
        offset = response.meta.get('offset', 0)
        page = (offset // self.ITEMS_PER_PAGE) + 1
        
        try:
            articles = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON from API: {response.url}")
            return
        
        if not articles:
            self.logger.info(f"No more articles in {category}")
            return
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not articles:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
            articles = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(articles)} articles in {category} page {page}")
        
        found_count = 0
        
        for article in articles:
            # Process article directly from API data
            item = self._process_api_article(article, category)
            if item:
                found_count += 1
                yield item
        
        # Pagination - get next batch
        if found_count > 0 and page < self.max_pages:
            next_offset = offset + self.ITEMS_PER_PAGE
            next_url = f"{self.API_BASE}/{self.ITEMS_PER_PAGE}/{next_offset}/{cat_id}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={
                    'category': category,
                    'cat_id': cat_id,
                    'offset': next_offset,
                },
                errback=self.handle_request_failure,
            )
    
    def _process_api_article(self, article: dict, category: str) -> Optional[NewsArticleItem]:
        """Process article data from API response."""
        try:
            url = article.get('url', '')
            if not url:
                return None
            
            if self.is_url_in_db(url):
                return None
            
            # Get headline
            headline = article.get('headline', '') or article.get('fullheadline', '')
            if not headline:
                return None
            
            # Clean HTML from headline
            headline = re.sub(r'<[^>]+>', '', headline)
            headline = unescape(headline.strip())
            
            # Get description/body
            description = article.get('description', '') or ''
            description = unescape(description.strip())
            
            if len(description) < 50:
                return None
            
            # Search query filter
            if not self.filter_by_search_query(headline, description):
                return None
            
            # Parse date from created_at (format: 2025-12-26 04:39:15)
            pub_date = None
            created_at = article.get('created_at', '')
            if created_at:
                pub_date = self._parse_date_string(created_at)
            
            # Date filter
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                return None
            
            # Get author/reporter
            author = article.get('reporter', '')
            
            # Get category from API
            api_category = article.get('categoryName', '') or article.get('categoryTitle', '') or category
            
            # Get image
            image_url = article.get('thumb', '') or article.get('thumbMedium', '')
            
            self.stats['articles_found'] += 1
            self.stats['articles_processed'] += 1
            
            return self.create_article_item(
                url=url,
                headline=headline,
                article_body=description,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=api_category,
                author=author,
                image_url=image_url,
            )
        except Exception as e:
            self.logger.error(f"Error processing article: {e}")
            return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date from API format."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # API format: 2025-12-26 04:39:15
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
