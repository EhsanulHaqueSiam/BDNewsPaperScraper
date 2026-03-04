"""
Ekushey TV Spider (Bangla)
==========================
Scrapes articles from Ekushey TV (ekushey-tv.com)

Features:
    - TV news portal
    - Category-based scraping
    - Date filtering (client-side)
"""

import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class EkusheyTVSpider(BaseNewsSpider):
    """
    Spider for Ekushey TV (Bangla TV News).
    
    TV channel news portal - "Committed to Change".
    
    Usage:
        scrapy crawl ekusheytv
        scrapy crawl ekusheytv -a max_pages=10
    """
    
    name = 'ekusheytv'
    paper_name = 'Ekushey TV'
    allowed_domains = ['ekushey-tv.com']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Ekushey TV spider initialized")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests."""
        self.stats['requests_made'] = 0
        
        url = "https://ekushey-tv.com/"
        self.stats['requests_made'] += 1
        yield Request(
            url=url,
            callback=self.parse_category,
            meta={'category': 'General', 'page': 1},
            errback=self.handle_request_failure,
        )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        page = response.meta.get('page', 1)
        
        # Extract article links
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            l for l in article_links
            if 'ekushey-tv.com/' in l
            and re.search(r'/\d+/?$', l)  # Article ID pattern
            and '/category/' not in l
            and '/page/' not in l
        ]
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
                url = f"https://ekushey-tv.com{url}"
            
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
        
        headline = (
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        body_parts = response.css('article p::text, .content p::text').getall()
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        if not self.filter_by_search_query(headline, article_body):
            return
        
        pub_date = None
        date_text = response.css('meta[property="article:published_time"]::attr(content)').get()
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())
        
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        category = response.meta.get('category', 'General')
        image_url = response.css('meta[property="og:image"]::attr(content)').get()
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
