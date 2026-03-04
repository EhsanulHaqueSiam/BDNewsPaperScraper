"""
Sylhet Express Spider (Bangla)
==============================
Scrapes articles from Sylhet Express (sylhetexpress.net)

Features:
    - Regional news from Sylhet division
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


class SylhetExpressSpider(BaseNewsSpider):
    """
    Spider for Sylhet Express (Regional Bangla).
    
    Sylhet's first online daily - regional news coverage.
    
    Usage:
        scrapy crawl sylhetexpress -a categories=sylhet,national
        scrapy crawl sylhetexpress -a max_pages=10
    """
    
    name = 'sylhetexpress'
    paper_name = 'Sylhet Express'
    allowed_domains = ['sylhetexpress.net', 'www.sylhetexpress.net']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category mappings
    CATEGORIES = {
        'sylhet': 'sylhet',
        'regional': 'sylhet',
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'literature': 'literature',
        'sports': 'sports',
        'lead': 'lead_news',
        'popular': 'popular_news',
        'serviceclub': 'serviceclub',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Sylhet Express spider initialized (Regional)")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests."""
        self.stats['requests_made'] = 0
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                url = f"https://sylhetexpress.net/category/{cat_slug}/"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Default: main page
            url = "https://sylhetexpress.net/"
            self.stats['requests_made'] += 1
            yield Request(
                url=url,
                callback=self.parse_category,
                meta={'category': 'General', 'cat_slug': '', 'page': 1},
                errback=self.handle_request_failure,
            )
    
    def parse_category(self, response: Response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)
        
        # Extract article links - pattern: /category/id/
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            l for l in article_links
            if 'sylhetexpress.net/' in l
            and re.search(r'/\d+/$', l)  # Ends with article ID
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
                url = f"https://sylhetexpress.net{url}"
            
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
                    next_page_link = f"https://sylhetexpress.net{next_page_link}"
                
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
        
        # Extract headline
        headline = (
            response.css('h1.entry-title::text').get() or
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        # Extract body
        body_parts = response.css(
            '.entry-content p::text, '
            'article p::text, '
            '.post-content p::text'
        ).getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Parse date
        pub_date = None
        date_text = response.css('meta[property="article:published_time"]::attr(content)').get()
        if not date_text:
            date_text = response.css('time::attr(datetime)').get()
        
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
