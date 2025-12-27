"""
Daily Asian Age Spider
=======================
Scrapes articles from The Daily Asian Age (dailyasianage.com)

Features:
    - Category-based scraping with numeric IDs
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


class DailyAsianAgeSpider(BaseNewsSpider):
    """
    Spider for The Daily Asian Age.
    
    Uses HTML scraping with category ID navigation.
    
    Usage:
        scrapy crawl dailyasianage -a categories=frontpage,business
        scrapy crawl dailyasianage -a max_pages=10
        scrapy crawl dailyasianage -a start_date=2024-01-01
    """
    
    name = 'dailyasianage'
    paper_name = 'The Daily Asian Age'
    allowed_domains = ['dailyasianage.com', 'www.dailyasianage.com']
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category ID mappings (from website navigation)
    CATEGORIES = {
        'frontpage': 1,
        'front': 1,
        'asia': 2,
        'city': 3,
        'world': 4,
        'international': 4,
        'oped': 5,
        'opinion': 5,
        'business': 6,
        'economy': 6,
        'globalbusiness': 7,
        'newsaz': 8,
        'commercialcapital': 9,
        'commercial': 9,
        'countrywide': 11,
        'national': 11,
        'entertainment': 12,
        'sports': 13,
        'editorial': 14,
        'lifestyle': 15,
        'reciprocal': 16,
        'teens': 17,
        'saturdaypost': 18,
        'supplement': 19,
        'tech': 20,
        'technology': 20,
        'invogue': 24,
        'food': 25,
        'backpage': 26,
        'livingcity': 31,
        'openblog': 35,
        'humour': 38,
        'health': 39,
        'environment': 40,
        'travel': 41,
        'weather': 42,
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Daily Asian Age spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category pages."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip().replace(' ', '').replace('-', '').replace('_', '')
                
                if cat_lower in self.CATEGORIES:
                    cat_id = self.CATEGORIES[cat_lower]
                else:
                    # Try as numeric ID
                    try:
                        cat_id = int(cat_lower)
                    except ValueError:
                        self.logger.warning(f"Unknown category: {category}")
                        continue
                
                url = f"https://dailyasianage.com/news-category/{cat_id}"
                
                self.logger.info(f"Crawling category: {category} (ID: {cat_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_id': cat_id, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl default categories
            default_cats = ['frontpage', 'business', 'world', 'sports']
            for cat in default_cats:
                cat_id = self.CATEGORIES[cat]
                url = f"https://dailyasianage.com/news-category/{cat_id}"
                
                self.logger.info(f"Crawling category: {cat} (ID: {cat_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_id': cat_id, 'page': 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_id = response.meta.get('cat_id')
        page = response.meta.get('page', 1)
        
        # Find article links - pattern: /news/{id}/{slug}
        article_links = response.css('a[href*="/news/"]::attr(href)').getall()
        
        # Deduplicate
        article_links = list(set(article_links))
        
        # ROBUST FALLBACK: Use universal link discovery if selectors fail

        
        if not article_links:

        
            self.logger.info("CSS selectors failed, using universal link discovery")

        
            article_links = self.discover_links(response, limit=50)

        
        

        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            self.logger.info(f"No more articles in {category}")
            return
        
        found_count = 0
        
        for link in article_links:
            # Skip category links
            if '/news-category/' in link:
                continue
            
            if not link.startswith('http'):
                url = f"https://dailyasianage.com{link}"
            else:
                url = link
            
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
        
        # Pagination - check for "Load More" or next page links
        # The site may use lazy loading, so we limit to first page per category
        # to avoid excessive requests
        if found_count > 0 and page < self.max_pages:
            # Try offset-based pagination if supported
            next_page = page + 1
            next_url = f"https://dailyasianage.com/news-category/{cat_id}?page={next_page}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={'category': category, 'cat_id': cat_id, 'page': next_page},
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
            response.css('h1.title::text').get() or
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
            response.css('.date::text').get() or
            response.css('.time::text').get() or
            response.css('.news-date::text').get() or
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
            author_text = response.css('.author::text, .byline::text, .reporter::text').get()
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
        
        # Handle ISO format from meta tags
        if 'T' in date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt
            except ValueError:
                pass
        
        # Standard date formats
        formats = [
            '%d %B, %Y',           # 26 December, 2024
            '%B %d, %Y',           # December 26, 2024
            '%Y-%m-%d',            # 2024-12-26
            '%d/%m/%Y',            # 26/12/2024
            '%A, %d %B %Y',        # Thursday, 26 December 2024
            '%d %b %Y',            # 26 Dec 2024
            '%b %d, %Y',           # Dec 26, 2024
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
