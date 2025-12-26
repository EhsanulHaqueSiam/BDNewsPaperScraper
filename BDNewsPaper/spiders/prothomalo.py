"""
Prothom Alo Spider (Enhanced)
=============================
Scrapes English news articles from Prothom Alo using their comprehensive API.

API Endpoints Discovered:
    - /api/v1/advanced-search - Article listing with filters
    - /route-data.json?path={slug} - Full article content in JSON
    - /api/v1/authors - Author information

Features:
    - Full API support with date and category filtering
    - Keyword search via 'q' parameter
    - Multiple extraction strategies (route-data.json, JSON-LD, API data, HTML)
    - Automatic pagination with offset
    - Complete article metadata extraction
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


class ProthomaloSpider(BaseNewsSpider):
    """
    Prothom Alo English edition scraper using their advanced search API.
    
    API Parameters Discovered:
        - q: Search keyword
        - from-date/to-date: Date range (ISO format with milliseconds)
        - section-id: Category filter (comma-separated IDs)
        - sort: latest-published, relevance, oldest-published
        - offset: Pagination offset
        - limit: Results per page
        - tag-name: Filter by tag
        - type: Story type (text, photo, video, live-blog)
        - fields: Comma-separated list of fields to return
    
    Usage:
        scrapy crawl prothomalo -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl prothomalo -a categories=Bangladesh,Sports
        scrapy crawl prothomalo -a search_query="Sheikh Hasina"
    """
    
    name = "prothomalo"
    paper_name = "Prothom Alo"
    allowed_domains = ["en.prothomalo.com"]
    
    # API capabilities
    supports_api_date_filter = True
    supports_api_category_filter = True
    supports_keyword_search = True
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 16,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.1,
        'AUTOTHROTTLE_MAX_DELAY': 2.0,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 8.0,
    }
    
    # API Endpoints
    BASE_API_URL = "https://en.prothomalo.com/api/v1/advanced-search"
    ROUTE_DATA_URL = "https://en.prothomalo.com/route-data.json"
    AUTHORS_API_URL = "https://en.prothomalo.com/api/v1/authors"
    
    # Category Section IDs (comprehensive list)
    CATEGORY_SECTION_IDS = {
        # Main Categories
        "Bangladesh": "16600,16725,16727,16728,17129,17134,17135,17136,17137,17139,35627",
        "Politics": "16725,17134",
        "Sports": "16603,16747,16748,17138",
        "Business": "16602,16735,16736,16737,16738,17132,17141,17203",
        "Opinion": "16606,16751,16752,17202",
        "Entertainment": "16604,16762,35629,35639,35640",
        "Youth": "16622,16756,17140",
        "World": "16601,16729,16730,16731,16732,16733,17130,17131,17142",
        "Environment": "16623,16767,16768",
        "Science & Tech": "16605,16770,16771,17143",
        "Corporate": "16624,16772,16773",
        "Lifestyle": "16764,16765,16766",
        "Photo": "16607,16774,16775",
        "Video": "16608,16776",
    }
    
    # All fields to request from API
    API_FIELDS = [
        'headline', 'subheadline', 'slug', 'url', 'tags', 'sections',
        'hero-image-s3-key', 'hero-image-caption', 'hero-image-metadata',
        'hero-image-attribution', 'last-published-at', 'first-published-at',
        'published-at', 'updated-at', 'alternative', 'authors', 'author-name',
        'author-id', 'story-template', 'metadata', 'access', 'seo', 'summary',
        'id', 'content-created-at', 'cards'
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Parse search query if provided
        self.search_query = kwargs.get('search_query', '')
        
        # Convert dates to ISO format for API (with milliseconds)
        self.start_timestamp = self._date_to_api_format(self.start_date)
        self.end_timestamp = self._date_to_api_format(self.end_date)
        
        # Setup categories
        self._setup_categories()
        
        # Default limit per page
        self.page_limit = int(kwargs.get('page_limit', 50))
        
        # Sort order
        self.sort_order = kwargs.get('sort', 'latest-published')
        
        # Story type filter
        self.story_type = kwargs.get('story_type', '')  # text, photo, video, live-blog
        
        self.logger.info(f"Categories: {list(self.category_map.keys())}")
        if self.search_query:
            self.logger.info(f"Search query: {self.search_query}")
    
    def _date_to_api_format(self, dt: datetime) -> str:
        """Convert datetime to API format (ISO with milliseconds)."""
        return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    def _setup_categories(self) -> None:
        """Setup category mappings based on filter."""
        if self.categories:
            self.category_map = {}
            for cat in self.categories:
                # Match by key (case-insensitive)
                for key, section_id in self.CATEGORY_SECTION_IDS.items():
                    if key.lower() == cat.lower():
                        self.category_map[key] = section_id
                        break
            
            if not self.category_map:
                self.logger.warning("No valid categories found, using Bangladesh only")
                self.category_map = {"Bangladesh": self.CATEGORY_SECTION_IDS["Bangladesh"]}
        else:
            # Default: scrape main categories
            self.category_map = {
                "Bangladesh": self.CATEGORY_SECTION_IDS["Bangladesh"],
                "Sports": self.CATEGORY_SECTION_IDS["Sports"],
                "Business": self.CATEGORY_SECTION_IDS["Business"],
            }
    
    # ================================================================
    # Request Generation
    # ================================================================
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial API requests."""
        if self.search_query:
            # Keyword search mode
            yield self._make_search_request(offset=0)
        else:
            # Category-based scraping
            for category, section_id in self.category_map.items():
                self.logger.info(f"Starting requests for category: {category}")
                yield self._make_category_request(category, section_id, offset=0)
    
    def _make_category_request(self, category: str, section_id: str, offset: int = 0) -> scrapy.Request:
        """Create API request for category listing."""
        params = {
            'section-id': section_id,
            'from-date': self.start_timestamp,
            'to-date': self.end_timestamp,
            'sort': self.sort_order,
            'offset': offset,
            'limit': self.page_limit,
            'fields': ','.join(self.API_FIELDS),
        }
        
        if self.story_type:
            params['type'] = self.story_type
        
        api_url = f"{self.BASE_API_URL}?{urlencode(params)}"
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=api_url,
            callback=self.parse_api_response,
            meta={
                "category": category,
                "section_id": section_id,
                "offset": offset,
                "page_num": offset // self.page_limit + 1,
                "request_type": "category",
            },
            errback=self.handle_request_failure,
            dont_filter=True,
        )
    
    def _make_search_request(self, offset: int = 0) -> scrapy.Request:
        """Create API request for keyword search."""
        params = {
            'q': self.search_query,
            'from-date': self.start_timestamp,
            'to-date': self.end_timestamp,
            'sort': self.sort_order,
            'offset': offset,
            'limit': self.page_limit,
            'fields': ','.join(self.API_FIELDS),
        }
        
        if self.story_type:
            params['type'] = self.story_type
        
        api_url = f"{self.BASE_API_URL}?{urlencode(params)}"
        self.stats['requests_made'] += 1
        
        return scrapy.Request(
            url=api_url,
            callback=self.parse_api_response,
            meta={
                "category": f"search:{self.search_query}",
                "offset": offset,
                "page_num": offset // self.page_limit + 1,
                "request_type": "search",
            },
            errback=self.handle_request_failure,
            dont_filter=True,
        )
    
    # ================================================================
    # API Response Parsing
    # ================================================================
    
    def parse_api_response(self, response: Response) -> Generator:
        """Parse API response and extract article URLs."""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.stats['errors'] += 1
            return
        
        category = response.meta["category"]
        offset = response.meta["offset"]
        page_num = response.meta["page_num"]
        request_type = response.meta.get("request_type", "category")
        
        total_results = data.get("total", 0)
        items = data.get("items", [])
        
        self.logger.info(
            f"Category '{category}' page {page_num}: "
            f"Found {len(items)} articles (Total: {total_results})"
        )
        
        # Process articles
        for item in items:
            slug = item.get("slug")
            url = item.get("url")
            
            # Validate URL - skip invalid patterns
            if not self.is_valid_article_url(url):
                self.logger.debug(f"Skipping invalid URL from API: {url}")
                continue
            
            full_url = f"https://en.prothomalo.com{url}" if not url.startswith('http') else url
            
            if not self.is_url_in_db(full_url):
                self.stats['articles_found'] += 1
                
                # Use route-data.json API for full article content
                route_data_url = f"{self.ROUTE_DATA_URL}?path={quote(url)}"
                
                yield scrapy.Request(
                    url=route_data_url,
                    callback=self.parse_route_data,
                    meta={
                        "category": category,
                        "api_data": item,
                        "article_url": full_url,
                    },
                    errback=self._handle_route_data_error,
                )
        
        # Handle pagination
        if request_type == "category":
            section_id = response.meta.get("section_id")
            if (offset + self.page_limit < total_results and 
                page_num < self.max_pages and 
                len(items) > 0):
                
                next_offset = offset + self.page_limit
                yield self._make_category_request(category, section_id, offset=next_offset)
        else:
            # Search pagination
            if (offset + self.page_limit < total_results and 
                page_num < self.max_pages and 
                len(items) > 0):
                
                next_offset = offset + self.page_limit
                yield self._make_search_request(offset=next_offset)
    
    def _handle_route_data_error(self, failure):
        """Handle route-data.json errors - fallback to HTML parsing."""
        request = failure.request
        article_url = request.meta.get("article_url")
        api_data = request.meta.get("api_data")
        category = request.meta.get("category")
        
        self.logger.warning(f"Route data failed for {article_url}, falling back to HTML")
        
        yield scrapy.Request(
            url=article_url,
            callback=self.parse_article_html,
            meta={
                "category": category,
                "api_data": api_data,
            },
            errback=self.handle_request_failure,
        )
    
    # ================================================================
    # Route Data Parsing (Preferred Method)
    # ================================================================
    
    def parse_route_data(self, response: Response) -> Optional[NewsArticleItem]:
        """Parse route-data.json for complete article content."""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback to HTML
            yield scrapy.Request(
                url=response.meta["article_url"],
                callback=self.parse_article_html,
                meta=response.meta,
                errback=self.handle_request_failure,
            )
            return
        
        self.stats['articles_processed'] += 1
        
        # Get page data
        page_data = data.get("data", {})
        story = page_data.get("story", {})
        
        if not story:
            self.logger.warning(f"No story data in route-data for {response.meta['article_url']}")
            return None
        
        # Extract all available fields
        item = self._extract_from_story(story, response.meta)
        
        if item:
            yield item
    
    def _extract_from_story(self, story: Dict, meta: Dict) -> NewsArticleItem:
        """Extract all fields from story data."""
        # Basic info
        headline = story.get("headline", "")
        subheadline = story.get("subheadline", "")
        url = meta.get("article_url", "")
        category = meta.get("category", "Unknown")
        
        # Extract article body from cards
        article_body = self._extract_body_from_cards(story.get("cards", []))
        
        # Dates (convert from Unix timestamp)
        pub_timestamp = story.get("published-at") or story.get("first-published-at")
        mod_timestamp = story.get("updated-at") or story.get("last-published-at")
        
        publication_date = self._timestamp_to_date(pub_timestamp)
        modification_date = self._timestamp_to_date(mod_timestamp)
        
        # Authors
        authors = story.get("authors", [])
        author_names = []
        for author in authors:
            if isinstance(author, dict):
                name = author.get("name", "")
                if name:
                    author_names.append(name)
        author = ", ".join(author_names) if author_names else "Unknown"
        
        # Hero image
        hero_image = story.get("hero-image-s3-key", "")
        image_url = f"https://images.prothomalo.com/{hero_image}" if hero_image else None
        image_caption = story.get("hero-image-caption", "")
        image_attribution = story.get("hero-image-attribution", "")
        
        # Tags
        tags = story.get("tags", [])
        tag_names = [t.get("name", "") for t in tags if isinstance(t, dict)]
        keywords = ", ".join(tag_names) if tag_names else None
        
        # Sections (subcategories)
        sections = story.get("sections", [])
        section_names = [s.get("name", "") for s in sections if isinstance(s, dict)]
        subcategory = ", ".join(section_names) if section_names else None
        
        # SEO metadata
        seo = story.get("seo", {})
        meta_description = seo.get("meta-description", "") or story.get("summary", "")
        meta_keywords = seo.get("meta-keywords", [])
        if meta_keywords and isinstance(meta_keywords, list):
            if not keywords:
                keywords = ", ".join(meta_keywords)
        
        # Access type
        access_type = story.get("access", "free")  # free, subscription, etc.
        
        # Story type
        story_template = story.get("story-template", "text")  # text, photo, video, live-blog
        
        # Create item with all extracted fields
        return self.create_article_item(
            headline=headline,
            sub_title=subheadline,
            article_body=article_body,
            url=url,
            publication_date=publication_date,
            modification_date=modification_date,
            author=author,
            category=category if category and not category.startswith("search:") else subcategory,
            image_url=image_url,
            keywords=keywords,
            publisher="Prothom Alo",
        )
    
    def _extract_body_from_cards(self, cards: List[Dict]) -> str:
        """Extract article body from cards structure."""
        body_parts = []
        
        for card in cards:
            story_elements = card.get("story-elements", [])
            for element in story_elements:
                element_type = element.get("type", "")
                
                if element_type == "text":
                    text = element.get("text", "")
                    # Remove HTML tags
                    clean_text = re.sub(r'<[^>]+>', '', text)
                    if clean_text.strip():
                        body_parts.append(clean_text.strip())
                
                elif element_type == "title":
                    text = element.get("text", "")
                    if text.strip():
                        body_parts.append(f"\n{text.strip()}\n")
                
                elif element_type == "blockquote":
                    text = element.get("text", "")
                    if text.strip():
                        body_parts.append(f'"{text.strip()}"')
        
        return " ".join(body_parts)
    
    def _timestamp_to_date(self, timestamp: Optional[int]) -> str:
        """Convert Unix timestamp (milliseconds) to ISO date string."""
        if not timestamp:
            return "Unknown"
        
        try:
            # Timestamp is in milliseconds
            dt = datetime.fromtimestamp(timestamp / 1000, tz=self.dhaka_tz)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return "Unknown"
    
    # ================================================================
    # HTML Parsing (Fallback)
    # ================================================================
    
    def parse_article_html(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse article page with HTML parsing (fallback)."""
        self.stats['articles_processed'] += 1
        
        # Strategy 1: JSON-LD structured data
        item = self._extract_from_jsonld(response)
        
        # Strategy 2: API data fallback
        if not item:
            api_data = response.meta.get('api_data')
            if api_data:
                item = self._extract_from_api_data(api_data, response)
        
        # Strategy 3: HTML parsing fallback
        if not item:
            item = self._extract_from_html(response)
        
        if item:
            item['category'] = response.meta.get('category', 'Unknown')
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
    
    def _extract_from_api_data(self, api_data: Dict, response: Response) -> Optional[NewsArticleItem]:
        """Extract from API data as fallback."""
        try:
            # Try to get body from HTML
            body = " ".join(response.css('div.story-content p::text, article p::text').getall())
            
            if body and len(body) > 50:
                pub_date = self._timestamp_to_date(api_data.get("last-published-at"))
                
                return self.create_article_item(
                    headline=api_data.get("headline"),
                    sub_title=api_data.get("subheadline"),
                    url=response.url,
                    article_body=body,
                    publication_date=pub_date,
                )
                
        except Exception as e:
            self.logger.debug(f"API data extraction error: {e}")
        
        return None
    
    def _extract_from_html(self, response: Response) -> Optional[NewsArticleItem]:
        """HTML parsing fallback."""
        try:
            headline = response.css('h1::text').get()
            body = " ".join(response.css('div.story-content p::text, article p::text').getall())
            
            if headline and body and len(body) > 50:
                return self.create_article_item(
                    headline=headline,
                    url=response.url,
                    article_body=body,
                    publication_date="Unknown",
                )
        except Exception as e:
            self.logger.debug(f"HTML extraction error: {e}")
        
        return None
    
    def _create_item_from_jsonld(self, data: Dict, response: Response) -> NewsArticleItem:
        """Create item from JSON-LD data."""
        # Extract authors
        authors = data.get("author", [])
        if isinstance(authors, list):
            author_names = [
                a.get("name", "Unknown") if isinstance(a, dict) else str(a)
                for a in authors
            ]
            author = ", ".join(author_names) if author_names else "Unknown"
        elif isinstance(authors, dict):
            author = authors.get("name", "Unknown")
        else:
            author = str(authors) if authors else "Unknown"
        
        # Extract image URL
        image_data = data.get("image")
        image_url = None
        if isinstance(image_data, list) and image_data:
            if isinstance(image_data[0], dict):
                image_url = image_data[0].get("url")
            elif isinstance(image_data[0], str):
                image_url = image_data[0]
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
            publisher=data.get("publisher", {}).get("name", "Prothom Alo"),
        )
