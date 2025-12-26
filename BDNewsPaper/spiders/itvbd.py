"""
ITV BD (Independent Television) Spider (Bangla)
================================================
Scrapes articles from ITV BD (itvbd.com)

Features:
    - Category-based scraping
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


class ITVBDSpider(BaseNewsSpider):
    """
    Spider for ITV BD (Independent Television).
    
    Uses HTML scraping with category navigation.
    URL pattern: itvbd.com/{category}/{article_id}/{slug}
    
    Usage:
        scrapy crawl itvbd -a categories=national,politics
        scrapy crawl itvbd -a max_pages=10
    """
    
    name = 'itvbd'
    paper_name = 'ITV BD'
    allowed_domains = ['itvbd.com', 'www.itvbd.com']
    language = 'Bangla'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Category slug mappings
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'world': 'world',
        'international': 'world',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'health': 'health',
        'opinion': 'opinion',
        'analysis': 'analysis',
        'country': 'country',
        'india': 'world/india',
        'america': 'world/america',
        'dhaka': 'country/dhaka',
        'chittagong': 'country/chittagong',
        'khulna': 'country/khulna',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("ITV BD spider initialized")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests to category pages."""
        self.stats['requests_made'] = 0
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip()
                cat_slug = self.CATEGORIES.get(cat_lower, cat_lower)
                url = f"https://www.itvbd.com/{cat_slug}"
                
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_category,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': 1},
                    errback=self.handle_request_failure,
                )
        else:
            # Default categories
            for cat in ['national', 'politics', 'sports', 'world']:
                cat_slug = self.CATEGORIES.get(cat, cat)
                url = f"https://www.itvbd.com/{cat_slug}"
                
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
        
        # Extract article links - ITV uses /category/id/slug pattern
        article_links = response.css('a::attr(href)').getall()
        # Filter to article links (ITV uses /category/id/slug pattern)
        article_links = [
            l for l in article_links 
            if 'itvbd.com/' in l 
            and re.search(r'/\d+/', l)
            and not l.endswith('/category/')
        ]
        article_links = list(set(article_links))
        
        self.logger.info(f"Found {len(article_links)} articles in {category} page {page}")
        
        if not article_links:
            return
        
        found_count = 0
        for url in article_links:
            # Ensure full URL
            if not url.startswith('http'):
                url = f"https://www.itvbd.com{url}"
            
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
        
        # Pagination - look for next page links
        if found_count > 0 and page < self.max_pages:
            next_page_link = response.css(
                'a.next::attr(href), '
                'a[rel="next"]::attr(href), '
                '.pagination a.next::attr(href)'
            ).get()
            
            if next_page_link:
                if not next_page_link.startswith('http'):
                    next_page_link = f"https://www.itvbd.com{next_page_link}"
                
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
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        
        if not headline:
            return
        
        headline = unescape(headline.strip())
        
        # Extract body
        body_parts = response.css(
            'article p::text, '
            '.news-content p::text, '
            '.article-content p::text, '
            '.details-content p::text, '
            '.story-content p::text'
        ).getall()
        
        if not body_parts:
            body_parts = response.css('p::text').getall()
        
        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        
        if len(article_body) < 100:
            return
        
        # Search filter
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
        
        # Extract description as subtitle
        sub_title = response.css('meta[property="og:description"]::attr(content)').get()
        if sub_title:
            sub_title = unescape(sub_title.strip())[:500]
        
        # Extract author
        author = self.extract_author(response)
        
        self.stats['articles_processed'] += 1
        
        yield self.create_article_item(
            url=url,
            headline=headline,
            article_body=article_body,
            sub_title=sub_title,
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
