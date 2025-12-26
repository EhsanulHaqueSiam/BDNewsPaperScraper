"""
Daily Sun Spider (Enhanced)
============================
Scrapes English news articles from Daily Sun using their AJAX API.

API Endpoints Discovered:
    - /ajax/load/latestnews/{count}/{type}/{page}?lastID={lastID} - Latest news pagination
    - /ajax/load/popularnews/{count}/{offset} - Popular news
    - /ajax/load/categorynews/{categoryID}/{count}/{offset} - Category-specific news
    - /search?q={query} - Search functionality

Note:
    - Site has heavy Cloudflare protection
    - Uses jQuery/AJAX architecture (no Next.js)
    - Images served from dscdn.daily-sun.com

Features:
    - AJAX API support with pagination
    - Multiple extraction strategies (AJAX data, JSON-LD, HTML)
    - Category-based scraping
    - Search functionality
    - Cloudflare-aware request handling
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlencode, quote

import scrapy
from scrapy.http import Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class DailySunSpider(BaseNewsSpider):
    """
    Daily Sun scraper using their AJAX API.
    
    API Endpoints:
        - Latest News: /ajax/load/latestnews/{count}/{type}/{page}?lastID={lastID}
        - Category News: /ajax/load/categorynews/{categoryID}/{count}/{offset}
        - Popular News: /ajax/load/popularnews/{count}/{offset}
        - Search: /search?q={query}
    
    Usage:
        scrapy crawl dailysun -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl dailysun -a categories=Bangladesh,Sports
        scrapy crawl dailysun -a search_query="politics"
    """
    
    name = "dailysun"
    paper_name = "Daily Sun"
    allowed_domains = ["daily-sun.com", "www.daily-sun.com"]
    
    # API capabilities
    supports_api_date_filter = False  # Date filtering done client-side
    supports_api_category_filter = True
    supports_keyword_search = True
    
    # Custom settings for Cloudflare handling
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,  # Slower due to Cloudflare
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,  # Lower concurrency for Cloudflare
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1.0,
        'AUTOTHROTTLE_MAX_DELAY': 10.0,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'RETRY_TIMES': 5,  # More retries for Cloudflare blocks
        'RETRY_HTTP_CODES': [403, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
    }
    
    # Base URLs
    BASE_URL = "https://www.daily-sun.com"
    AJAX_LATEST_URL = "https://www.daily-sun.com/ajax/load/latestnews"
    AJAX_CATEGORY_URL = "https://www.daily-sun.com/ajax/load/categorynews"
    AJAX_POPULAR_URL = "https://www.daily-sun.com/ajax/load/popularnews"
    
    # Category mappings (name -> URL path and category ID if known)
    CATEGORIES = {
        "Bangladesh": {"path": "bangladesh", "id": "1"},
        "Business": {"path": "business", "id": "2"},
        "World": {"path": "world", "id": "3"},
        "Entertainment": {"path": "entertainment", "id": "4"},
        "Sports": {"path": "sports", "id": "5"},
        "Lifestyle": {"path": "lifestyle", "id": "6"},
        "Tech": {"path": "tech", "id": "7"},
        "Opinion": {"path": "opinion", "id": "8"},
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Search query
        self.search_query = kwargs.get('search_query', '')
        
        # Items per page
        self.items_per_page = int(kwargs.get('items_per_page', 30))
        
        # Track last IDs for pagination
        self.last_ids = {}
        
        # Track consecutive empty pages for stopping
        self.consecutive_empty = {}
        self.max_consecutive_empty = 3
        
        # Setup categories
        self._setup_categories()
        
        self.logger.info(f"Categories: {list(self.category_map.keys())}")
        if self.search_query:
            self.logger.info(f"Search query: {self.search_query}")
    
    def _setup_categories(self) -> None:
        """Setup category mappings based on filter."""
        if self.categories:
            self.category_map = {}
            for cat in self.categories:
                for key, value in self.CATEGORIES.items():
                    if key.lower() == cat.lower():
                        self.category_map[key] = value
                        break
            
            if not self.category_map:
                self.logger.warning("No valid categories found, using Bangladesh only")
                self.category_map = {"Bangladesh": self.CATEGORIES["Bangladesh"]}
        else:
            # Default categories
            self.category_map = {
                "Bangladesh": self.CATEGORIES["Bangladesh"],
                "Business": self.CATEGORIES["Business"],
                "Sports": self.CATEGORIES["Sports"],
            }
    
    # ================================================================
    # Request Generation
    # ================================================================
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial requests."""
        if self.search_query:
            # Search mode
            yield self._make_search_request()
        else:
            # Category-based scraping using AJAX API
            for category, info in self.category_map.items():
                self.consecutive_empty[category] = 0
                self.last_ids[category] = 0
                yield self._make_ajax_category_request(category, info, page=1)
    
    def _make_ajax_category_request(
        self, category: str, info: Dict, page: int = 1
    ) -> scrapy.Request:
        """Create AJAX request for category listing."""
        category_id = info.get("id", "1")
        
        # Build AJAX URL: /ajax/load/categorynews/{categoryID}/{count}/{offset}
        offset = (page - 1) * self.items_per_page
        ajax_url = f"{self.AJAX_CATEGORY_URL}/{category_id}/{self.items_per_page}/{offset}"
        
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=ajax_url,
            callback=self.parse_ajax_response,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/html, */*',
                'Referer': f"{self.BASE_URL}/{info['path']}",
            },
            meta={
                "category": category,
                "category_info": info,
                "page": page,
                "request_type": "ajax_category",
            },
            errback=self._handle_ajax_error,
            dont_filter=True,
        )
    
    def _make_ajax_latest_request(self, page: int = 1, last_id: int = 0) -> scrapy.Request:
        """Create AJAX request for latest news."""
        # URL format: /ajax/load/latestnews/{count}/{type}/{page}?lastID={lastID}
        ajax_url = f"{self.AJAX_LATEST_URL}/{self.items_per_page}/1/{page}?lastID={last_id}"
        
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=ajax_url,
            callback=self.parse_ajax_response,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/html, */*',
                'Referer': f"{self.BASE_URL}/todays-news",
            },
            meta={
                "category": "Latest",
                "page": page,
                "last_id": last_id,
                "request_type": "ajax_latest",
            },
            errback=self._handle_ajax_error,
            dont_filter=True,
        )
    
    def _make_search_request(self) -> scrapy.Request:
        """Create search request."""
        search_url = f"{self.BASE_URL}/search?q={quote(self.search_query)}"
        
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=search_url,
            callback=self.parse_search_results,
            meta={
                "category": f"search:{self.search_query}",
                "request_type": "search",
            },
            errback=self.handle_request_failure,
        )
    
    def _handle_ajax_error(self, failure):
        """Handle AJAX request errors - fallback to HTML scraping."""
        request = failure.request
        category = request.meta.get("category")
        category_info = request.meta.get("category_info", {})
        page = request.meta.get("page", 1)
        
        self.logger.warning(f"AJAX failed for {category}, falling back to HTML")
        self.stats['errors'] += 1
        
        # Fallback to category page HTML scraping
        if category_info:
            fallback_url = f"{self.BASE_URL}/{category_info['path']}"
            yield scrapy.Request(
                url=fallback_url,
                callback=self.parse_category_html,
                meta={
                    "category": category,
                    "category_info": category_info,
                    "page": page,
                },
                errback=self.handle_request_failure,
            )
    
    # ================================================================
    # AJAX Response Parsing
    # ================================================================
    
    def parse_ajax_response(self, response: Response) -> Generator:
        """Parse AJAX API response."""
        category = response.meta["category"]
        page = response.meta["page"]
        request_type = response.meta.get("request_type")
        
        # Try to parse as JSON first
        articles = []
        try:
            # AJAX response might be JSON or HTML fragment
            content_type = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
            
            if 'json' in content_type or response.text.strip().startswith('{'):
                data = json.loads(response.text)
                articles = data.get('items', data.get('articles', []))
                if isinstance(data, list):
                    articles = data
            else:
                # HTML fragment - parse directly
                yield from self._parse_ajax_html_fragment(response)
                return
                
        except json.JSONDecodeError:
            # It's HTML, parse as fragment
            yield from self._parse_ajax_html_fragment(response)
            return
        
        self.logger.info(f"Category '{category}' page {page}: Found {len(articles)} articles")
        
        if not articles:
            self.consecutive_empty[category] = self.consecutive_empty.get(category, 0) + 1
            if self.consecutive_empty[category] >= self.max_consecutive_empty:
                self.logger.info(f"Stopping {category}: {self.max_consecutive_empty} consecutive empty pages")
                return
        else:
            self.consecutive_empty[category] = 0
        
        # Process articles from JSON data
        for article_data in articles:
            url = article_data.get('url', '')
            if not url:
                continue
            
            full_url = f"{self.BASE_URL}{url}" if not url.startswith('http') else url
            
            # Check date filter if date is available
            pub_date = article_data.get('date', article_data.get('published_at', ''))
            if pub_date and not self._is_date_valid(pub_date):
                if self._is_before_start(pub_date):
                    self.logger.info(f"Stopping {category}: Article before start date")
                    return
                continue
            
            if not self.is_url_in_db(full_url):
                self.stats['articles_found'] += 1
                
                # Try to create item from AJAX data
                item = self._create_item_from_ajax_data(article_data, category)
                
                if item and self._has_sufficient_content(item):
                    yield item
                else:
                    # Need to fetch full article
                    yield scrapy.Request(
                        url=full_url,
                        callback=self.parse_article,
                        meta={
                            "category": category,
                            "ajax_data": article_data,
                        },
                        errback=self.handle_request_failure,
                    )
        
        # Pagination
        if articles and page < self.max_pages:
            next_page = page + 1
            if request_type == "ajax_latest":
                # Get last ID from response
                last_article = articles[-1] if articles else {}
                last_id = last_article.get('id', 0)
                yield self._make_ajax_latest_request(next_page, last_id)
            else:
                category_info = response.meta.get("category_info", {})
                yield self._make_ajax_category_request(category, category_info, next_page)
    
    def _parse_ajax_html_fragment(self, response: Response) -> Generator:
        """Parse HTML fragment from AJAX response."""
        category = response.meta.get("category", "Unknown")
        page = response.meta.get("page", 1)
        
        # Parse media items from HTML fragment
        articles = response.css('.media, .news-item, article')
        
        self.logger.info(f"Category '{category}' page {page}: Found {len(articles)} HTML articles")
        
        for article in articles:
            # Extract basic info
            title_el = article.css('h3::text, h4::text, .title::text').get()
            link_el = article.css('a.linkOverlay::attr(href), a::attr(href)').get()
            summary_el = article.css('.desktopSummary::text, .summary::text, p::text').get()
            date_el = article.css('.desktopTime span span::text, .date::text, time::text').get()
            img_el = article.css('img::attr(src), img::attr(data-src)').get()
            
            # Validate URL - skip invalid ones like #, javascript:, etc.
            if not self._is_valid_article_url(link_el):
                self.logger.debug(f"Skipping invalid URL: {link_el}")
                continue
            
            full_url = f"{self.BASE_URL}{link_el}" if not link_el.startswith('http') else link_el
            
            # Check date
            if date_el and not self._is_date_valid(date_el):
                if self._is_before_start(date_el):
                    return
                continue
            
            if not self.is_url_in_db(full_url):
                self.stats['articles_found'] += 1
                
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_article,
                    meta={
                        "category": category,
                        "preview_data": {
                            "title": title_el,
                            "summary": summary_el,
                            "date": date_el,
                            "image": img_el,
                        },
                    },
                    errback=self.handle_request_failure,
                )
        
        # Pagination for HTML response
        if len(articles) >= 10 and page < self.max_pages:
            category_info = response.meta.get("category_info", {})
            yield self._make_ajax_category_request(category, category_info, page + 1)
    
    def _create_item_from_ajax_data(
        self, data: Dict, category: str
    ) -> Optional[NewsArticleItem]:
        """Create item from AJAX data if complete."""
        title = data.get('title', data.get('headline', ''))
        body = data.get('content', data.get('body', data.get('summary', '')))
        url = data.get('url', '')
        
        # Validate URL - skip invalid ones like #, javascript:, etc.
        if not self._is_valid_article_url(url):
            self.logger.debug(f"Skipping invalid URL from API: {url}")
            return None
        
        full_url = f"{self.BASE_URL}{url}" if not url.startswith('http') else url
        
        # Parse date
        pub_date = data.get('date', data.get('published_at', 'Unknown'))
        
        # Get image
        image = data.get('image', data.get('thumbnail', ''))
        if image and not image.startswith('http'):
            image = f"https://dscdn.daily-sun.com/{image}"
        
        return self.create_article_item(
            headline=title,
            article_body=body,
            url=full_url,
            publication_date=pub_date,
            category=category,
            image_url=image if image else None,
        )
    
    def _has_sufficient_content(self, item: NewsArticleItem) -> bool:
        """Check if item has enough content to skip fetching full article."""
        body = item.get('article_body', '')
        return body and len(body) > 200
    
    def _is_valid_article_url(self, url: Optional[str]) -> bool:
        """Check if URL is a valid article link (not #, javascript:, empty, etc.)."""
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if not url:
            return False
        # Filter out common invalid patterns
        invalid_patterns = ['#', 'javascript:', 'void(0)', 'mailto:', 'tel:']
        for pattern in invalid_patterns:
            if url == pattern or url.startswith(pattern):
                return False
        # Must be a path or full URL
        return url.startswith('/') or url.startswith('http://') or url.startswith('https://')
    
    # ================================================================
    # Date Validation Helpers
    # ================================================================
    
    def _is_date_valid(self, date_str: str) -> bool:
        """Check if date is within range."""
        parsed = self._parse_date(date_str)
        if not parsed:
            return True  # Unknown date, let it through
        
        return self.start_date <= parsed <= self.end_date
    
    def _is_before_start(self, date_str: str) -> bool:
        """Check if date is before start date."""
        parsed = self._parse_date(date_str)
        if not parsed:
            return False
        
        return parsed < self.start_date
    
    def _parse_date(self, date_str: str, end_of_day: bool = False) -> Optional[datetime]:
        """Parse various date formats."""
        if not date_str:
            return None
        
        formats = [
            '%d %b %Y, %I:%M %p',  # "26 Dec 2025, 12:28 AM"
            '%d %B %Y, %I:%M %p',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%B %d, %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    # ================================================================
    # HTML Category Parsing (Fallback)
    # ================================================================
    
    def parse_category_html(self, response: Response) -> Generator:
        """Parse category page HTML (fallback)."""
        category = response.meta.get("category", "Unknown")
        
        # Check for Cloudflare block
        if 'Just a moment' in response.text or 'Cloudflare' in response.text:
            self.logger.warning(f"Cloudflare blocked {response.url}")
            self.stats['errors'] += 1
            return
        
        articles = response.css('.media, .news-item, article, .story-card')
        
        self.logger.info(f"Category '{category}': Found {len(articles)} articles in HTML")
        
        for article in articles:
            link = article.css('a::attr(href)').get()
            if not link:
                continue
            
            full_url = f"{self.BASE_URL}{link}" if not link.startswith('http') else link
            
            if not self.is_url_in_db(full_url):
                self.stats['articles_found'] += 1
                
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_article,
                    meta={"category": category},
                    errback=self.handle_request_failure,
                )
    
    # ================================================================
    # Search Results Parsing
    # ================================================================
    
    def parse_search_results(self, response: Response) -> Generator:
        """Parse search results page."""
        # Check for Cloudflare block
        if 'Just a moment' in response.text:
            self.logger.warning("Cloudflare blocked search results")
            self.stats['errors'] += 1
            return
        
        articles = response.css('.media, .search-result, article')
        
        self.logger.info(f"Search results: Found {len(articles)} articles")
        
        for article in articles:
            link = article.css('a::attr(href)').get()
            if not link:
                continue
            
            full_url = f"{self.BASE_URL}{link}" if not link.startswith('http') else link
            
            if not self.is_url_in_db(full_url):
                self.stats['articles_found'] += 1
                
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_article,
                    meta={"category": f"search:{self.search_query}"},
                    errback=self.handle_request_failure,
                )
    
    # ================================================================
    # Article Parsing
    # ================================================================
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        self.stats['articles_processed'] += 1
        
        # Check for Cloudflare block
        if 'Just a moment' in response.text:
            self.logger.warning(f"Cloudflare blocked {response.url}")
            self.stats['errors'] += 1
            return
        
        category = response.meta.get("category", "Unknown")
        
        # Strategy 1: JSON-LD structured data
        item = self._extract_from_jsonld(response)
        
        # Strategy 2: HTML parsing
        if not item:
            item = self._extract_from_html(response)
        
        # Strategy 3: Use preview data if available
        if not item:
            preview = response.meta.get("preview_data", {})
            if preview:
                item = self._extract_from_preview(response, preview)
        
        if item:
            item['category'] = category if not category.startswith('search:') else 'Search'
            yield item
        else:
            self.logger.warning(f"Could not extract data from {response.url}")
            self.stats['errors'] += 1
    
    def _extract_from_jsonld(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract from JSON-LD structured data."""
        scripts = response.xpath("//script[@type='application/ld+json']/text()").getall()
        
        for script in scripts:
            try:
                data = json.loads(script)
                
                if isinstance(data, list):
                    data = next(
                        (item for item in data if item.get("@type") in ["Article", "NewsArticle"]),
                        None
                    )
                    if not data:
                        continue
                elif data.get("@type") not in ["Article", "NewsArticle"]:
                    continue
                
                return self._create_item_from_jsonld(data, response)
                
            except (json.JSONDecodeError, KeyError):
                continue
        
        return None
    
    def _extract_from_html(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract from HTML selectors."""
        try:
            # Multiple selector strategies
            headline = (
                response.css('h1.title::text').get() or
                response.css('h1::text').get() or
                response.css('article h1::text').get() or
                response.css('.article-title::text').get()
            )
            
            # Body extraction - multiple strategies
            body_parts = []
            
            # Strategy 1: Main article content div
            body_parts.extend(response.css('.fullStory p::text, .article-body p::text').getall())
            
            # Strategy 2: Generic article paragraphs
            if not body_parts:
                body_parts.extend(response.css('article p::text').getall())
            
            # Strategy 3: Any paragraphs in content area
            if not body_parts:
                body_parts.extend(response.css('.content p::text, .story p::text').getall())
            
            body = " ".join(p.strip() for p in body_parts if p.strip())
            
            if not headline or not body or len(body) < 50:
                return None
            
            # Extract other fields
            pub_date = (
                response.css('time::attr(datetime)').get() or
                response.css('.date::text, .published-date::text').get() or
                response.css('meta[property="article:published_time"]::attr(content)').get() or
                "Unknown"
            )
            
            author = (
                response.css('.author::text, .reporter-name::text').get() or
                response.css('meta[name="author"]::attr(content)').get() or
                "Unknown"
            )
            
            image_url = (
                response.css('meta[property="og:image"]::attr(content)').get() or
                response.css('.featured-image img::attr(src)').get() or
                response.css('article img::attr(src)').get()
            )
            
            return self.create_article_item(
                headline=headline.strip(),
                article_body=body,
                url=response.url,
                publication_date=pub_date,
                author=author.strip() if author != "Unknown" else None,
                image_url=image_url,
            )
            
        except Exception as e:
            self.logger.debug(f"HTML extraction error: {e}")
            return None
    
    def _extract_from_preview(
        self, response: Response, preview: Dict
    ) -> Optional[NewsArticleItem]:
        """Extract using preview data as fallback."""
        headline = preview.get('title', '')
        if not headline:
            return None
        
        # Try to get body from page
        body_parts = response.css('article p::text, .content p::text').getall()
        body = " ".join(p.strip() for p in body_parts if p.strip())
        
        if not body:
            body = preview.get('summary', '')
        
        if not body or len(body) < 50:
            return None
        
        return self.create_article_item(
            headline=headline,
            article_body=body,
            url=response.url,
            publication_date=preview.get('date', 'Unknown'),
            image_url=preview.get('image'),
        )
    
    def _create_item_from_jsonld(
        self, data: Dict, response: Response
    ) -> NewsArticleItem:
        """Create item from JSON-LD data."""
        # Extract authors
        authors = data.get("author", [])
        if isinstance(authors, list):
            author_names = [
                a.get("name", "") if isinstance(a, dict) else str(a)
                for a in authors
            ]
            author = ", ".join(filter(None, author_names)) or "Unknown"
        elif isinstance(authors, dict):
            author = authors.get("name", "Unknown")
        else:
            author = str(authors) if authors else "Unknown"
        
        # Extract image
        image_data = data.get("image")
        image_url = None
        if isinstance(image_data, list) and image_data:
            if isinstance(image_data[0], dict):
                image_url = image_data[0].get("url")
            else:
                image_url = str(image_data[0])
        elif isinstance(image_data, dict):
            image_url = image_data.get("url")
        elif isinstance(image_data, str):
            image_url = image_data
        
        # Extract keywords
        keywords = data.get("keywords")
        if isinstance(keywords, list):
            keywords = ", ".join(str(k) for k in keywords)
        
        return self.create_article_item(
            headline=data.get("headline", "No headline"),
            url=data.get("url", response.url),
            article_body=data.get("articleBody", ""),
            sub_title=data.get("description", ""),
            publication_date=data.get("datePublished"),
            modification_date=data.get("dateModified"),
            author=author,
            image_url=image_url,
            keywords=keywords,
            publisher=data.get("publisher", {}).get("name", "Daily Sun"),
        )