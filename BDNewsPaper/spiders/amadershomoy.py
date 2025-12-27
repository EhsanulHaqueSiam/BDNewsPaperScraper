"""
Dainik Amader Shomoy Spider (Bangla)
====================================
Scrapes articles from Dainik Amader Shomoy (dainikamadershomoy.com)

Features:
    - Category-based scraping
    - Date filtering (client-side)
    - Bangla newspaper
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class DainikAmaderShomoySpider(BaseNewsSpider):
    """
    Spider for Dainik Amader Shomoy (Bangla Daily).
    
    Uses HTML scraping with category navigation.
    
    Usage:
        scrapy crawl amadershomoy -a categories=national,politics
        scrapy crawl amadershomoy -a max_pages=10
    """
    
    name = 'amadershomoy'
    paper_name = 'Amader Shomoy'
    allowed_domains = ['dainikamadershomoy.com', 'www.dainikamadershomoy.com']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'economy': 'economy',
        'business': 'economy',
        'opinion': 'opinion',
        'country': 'country',
        'religion': 'religion',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Dainik Amader Shomoy spider initialized")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category pages."""
        self.stats['requests_made'] = 0
        
        # This site uses Nuxt.js and requires JavaScript rendering
        playwright_meta = {
            'playwright': True,
            'playwright_include_page': False,
        }
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                url = f"https://dainikamadershomoy.com/category/all/{cat_slug}/"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1, **playwright_meta},
                    errback=self.handle_request_failure,
                )
        else:
            # Default: main page for latest articles
            url = "https://dainikamadershomoy.com/"
            self.stats['requests_made'] += 1
            yield Request(
                url=url,
                callback=self.parse_category,
                meta={'category': 'General', 'cat_slug': '', 'page': 1, **playwright_meta},
                errback=self.handle_request_failure,
            )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)
        
        # Extract article links - site uses /details/{id} pattern
        article_links = response.css('a[href*="/details/"]::attr(href)').getall()
        article_links = list(set(article_links))
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail
        if not article_links:
            self.logger.info("CSS selectors failed, using universal link discovery")
            article_links = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            return
        
        found_count = 0
        for url in article_links:
            if not url.startswith('http'):
                url = f"https://dainikamadershomoy.com{url}"
            
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
        if found_count > 0 and page < self.max_pages:
            next_page_link = response.css('a.next::attr(href), a[rel="next"]::attr(href)').get()
            if next_page_link:
                if not next_page_link.startswith('http'):
                    next_page_link = f"https://dainikamadershomoy.com{next_page_link}"
                
                self.stats['requests_made'] += 1
                yield Request(
                    url=next_page_link,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': page + 1},
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
        
        # Extract headline
        headline = (
            response.css('h1::text').get() or
            response.css('h1.test::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        # Extract body - site uses .description class
        body_parts = response.css('.description p::text, .description::text').getall()
        
        if not body_parts:
            body_parts = response.css('article p::text, .content p::text, p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        # Search filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Parse date - site uses .publish-time class
        pub_date = None
        date_text = (
            response.css('p.publish-time::text').get() or
            response.css('.publish-time::text').get() or
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            response.css('time::attr(datetime)').get()
        )
        
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        category = response.meta.get('category', 'General')
        image_url = response.css('meta[property="og:image"]::attr(content)').get()
        
        # Extract author
        author = self.extract_author(response)
        
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
        """Parse date string to datetime."""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.split('+')[0].split('Z')[0], fmt.split('%z')[0])
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
