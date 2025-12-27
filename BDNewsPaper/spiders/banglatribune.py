"""
Bangla Tribune Spider (Bangla)
==============================
Scrapes articles from Bangla Tribune (banglatribune.com)

Features:
    - Category-based scraping with pagination
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


class BanglaTribuneSpider(BaseNewsSpider):
    """
    Spider for Bangla Tribune (Bangla Newspaper).
    
    Uses HTML scraping with ?page= pagination.
    
    Usage:
        scrapy crawl banglatribune -a categories=national,politics,sports
        scrapy crawl banglatribune -a max_pages=10
        scrapy crawl banglatribune -a start_date=2024-01-01
    """
    
    name = 'banglatribune'
    paper_name = 'Bangla Tribune'
    allowed_domains = ['banglatribune.com', 'www.banglatribune.com']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'foreign',
        'world': 'foreign',
        'foreign': 'foreign',
        'business': 'business',
        'economy': 'business',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'lifestyle': 'lifestyle',
        'education': 'education',
        'tech': 'tech',
        'technology': 'tech',
        'health': 'health',
        'opinion': 'opinion',
        'crime': 'crime',
        'law': 'law',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Bangla Tribune spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category pages."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    cat_slug = self.CATEGORIES[cat_lower]
                else:
                    cat_slug = cat_lower
                
                url = f"https://www.banglatribune.com/{cat_slug}"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl default categories
            default_cats = ['national', 'politics', 'business', 'sports']
            for cat in default_cats:
                cat_slug = self.CATEGORIES[cat]
                url = f"https://www.banglatribune.com/{cat_slug}"
                
                self.logger.info(f"Crawling category: {cat} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': cat, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)
        
        # Primary: CSS selectors for known patterns
        article_links = response.css('a[href*="/news/"]::attr(href)').getall()
        article_links += response.css(f'a[href*="/{cat_slug}/"]::attr(href)').getall()
        
        # Filter to only article links (with numeric IDs)
        article_links = [l for l in article_links if re.search(r'/\d+/', l)]
        
        # Deduplicate
        article_links = list(set(article_links))
        
        # FALLBACK: If CSS selectors fail, use universal link discovery
        if not article_links:
            self.logger.info(f"CSS selectors failed, using universal link discovery for {category}")
            article_links = self.discover_links(response, limit=50)
        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        found_count = 0
        
        for link in article_links:
            if not link.startswith('http'):
                url = f"https://www.banglatribune.com{link}"
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
        
        # Pagination
        if found_count > 0 and page < self.max_pages:
            next_page = page + 1
            next_url = f"https://www.banglatribune.com/{cat_slug}?page={next_page}"
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_category,
                meta={'category': category, 'cat_slug': cat_slug, 'page': next_page},
                errback=self.handle_request_failure,
            )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # Try JSON-LD and generic fallback FIRST (more reliable)
        extracted = self.extract_article_fallback(response)
        
        if extracted and extracted.get('headline') and extracted.get('article_body') and len(extracted.get('article_body', '')) >= 100:
            # Use fallback extraction result
            headline = unescape(extracted['headline'].strip())
            article_body = extracted['article_body']
            pub_date = None
            
            if extracted.get('publication_date'):
                pub_date = self._parse_date_string(extracted['publication_date'])
            
            # Date filter
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                return
            
            # Search query filter
            if not self.filter_by_search_query(headline, article_body):
                return
            
            self.stats['articles_processed'] += 1
            
            yield self.create_article_item(
                url=url,
                headline=headline,
                article_body=article_body,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=response.meta.get('category', 'General'),
                author=extracted.get('author') or self.extract_author(response),
                image_url=extracted.get('image_url'),
            )
            return
        
        # FALLBACK: Original CSS selector approach
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
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d %B, %Y',
            '%B %d, %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
