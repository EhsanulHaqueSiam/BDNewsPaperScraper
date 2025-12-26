"""
The Independent BD Spider
=========================
Scrapes articles from The Independent Bangladesh (theindependentbd.com)

Features:
    - Category filtering via URL
    - RSS feed for latest articles
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


class TheIndependentSpider(BaseNewsSpider):
    """
    Spider for The Independent Bangladesh.
    
    Usage:
        scrapy crawl theindependent -a categories=bangladesh,politics,business
        scrapy crawl theindependent -a max_pages=10
        scrapy crawl theindependent -a start_date=2024-01-01 -a end_date=2024-12-31
        scrapy crawl theindependent -a search_query=election
    """
    
    name = 'theindependent'
    paper_name = 'The Independent'
    allowed_domains = ['theindependentbd.com', 'www.theindependentbd.com']
    
    # API/filter capabilities
    supports_api_date_filter = False  # Date filter is client-side
    supports_api_category_filter = True
    
    # Category URL mappings
    CATEGORIES = {
        'politics': '/online/politics',
        'bangladesh': '/online/bangladesh',
        'world': '/online/world-news',
        'business': '/online/business',
        'sports': '/online/sports',
        'entertainment': '/online/entertainment',
        'opinion': '/online/opinion',
        'environment': '/online/environment',
        'science': '/online/science-tech',
        'metro': '/online/dhaka-metro',
        'culture': '/online/art-culture',
        'travel': '/online/travel-tourism',
        'health': '/online/health',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Use RSS feed by default for comprehensive scraping
        self.use_rss = kwargs.get('use_rss', 'true').lower() == 'true'
        
        self.logger.info(f"The Independent spider initialized")
        self.logger.info(f"Categories: {self.categories or 'all'}")
        self.logger.info(f"Use RSS: {self.use_rss}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those category pages
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    url = f"https://theindependentbd.com{self.CATEGORIES[cat_lower]}"
                else:
                    # Try direct slug
                    url = f"https://theindependentbd.com/online/{cat_lower}"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Use RSS feed for all latest articles
            if self.use_rss:
                self.logger.info("Crawling via RSS feed")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url='https://theindependentbd.com/rss.xml',
                    callback=self.parse_rss,
                    errback=self.handle_request_failure,
                )
            else:
                # Crawl all categories
                for cat_name, cat_path in self.CATEGORIES.items():
                    url = f"https://theindependentbd.com{cat_path}"
                    self.stats['requests_made'] += 1
                    
                    yield Request(
                        url=url,
                        callback=self.parse_category,
                        meta={'category': cat_name, 'page': 1},
                        errback=self.handle_request_failure,
                    )
    
    def parse_rss(self, response: Response) -> Generator[Request, None, None]:
        """Parse RSS feed for article URLs."""
        # RSS items
        items = response.xpath('//item')
        
        self.logger.info(f"Found {len(items)} articles in RSS feed")
        
        for item in items:
            url = item.xpath('link/text()').get()
            title = item.xpath('title/text()').get()
            pub_date_str = item.xpath('pubDate/text()').get()
            
            if not url:
                continue
            
            # Check if already processed
            if self.is_url_in_db(url):
                self.logger.debug(f"Skipping duplicate: {url}")
                continue
            
            # Parse date for filtering
            if pub_date_str:
                try:
                    # RFC 822 format: Thu, 26 Dec 2024 10:00:00 +0600
                    pub_date = datetime.strptime(
                        pub_date_str.strip()[:25], 
                        '%a, %d %b %Y %H:%M:%S'
                    )
                    pub_date = self.dhaka_tz.localize(pub_date)
                    
                    if not self.is_date_in_range(pub_date):
                        self.stats['date_filtered'] += 1
                        continue
                except ValueError:
                    pass
            
            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            
            yield Request(
                url=url,
                callback=self.parse_article,
                meta={'title_hint': title},
                errback=self.handle_request_failure,
            )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        page = response.meta.get('page', 1)
        
        # Find article links
        article_links = response.css('a[href*="/post/"]::attr(href)').getall()
        article_links = list(set(article_links))  # Dedupe
        
        self.logger.info(f"Found {len(article_links)} articles on {category} page {page}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
            return
        
        found_in_range = 0
        
        for url in article_links:
            if not url.startswith('http'):
                url = f"https://theindependentbd.com{url}"
            
            if self.is_url_in_db(url):
                continue
            
            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            found_in_range += 1
            
            yield Request(
                url=url,
                callback=self.parse_article,
                meta={'category': category},
                errback=self.handle_request_failure,
            )
        
        # Pagination - try next page if we found articles and haven't hit max
        if found_in_range > 0 and page < self.max_pages:
            next_page = page + 1
            # Some category pages might support ?page= 
            next_url = f"{response.url.split('?')[0]}?page={next_page}"
            
            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={'category': category, 'page': next_page},
                errback=self.handle_request_failure,
            )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # Skip non-article pages
        if '/post/' not in url:
            return
        
        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('h2.title::text').get() or
            response.css('.post-title::text').get() or
            response.meta.get('title_hint', '')
        )
        
        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return
        
        headline = headline.strip()
        
        # Extract article body
        body_parts = response.css('article p::text, .post-content p::text, .news-content p::text').getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(p.strip() for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            self.logger.debug(f"Article too short: {url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            self.logger.debug(f"Filtered by search: {url}")
            return
        
        # Extract date
        pub_date_str = (
            response.css('.date::text').get() or
            response.css('.time::text').get() or
            response.css('.post-date::text').get() or
            ''
        )
        
        pub_date = self._parse_date_string(pub_date_str)
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Extract author
        author = self.extract_author(response)
        
        # Extract category
        category = (
            response.meta.get('category') or
            response.css('.category a::text').get() or
            response.css('.breadcrumb a::text').getall()[-1] if response.css('.breadcrumb a::text').getall() else None or
            'General'
        )
        
        # Extract image
        image_url = (
            response.css('article img::attr(src)').get() or
            response.css('.post-image img::attr(src)').get() or
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
        
        formats = [
            '%d %B, %Y %I:%M:%S %p',  # 30 January, 2022 11:12:21 AM
            '%d %B, %Y %H:%M:%S',
            '%d %B, %Y',
            '%B %d, %Y',
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
