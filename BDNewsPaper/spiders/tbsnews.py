"""
TBS News (The Business Standard) Spider
========================================
Scrapes articles from The Business Standard (tbsnews.net)

Features:
    - Drupal AJAX API for category scraping
    - Numeric pagination support
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


class TBSNewsSpider(BaseNewsSpider):
    """
    Spider for The Business Standard.
    
    Uses Drupal views/ajax endpoint for efficient API-based scraping.
    
    Usage:
        scrapy crawl tbsnews -a categories=bangladesh,economy
        scrapy crawl tbsnews -a max_pages=20
        scrapy crawl tbsnews -a start_date=2024-01-01 -a end_date=2024-12-31
    """
    
    name = 'tbsnews'
    paper_name = 'The Business Standard'
    allowed_domains = ['tbsnews.net', 'www.tbsnews.net']
    
    # Drupal views/ajax API endpoint
    API_BASE = 'https://www.tbsnews.net/views/ajax'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category taxonomy term ID mappings (from Drupal)
    # view_args format: {term_id}/0
    CATEGORIES = {
        'bangladesh': 4,
        'politics': 5,
        'economy': 6,
        'business': 6,
        'stocks': 7,
        'world': 8,
        'international': 8,
        'sports': 9,
        'features': 10,
        'splash': 11,
        'entertainment': 11,
        'infograph': 12,
        'thoughts': 13,
        'opinion': 13,
        'analysis': 14,
        'tech': 15,
        'science': 16,
        'education': 17,
        'health': 18,
        'environment': 19,
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
        self.logger.info(f"TBS News spider initialized")
        self.logger.info(f"Categories: {self.categories or 'default'}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to Drupal AJAX API."""
        self.stats['requests_made'] = 0
        
        # If categories specified, crawl those
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                
                if cat_lower in self.CATEGORIES:
                    term_id = self.CATEGORIES[cat_lower]
                else:
                    # Try as numeric ID
                    try:
                        term_id = int(cat_lower)
                    except ValueError:
                        self.logger.warning(f"Unknown category: {category}")
                        continue
                
                # Drupal views/ajax endpoint
                url = (
                    f"{self.API_BASE}?"
                    f"view_name=category_grid_view&"
                    f"view_display_id=panel_pane_2&"
                    f"view_args={term_id}/0&"
                    f"page=0"
                )
                
                self.logger.info(f"Crawling category: {category} (term_id: {term_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_ajax_response,
                    meta={
                        'category': category,
                        'term_id': term_id,
                        'page': 0,
                    },
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl default categories
            default_cats = ['bangladesh', 'economy', 'world', 'sports']
            for cat in default_cats:
                term_id = self.CATEGORIES[cat]
                url = (
                    f"{self.API_BASE}?"
                    f"view_name=category_grid_view&"
                    f"view_display_id=panel_pane_2&"
                    f"view_args={term_id}/0&"
                    f"page=0"
                )
                
                self.logger.info(f"Crawling category: {cat} (term_id: {term_id})")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_ajax_response,
                    meta={
                        'category': cat,
                        'term_id': term_id,
                        'page': 0,
                    },
                    errback=self.handle_request_failure,
                )
    
    def parse_ajax_response(self, response: Response) -> Generator:
        """Parse Drupal AJAX JSON response."""
        category = response.meta.get('category', 'Unknown')
        term_id = response.meta.get('term_id')
        page = response.meta.get('page', 0)
        
        try:
            # Drupal returns array of command objects
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON from API: {response.url}")
            return
        
        # Find the insert command containing HTML
        html_content = ''
        for item in data:
            if isinstance(item, dict) and item.get('command') == 'insert':
                html_content = item.get('data', '')
                break
        
        if not html_content or len(html_content) < 100:
            self.logger.info(f"No more content for {category} at page {page}")
            return
        
        # Extract article links from HTML
        # Pattern: href="/bangladesh/politics/article-slug-123456"
        article_links = re.findall(
            r'href="(/[a-z]+(?:/[a-z-]+)*-\d+)"',
            html_content
        )
        
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
            url = f"https://www.tbsnews.net{link}"
            
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
        
        # Pagination - request next page
        if found_count > 0 and page < self.max_pages - 1:
            next_page = page + 1
            next_url = (
                f"{self.API_BASE}?"
                f"view_name=category_grid_view&"
                f"view_display_id=panel_pane_2&"
                f"view_args={term_id}/0&"
                f"page={next_page}"
            )
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_ajax_response,
                meta={
                    'category': category,
                    'term_id': term_id,
                    'page': next_page,
                },
                errback=self.handle_request_failure,
            )
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        url = response.url
        
        # Extract headline
        headline = (
            response.css('h1.title::text').get() or
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            self.logger.warning(f"No headline found: {url}")
            return
        
        headline = unescape(headline.strip())
        
        # Extract article body from the content div
        body_parts = response.css('.field-body p::text, .section-content p::text').getall()
        
        if not body_parts:
            body_parts = response.css('article p::text, .content p::text').getall()
        
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
            author_text = response.css('.author-name::text, .byline a::text').get()
            if author_text:
                author = author_text.strip()
        
        # Extract category from URL or meta
        category = response.meta.get('category', 'General')
        
        # Extract image
        image_url = (
            response.css('.section-media img::attr(src)').get() or
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
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
