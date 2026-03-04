"""
Observer BD Spider
==================
Scrapes articles from The Daily Observer Bangladesh (observerbd.com)

Features:
    - Category filtering via category ID
    - Date filtering (client-side)
    - Search query filtering
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class ObserverBDSpider(BaseNewsSpider):
    """
    Spider for The Daily Observer Bangladesh.
    
    Usage:
        scrapy crawl observerbd -a categories=national,international
        scrapy crawl observerbd -a max_pages=10
        scrapy crawl observerbd -a start_date=2024-01-01 -a end_date=2024-12-31
    """
    
    name = 'observerbd'
    paper_name = 'The Daily Observer'
    allowed_domains = ['observerbd.com', 'www.observerbd.com']
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category ID mappings
    CATEGORIES = {
        'national': 186,
        'international': 187,
        'countryside': 188,
        'business': 191,
        'sports': 185,
        'education': 227,
        'opinion': 246,
        'editorial': 199,
        'oped': 200,
        'city': 195,
        'health': 228,
        'entertainment': 236,
        'analysis': 247,
        'dhaka': 238,
        'chittagong': 239,
        'rajshahi': 240,
        'khulna': 241,
        'sylhet': 242,
        'barisal': 243,
        'rangpur': 244,
        'mymensingh': 245,
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Observer BD spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    cat_id = self.CATEGORIES[cat_lower]
                    url = f"https://www.observerbd.com/menu/{cat_id}"
                else:
                    # Try as numeric ID
                    try:
                        cat_id = int(cat_lower)
                        url = f"https://www.observerbd.com/menu/{cat_id}"
                    except ValueError:
                        self.logger.warning(f"Unknown category: {category}")
                        continue
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl default categories
            default_cats = ['national', 'international', 'business', 'sports']
            for cat in default_cats:
                cat_id = self.CATEGORIES[cat]
                url = f"https://www.observerbd.com/menu/{cat_id}"
                
                self.logger.info(f"Crawling category: {cat} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'page': 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        page = response.meta.get('page', 1)
        
        # Find article links
        article_links = response.css('a[href*="/news/"]::attr(href)').getall()
        article_links = list(set(article_links))  # Dedupe
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not article_links:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
            article_links = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(article_links)} articles on {category} page {page}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
            return
        
        found_count = 0
        
        for url in article_links:
            if not url.startswith('http'):
                url = f"https://www.observerbd.com{url}"
            
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
        
        # Pagination - Observer BD supports &page= parameter
        if found_count > 0 and page < self.max_pages:
            cat_id = self.CATEGORIES.get(category, '147')
            next_url = f"https://www.observerbd.com/cat.php?cd={cat_id}&page={page + 1}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={'category': category, 'page': page + 1},
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
        
        # Skip non-article pages
        if '/news/' not in url:
            return
        
        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('h2.title::text').get() or
            response.css('.news-title::text').get() or
            ''
        )
        
        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return
        
        headline = headline.strip()
        
        # Extract article body
        body_parts = response.css('.news-content p::text, .content p::text, article p::text').getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(p.strip() for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Extract date - format: Thursday, 25 December, 2025 at 10:12 PM
        pub_date_str = ''
        date_patterns = response.css('text()').re(r'\w+day,\s+\d+\s+\w+,\s+\d+\s+at\s+\d+:\d+\s+[AP]M')
        if date_patterns:
            pub_date_str = date_patterns[0]
        
        pub_date = self._parse_date_string(pub_date_str)
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Extract author
        author = self.extract_author(response)
        if not author:
            # Try common patterns
            author_text = response.css('i::text, .reporter::text').get()
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
        """Parse date from various formats."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Format: Thursday, 25 December, 2025 at 10:12 PM
        formats = [
            '%A, %d %B, %Y at %I:%M %p',
            '%A, %d %B, %Y',
            '%d %B, %Y',
            '%B %d, %Y',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
