"""
BD News 24 Spider
=================
Scrapes English news articles from BD News 24.

Website Structure:
    - Bilingual site (English and Bangla)
    - Category-based URL structure
    - Standard HTML pagination

Features:
    - Category-based scraping
    - English content focus
    - HTML pagination
    - Client-side date filtering
"""

import json
import re
from datetime import datetime
from typing import Generator, Optional

import scrapy
from scrapy.http import Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class BDNews24Spider(BaseNewsSpider):
    """
    BD News 24 English scraper using HTML pagination.
    
    Usage:
        scrapy crawl bdnews24 -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl bdnews24 -a categories=bangladesh,business,sports
    """
    
    name = "bdnews24"
    paper_name = "BD News 24"
    allowed_domains = ["bdnews24.com"]
    
    # API capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    supports_keyword_search = False
    
    # Custom settings - Cloudflare protected site
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1.0,
        'AUTOTHROTTLE_MAX_DELAY': 5.0,
        'ROBOTSTXT_OBEY': False,  # Site has aggressive bot detection
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
        },
    }
    
    BASE_URL = "https://bdnews24.com"
    
    # Category mappings
    CATEGORIES = {
        "bangladesh": "bangladesh",
        "politics": "politics",
        "economy": "economy",
        "world": "world",
        "business": "business",
        "sports": "sports",
        "entertainment": "entertainment",  
        "tech": "tech",
        "opinion": "opinion",
        "lifestyle": "lifestyle",
    }
    
    DEFAULT_CATEGORIES = ["bangladesh", "business", "sports", "world"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._setup_categories()
        self.logger.info(f"Categories: {list(self.category_map.keys())}")
    
    def _setup_categories(self) -> None:
        """Setup category mappings based on filter."""
        if self.categories:
            self.category_map = {}
            for cat in self.categories:
                cat_lower = cat.lower()
                if cat_lower in self.CATEGORIES:
                    self.category_map[cat_lower] = self.CATEGORIES[cat_lower]
            
            if not self.category_map:
                self.logger.warning("No valid categories found, using defaults")
                self.category_map = {
                    cat: self.CATEGORIES[cat] for cat in self.DEFAULT_CATEGORIES
                }
        else:
            self.category_map = {
                cat: self.CATEGORIES[cat] for cat in self.DEFAULT_CATEGORIES
            }
    
    # ================================================================
    # Request Generation
    # ================================================================
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial requests for categories."""
        for category, path in self.category_map.items():
            yield self._make_category_request(category, path, page=1)
    
    def _make_category_request(
        self, category: str, path: str, page: int = 1
    ) -> scrapy.Request:
        """Create request for category page."""
        url = f"{self.BASE_URL}/{path}"
        if page > 1:
            url = f"{url}?page={page}"
        
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=url,
            callback=self.parse_category_page,
            meta={
                "category": category,
                "category_path": path,
                "page": page,
            },
            errback=self.handle_request_failure,
        )
    
    # ================================================================
    # Category Page Parsing
    # ================================================================
    
    def parse_category_page(self, response: Response) -> Generator:
        """Parse category listing page."""
        if self.should_stop:
            return
        
        category = response.meta["category"]
        path = response.meta["category_path"]
        page = response.meta["page"]
        
        # Find article links - bdnews24 uses hex ID URLs like /bangladesh/f54fe8134e48
        # Try multiple selector patterns for robustness
        article_links = []
        
        # Pattern 1: Links containing category path with hex IDs
        category_links = response.css(f'a[href*="/{path}/"]::attr(href)').getall()
        article_links.extend(category_links)
        
        # Pattern 2: Generic article containers
        container_links = response.css(
            '.Cat-list a::attr(href), '
            '.rm-container a::attr(href), '
            '.Cat-lead-wrapper a::attr(href), '
            'article a::attr(href), '
            'h2 a::attr(href), '
            'h3 a::attr(href), '
            'h5 a::attr(href)'
        ).getall()
        article_links.extend(container_links)
        
        # Filter to unique article URLs
        seen_urls = set()
        valid_links = []
        for link in article_links:
            if not link or link in seen_urls:
                continue
            
            # Skip category pages
            if link.endswith('/') or '/page/' in link:
                continue
            
            full_url = link if link.startswith('http') else f"{self.BASE_URL}{link}"
            
            # Only process bdnews24.com links
            if 'bdnews24.com' not in full_url:
                continue
            
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                valid_links.append(full_url)
        
        self.logger.info(f"Category '{category}' page {page}: Found {len(valid_links)} articles")
        
        for full_url in valid_links:
            if self.should_stop:
                break
            
            if full_url in self.processed_urls:
                continue
            
            if self.is_url_in_db(full_url):
                continue
            
            self.processed_urls.add(full_url)
            self.stats['articles_found'] += 1
            
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_article,
                meta={"category": category},
                errback=self.handle_request_failure,
            )
        
        # Pagination
        if not self.should_stop and len(valid_links) > 0 and page < self.max_pages:
            yield self._make_category_request(category, path, page + 1)
    
    # ================================================================
    # Article Parsing
    # ================================================================
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        if self.should_stop:
            return
        
        self.stats['articles_processed'] += 1
        category = response.meta.get("category", "Unknown")
        
        # Strategy 1: JSON-LD
        item = self._extract_from_jsonld(response)
        
        # Strategy 2: HTML parsing
        if not item:
            item = self._extract_from_html(response)
        
        if item:
            item['category'] = category
            
            # Date validation
            pub_date = item.get('publication_date', '')
            if pub_date and pub_date != 'Unknown':
                parsed_date = self.parse_article_date(pub_date)
                if parsed_date:
                    if self.is_before_start_date(parsed_date):
                        self.stats['date_filtered'] += 1
                        return
                    if not self.is_date_in_range(parsed_date):
                        self.stats['date_filtered'] += 1
                        return
            
            # Search filtering
            if self.search_query:
                headline = item.get('headline', '')
                body = item.get('article_body', '')
                if not self.filter_by_search_query(headline, body):
                    return
            
            yield item
        else:
            self.logger.warning(f"Could not extract article: {response.url}")
            self.stats['errors'] += 1
    
    def _extract_from_jsonld(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract article data from JSON-LD."""
        scripts = response.xpath("//script[@type='application/ld+json']/text()").getall()
        
        for script in scripts:
            try:
                data = json.loads(script)
                
                if isinstance(data, list):
                    data = next(
                        (item for item in data 
                         if item.get("@type") in ["Article", "NewsArticle"]),
                        None
                    )
                    if not data:
                        continue
                
                if data.get("@type") not in ["Article", "NewsArticle", "WebPage"]:
                    continue
                
                headline = data.get("headline", "")
                body = data.get("articleBody", "") or data.get("description", "")
                
                if not headline or not body:
                    continue
                
                # Extract author
                author = "Unknown"
                authors = data.get("author", [])
                if isinstance(authors, list) and authors:
                    author_names = [
                        a.get("name", "") if isinstance(a, dict) else str(a)
                        for a in authors
                    ]
                    author = ", ".join(filter(None, author_names))
                elif isinstance(authors, dict):
                    author = authors.get("name", "Unknown")
                
                # Extract image
                image_data = data.get("image")
                image_url = None
                if isinstance(image_data, list) and image_data:
                    image_url = image_data[0].get("url") if isinstance(image_data[0], dict) else image_data[0]
                elif isinstance(image_data, dict):
                    image_url = image_data.get("url")
                elif isinstance(image_data, str):
                    image_url = image_data
                
                return self.create_article_item(
                    headline=headline,
                    article_body=body,
                    url=response.url,
                    publication_date=data.get("datePublished", "Unknown"),
                    modification_date=data.get("dateModified"),
                    author=author,
                    image_url=image_url,
                    publisher="BD News 24",
                )
                
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return None
    
    def _extract_from_html(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract article data from HTML."""
        try:
            # Headline
            headline = (
                response.css('h1.title::text').get() or
                response.css('article h1::text').get() or
                response.css('h1::text').get()
            )
            
            if not headline:
                return None
            
            headline = headline.strip()
            
            # Body
            body_parts = response.css(
                '.article-content p::text, '
                '.story-content p::text, '
                'article p::text, '
                '.content p::text'
            ).getall()
            
            if not body_parts:
                body_parts = response.css('p::text').getall()
            
            body = " ".join(p.strip() for p in body_parts if p.strip())
            
            if not body or len(body) < 50:
                return None
            
            # Date
            pub_date = (
                response.css('meta[property="article:published_time"]::attr(content)').get() or
                response.css('time::attr(datetime)').get() or
                response.css('.date::text').get() or
                "Unknown"
            )
            
            # Author
            author = (
                response.css('.author-name::text').get() or
                response.css('meta[name="author"]::attr(content)').get() or
                "Unknown"
            )
            
            # Image
            image_url = (
                response.css('meta[property="og:image"]::attr(content)').get() or
                response.css('article img::attr(src)').get()
            )
            
            return self.create_article_item(
                headline=headline,
                article_body=body,
                url=response.url,
                publication_date=pub_date,
                author=author.strip() if author != "Unknown" else None,
                image_url=image_url,
                publisher="BD News 24",
            )
            
        except Exception as e:
            self.logger.debug(f"HTML extraction error: {e}")
            return None
