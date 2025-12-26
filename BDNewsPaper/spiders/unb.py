"""
UNB (United News of Bangladesh) Spider
=======================================
Scrapes articles from United News of Bangladesh (unb.com.bd)

Features:
    - API-based category scraping
    - Infinite scroll pagination via API
    - Date filtering (client-side)
    - Search query filtering
"""

import json
import re
from datetime import datetime
from html import unescape
from typing import Any, Dict, Generator, List, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class UNBSpider(BaseNewsSpider):
    """
    Spider for United News of Bangladesh.
    
    Usage:
        scrapy crawl unb -a categories=bangladesh,international
        scrapy crawl unb -a max_pages=20
        scrapy crawl unb -a start_date=2024-01-01 -a end_date=2024-12-31
    """
    
    name = 'unb'
    paper_name = 'United News of Bangladesh'
    allowed_domains = ['unb.com.bd', 'www.unb.com.bd']
    
    # API endpoint discovered from browser network inspection
    API_BASE = 'https://unb.com.bd/api/categories-news'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category ID mappings from the website
    CATEGORIES = {
        'bangladesh': 14,
        'national': 14,
        'international': 107,
        'politics': 108,
        'business': 109,
        'economy': 109,
        'sports': 110,
        'entertainment': 111,
        'lifestyle': 112,
        'science': 113,
        'technology': 114,
        'tech': 114,
        'health': 115,
        'education': 116,
        'environment': 117,
        'crime': 118,
        'law': 119,
        'opinion': 120,
        'editorial': 121,
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
        self.logger.info(f"UNB spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category API endpoints."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    cat_id = self.CATEGORIES[cat_lower]
                else:
                    # Try as numeric ID
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
                    meta={
                        'category': category,
                        'category_id': cat_id,
                        'item': 1,
                    },
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl default categories
            default_cats = ['bangladesh', 'international', 'business', 'sports']
            for cat in default_cats:
                cat_id = self.CATEGORIES[cat]
                url = f"{self.API_BASE}?category_id={cat_id}&item=1"
                
                self.logger.info(f"Crawling category: {cat} (ID: {cat_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_api_response,
                    meta={
                        'category': cat,
                        'category_id': cat_id,
                        'item': 1,
                    },
                    errback=self.handle_request_failure,
                )
    
    def parse_api_response(self, response: Response) -> Generator:
        """Parse API response containing article HTML fragments."""
        category = response.meta.get('category', 'Unknown')
        cat_id = response.meta.get('category_id')
        item = response.meta.get('item', 1)
        
        # The API returns HTML content as text
        html_content = response.text
        
        if not html_content or len(html_content) < 100:
            self.logger.info(f"No more content for {category} at item {item}")
            return
        
        # Extract article links from the HTML response
        # Pattern: href="/category/ID/title-slug"
        article_links = re.findall(r'href="(/category/\d+/[^"]+)"', html_content)
        
        # Also try pattern: href="/news/ID/title-slug"  
        article_links += re.findall(r'href="(/news/\d+/[^"]+)"', html_content)
        
        # Deduplicate
        article_links = list(set(article_links))
        
        self.logger.info(f"Found {len(article_links)} articles in {category} item {item}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
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
        
        # Pagination - request next item batch
        if found_count > 0 and item < self.max_pages:
            next_item = item + 1
            next_url = f"{self.API_BASE}?category_id={cat_id}&item={next_item}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={
                    'category': category,
                    'category_id': cat_id,
                    'item': next_item,
                },
                errback=self.handle_request_failure,
            )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('h2.title::text').get() or
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
            body_parts = response.css('.main-content p::text, .article-body p::text').getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date - format: "X hours ago" or actual date
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
            author_text = response.css('.reporter::text, .author::text, .byline::text').get()
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
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats including relative times."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Handle ISO format from meta tags
        if 'T' in date_str:
            try:
                # ISO format: 2024-12-26T05:00:00+06:00
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt
            except ValueError:
                pass
        
        # Handle relative times: "X hours ago", "X minutes ago"
        relative_match = re.match(r'(\d+)\s+(hour|minute|day|week)s?\s+ago', date_str, re.I)
        if relative_match:
            from datetime import timedelta
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
        
        # Standard date formats
        formats = [
            '%B %d, %Y',           # December 26, 2024
            '%d %B, %Y',           # 26 December, 2024
            '%Y-%m-%d',            # 2024-12-26
            '%d/%m/%Y',            # 26/12/2024
            '%A, %d %B, %Y',       # Thursday, 26 December, 2024
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
