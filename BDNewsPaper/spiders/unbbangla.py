"""
UNB Bangla Spider (Bangla)
==========================
Scrapes articles from UNB Bangla (unb.com.bd/bangla)

Features:
    - API-based category scraping (same as English UNB)
    - Infinite scroll pagination via API
    - Date filtering (client-side)
    - Official news agency
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


class UNBBanglaSpider(BaseNewsSpider):
    """
    Spider for UNB Bangla (United News of Bangladesh Bangla).
    
    Usage:
        scrapy crawl unbbangla -a categories=bangladesh,politics
        scrapy crawl unbbangla -a max_pages=20
    """
    
    name = 'unbbangla'
    paper_name = 'UNB Bangla'
    allowed_domains = ['unb.com.bd']
    language = 'Bangla'
    
    # API endpoint (same as English but with Bangla categories)
    API_BASE = 'https://unb.com.bd/api/categories-news'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category ID mappings for Bangla
    CATEGORIES = {
        'bangladesh': 131,
        'national': 131,
        'politics': 132,
        'international': 133,
        'economics': 134,
        'sports': 135,
        'entertainment': 136,
        'lifestyle': 137,
        'opinion': 138,
        'country': 139,  # regional
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json, text/html, */*',
            'X-Requested-With': 'XMLHttpRequest',
        },
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("UNB Bangla spider initialized")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category API endpoints."""
        self.stats['requests_made'] = 0
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    cat_id = self.CATEGORIES[cat_lower]
                else:
                    try:
                        cat_id = int(cat_lower)
                    except ValueError:
                        self.logger.warning(f"Unknown category: {category}")
                        continue
                
                url = f"{self.API_BASE}?category_id={cat_id}&item=1"
                self.logger.info(f"Crawling category: {category} (ID: {cat_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_api_response,
                    meta={'category': category, 'category_id': cat_id, 'item': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Default categories
            default_cats = ['bangladesh', 'politics', 'economics', 'sports']
            for cat in default_cats:
                cat_id = self.CATEGORIES[cat]
                url = f"{self.API_BASE}?category_id={cat_id}&item=1"
                
                self.logger.info(f"Crawling category: {cat} (ID: {cat_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_api_response,
                    meta={'category': cat, 'category_id': cat_id, 'item': 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_api_response(self, response: Response) -> Generator:
        """Parse API response containing article HTML fragments."""
        category = response.meta.get('category', 'Unknown')
        cat_id = response.meta.get('category_id')
        item = response.meta.get('item', 1)
        
        html_content = response.text
        
        if not html_content or len(html_content) < 100:
            self.logger.info(f"No more content for {category} at item {item}")
            return
        
        # Extract article links - UNB Bangla pattern
        article_links = re.findall(r'href="(/bangla/category/[^"]+/\d+)"', html_content)
        article_links = list(set(article_links))
        
        self.logger.info(f"Found {len(article_links)} articles in {category} item {item}")
        
        if not article_links:
            return
        
        found_count = 0
        
        for link in article_links:
            url = f"https://unb.com.bd{link}"
            
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
        if found_count > 0 and item < self.max_pages:
            next_item = item + 1
            next_url = f"{self.API_BASE}?category_id={cat_id}&item={next_item}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={'category': category, 'category_id': cat_id, 'item': next_item},
                errback=self.handle_request_failure,
            )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('h2.title::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        # Extract article body
        body_parts = response.css('.news-content p::text, .content p::text, article p::text').getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date
        pub_date = None
        date_text = (
            response.css('.date::text').get() or
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            ''
        )
        
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        author = self.extract_author(response)
        category = response.meta.get('category', 'General')
        image_url = response.css('meta[property="og:image"]::attr(content)').get()
        
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
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # ISO format
        if 'T' in date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt
            except ValueError:
                pass
        
        # Relative times
        relative_match = re.match(r'(\d+)\s+(hour|minute|day|week)s?\s+ago', date_str, re.I)
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2).lower()
            
            now = datetime.now(self.dhaka_tz)
            if unit == 'minute':
                return now - timedelta(minutes=amount)
            elif unit == 'hour':
                return now - timedelta(hours=amount)
            elif unit == 'day':
                return now - timedelta(days=amount)
            elif unit == 'week':
                return now - timedelta(weeks=amount)
        
        # Standard formats
        formats = [
            '%B %d, %Y',
            '%d %B, %Y',
            '%Y-%m-%d',
            '%d/%m/%Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
