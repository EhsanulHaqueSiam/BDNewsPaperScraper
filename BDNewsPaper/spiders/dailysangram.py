"""
Daily Sangram Spider (Bangla)
==============================
Scrapes articles from Daily Sangram (dailysangram.com) - Established Bangla Daily

Features:
    - Category-based scraping
    - HTML content extraction
    - Date filtering (client-side)
    - Search query filtering
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class DailySangramSpider(BaseNewsSpider):
    """
    Spider for Daily Sangram (Established Bangla Daily Newspaper).
    
    Uses HTML scraping with category navigation.
    
    Usage:
        scrapy crawl dailysangram
        scrapy crawl dailysangram -a categories=national,politics,sports
        scrapy crawl dailysangram -a max_pages=10
    """
    
    name = 'dailysangram'
    paper_name = 'Daily Sangram'
    allowed_domains = ['dailysangram.com', 'www.dailysangram.com']
    language = 'Bangla'
    
    # Base URL
    BASE_URL = 'https://www.dailysangram.com'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category slug mappings (URL path structure)
    CATEGORIES = {
        'national': 'bangladesh/national',
        'bangladesh': 'bangladesh/national',
        'politics': 'bangladesh/politics',
        'international': 'international',
        'world': 'international',
        'economy': 'economy',
        'business': 'economy',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'lifestyle': 'lifestyle',
        'opinion': 'opinion',
        'education': 'bangladesh/education-campus',
        'crime': 'bangladesh/crime',
        'islam': 'islam',
        'health': 'bangladesh/health',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Daily Sangram spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category pages."""
        self.stats['requests_made'] = 0
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    cat_path = self.CATEGORIES[cat_lower]
                else:
                    cat_path = cat_lower
                
                url = f"{self.BASE_URL}/{cat_path}/"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_path': cat_path, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Default categories if none specified
            default_cats = ['national', 'politics', 'sports', 'international']
            for cat in default_cats:
                cat_path = self.CATEGORIES.get(cat, cat)
                url = f"{self.BASE_URL}/{cat_path}/"
                
                self.logger.info(f"Crawling category: {cat} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_path': cat_path, 'page': 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_path = response.meta.get('cat_path')
        page = response.meta.get('page', 1)
        
        # Find article links - Daily Sangram uses /category/article_id/ pattern
        article_links = response.css('a::attr(href)').getall()
        
        # Filter to article links (pattern: /path/.../article_id/)
        # Articles have an alphanumeric ID at the end
        article_pattern = re.compile(r'dailysangram\.com/[\w/-]+/([A-Za-z0-9]{10,})/?$')
        
        filtered_links = []
        for link in article_links:
            if article_pattern.search(link):
                if not link.startswith('http'):
                    link = f"{self.BASE_URL}{link}"
                filtered_links.append(link)
        
        # Deduplicate
        article_links = list(set(filtered_links))
        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
            return
        
        found_count = 0
        
        for url in article_links:
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
        
        # Pagination - try next page if we found articles
        if found_count > 0 and page < self.max_pages:
            next_page = page + 1
            next_url = f"{self.BASE_URL}/{cat_path}/?page={next_page}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={'category': category, 'cat_path': cat_path, 'page': next_page},
                errback=self.handle_request_failure,
            )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # Extract headline from og:title or h1
        headline = (
            response.css('meta[property="og:title"]::attr(content)').get() or
            response.css('h1::text').get() or
            response.css('title::text').get() or
            ''
        )
        
        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return
        
        headline = unescape(headline.strip())
        # Clean headline - remove " - দৈনিক সংগ্রাম" suffix
        headline = re.sub(r'\s*-\s*দৈনিক সংগ্রাম\s*$', '', headline).strip()
        
        # Extract article body
        body_parts = response.css('article p::text, .article-content p::text, .content p::text').getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
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
            response.css('.time::text').get() or
            response.css('.post-date::text').get() or
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
        
        # Extract category
        category = response.meta.get('category', 'General')
        
        # Extract image
        image_url = (
            response.css('meta[property="og:image"]::attr(content)').get() or
            response.css('.news-image img::attr(src)').get() or
            response.css('article img::attr(src)').get()
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
