"""
Dhaka Tribune Spider
====================
Scrapes English news articles from Dhaka Tribune.

Website Structure:
    - Standard HTML pagination with page parameter
    - Category-based URL structure
    - JSON-LD structured data available

Features:
    - Category-based scraping
    - HTML pagination
    - Client-side date filtering
    - JSON-LD extraction
"""

import json
import re
from datetime import datetime
from typing import Generator, Optional

import scrapy
from scrapy.http import Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class DhakaTribuneSpider(BaseNewsSpider):
    """
    Dhaka Tribune scraper using HTML pagination.
    
    Usage:
        scrapy crawl dhakatribune -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl dhakatribune -a categories=bangladesh,business,sports
    """
    
    name = "dhakatribune"
    paper_name = "Dhaka Tribune"
    allowed_domains = ["dhakatribune.com", "www.dhakatribune.com"]
    
    # API capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    supports_keyword_search = True  # Has search at /search?query=
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.5,
        'AUTOTHROTTLE_MAX_DELAY': 3.0,
    }
    
    BASE_URL = "https://www.dhakatribune.com"
    
    # Category mappings
    CATEGORIES = {
        "bangladesh": "bangladesh",
        "politics": "bangladesh/politics",
        "nation": "bangladesh/nation",
        "world": "world",
        "business": "business",
        "economy": "business/economy",
        "sports": "sports",
        "cricket": "sports/cricket",
        "football": "sports/football",
        "opinion": "opinion",
        "editorial": "opinion/editorial",
        "lifestyle": "lifestyle",
        "entertainment": "lifestyle/entertainment",
        "tech": "technology",
    }
    
    DEFAULT_CATEGORIES = ["bangladesh", "business", "sports", "world"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup categories
        self._setup_categories()
        
        # Track consecutive old articles per category
        self.consecutive_old_articles = {}
        self.max_consecutive_old = 5
        
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
        if self.search_query:
            # Search mode
            yield self._make_search_request(page=1)
        else:
            # Category mode
            for category, path in self.category_map.items():
                self.consecutive_old_articles[category] = 0
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
    
    def _make_search_request(self, page: int = 1) -> scrapy.Request:
        """Create request for search results."""
        url = f"{self.BASE_URL}/search?query={self.search_query}"
        if page > 1:
            url = f"{url}&page={page}"
        
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=url,
            callback=self.parse_search_results,
            meta={"page": page},
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
        
        # Find article links - Dhaka Tribune uses various card formats
        article_links = response.css(
            'article a::attr(href), '
            '.card a::attr(href), '
            '.news-card a::attr(href), '
            'h2 a::attr(href), '
            'h3 a::attr(href)'
        ).getall()
        
        # Filter to unique article URLs
        seen_urls = set()
        valid_links = []
        for link in article_links:
            if not link or link in seen_urls:
                continue
            
            # Only process article URLs (contain numeric ID)
            if not re.search(r'/\d+/', link):
                continue
            
            full_url = link if link.startswith('http') else f"{self.BASE_URL}{link}"
            
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                valid_links.append(full_url)
        
        self.logger.info(f"Category '{category}' page {page}: Found {len(valid_links)} articles")
        
        old_article_count = 0
        
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
        
        # Pagination - continue if we found articles
        if not self.should_stop and len(valid_links) > 0 and page < self.max_pages:
            yield self._make_category_request(category, path, page + 1)
    
    def parse_search_results(self, response: Response) -> Generator:
        """Parse search results page."""
        if self.should_stop:
            return
        
        page = response.meta["page"]
        
        # Extract article links from search results
        article_links = response.css('article a::attr(href), h2 a::attr(href)').getall()
        
        seen_urls = set()
        for link in article_links:
            if not link or link in seen_urls:
                continue
            
            if not re.search(r'/\d+/', link):
                continue
            
            full_url = link if link.startswith('http') else f"{self.BASE_URL}{link}"
            
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            if full_url in self.processed_urls or self.is_url_in_db(full_url):
                continue
            
            self.processed_urls.add(full_url)
            self.stats['articles_found'] += 1
            
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_article,
                meta={"category": f"search:{self.search_query}"},
                errback=self.handle_request_failure,
            )
        
        # Pagination
        if len(seen_urls) > 0 and page < self.max_pages:
            yield self._make_search_request(page + 1)
    
    # ================================================================
    # Article Parsing
    # ================================================================
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        if self.should_stop:
            return
        
        self.stats['articles_processed'] += 1
        category = response.meta.get("category", "Unknown")
        
        # Strategy 1: JSON-LD structured data
        item = self._extract_from_jsonld(response)
        
        # Strategy 2: HTML parsing
        if not item:
            item = self._extract_from_html(response)
        
        if item:
            # Set category
            item['category'] = category if not category.startswith("search:") else item.get('category', 'Unknown')
            
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
            
            # Search filtering (client-side)
            if self.search_query and not category.startswith("search:"):
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
                
                # Extract keywords
                keywords = data.get("keywords")
                if isinstance(keywords, list):
                    keywords = ", ".join(str(k) for k in keywords)
                
                return self.create_article_item(
                    headline=headline,
                    article_body=body,
                    url=response.url,
                    sub_title=data.get("description") if body != data.get("description") else None,
                    publication_date=data.get("datePublished", "Unknown"),
                    modification_date=data.get("dateModified"),
                    author=author,
                    image_url=image_url,
                    keywords=keywords,
                    publisher="Dhaka Tribune",
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
                'article p::text, '
                '.article-content p::text, '
                '.story-content p::text'
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
                response.css('.date::text, .time::text').get() or
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
            
            # Category from URL or meta
            category = response.css(
                'meta[property="article:section"]::attr(content)'
            ).get()
            
            return self.create_article_item(
                headline=headline,
                article_body=body,
                url=response.url,
                publication_date=pub_date,
                author=author.strip() if author != "Unknown" else None,
                image_url=image_url,
                category=category,
                publisher="Dhaka Tribune",
            )
            
        except Exception as e:
            self.logger.debug(f"HTML extraction error: {e}")
            return None
