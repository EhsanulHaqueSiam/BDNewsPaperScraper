"""
The Daily Star Spider (Enhanced)
=================================
Scrapes English news articles from The Daily Star.

Website Structure:
    - Framework: Drupal 7
    - Pagination: ?page=X query parameter
    - RSS Feed: /rss.xml for structured data
    - Search: Google Custom Search at /search?t={query}

Features:
    - Standard HTML pagination with ?page=X
    - RSS feed support for efficient article discovery
    - JSON-LD structured data extraction (NewsArticle schema)
    - Multiple content extraction strategies
    - Category-based scraping
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlencode, quote

import scrapy
from scrapy.http import Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class TheDailyStarSpider(BaseNewsSpider):
    """
    The Daily Star scraper with Drupal pagination and JSON-LD support.
    
    Usage:
        scrapy crawl thedailystar -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl thedailystar -a categories=Bangladesh,Sports,Business
        scrapy crawl thedailystar -a use_rss=true
    """
    
    name = "thedailystar"
    paper_name = "The Daily Star"
    allowed_domains = ["thedailystar.net", "www.thedailystar.net"]
    
    # API capabilities
    supports_api_date_filter = False  # Date filtering done client-side
    supports_api_category_filter = True
    supports_keyword_search = True  # Via Google CSE
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.5,
        'AUTOTHROTTLE_MAX_DELAY': 5.0,
    }
    
    # Base URLs
    BASE_URL = "https://www.thedailystar.net"
    RSS_URL = "https://www.thedailystar.net/rss.xml"
    
    # Category mappings (name -> URL path)
    CATEGORIES = {
        # News Categories
        "Bangladesh": "news/bangladesh",
        "Politics": "news/bangladesh/politics",
        "Crime": "news/bangladesh/crime-justice",
        "Governance": "news/bangladesh/governance",
        "Coronavirus": "news/coronavirus",
        "World": "world",
        "Asia": "world/asia",
        "Europe": "world/europe",
        "Americas": "world/americas",
        "MiddleEast": "world/middle-east",
        
        # Other Categories
        "Business": "business",
        "Economy": "business/economy",
        "Banks": "business/economy/banks",
        "StockMarket": "business/economy/stock",
        "Sports": "sports",
        "Cricket": "sports/cricket",
        "Football": "sports/football",
        "Opinion": "opinion",
        "Editorial": "opinion/editorial",
        "Entertainment": "lifestyle/entertainment",
        "Arts": "lifestyle/arts-culture",
        "Tech": "tech-startup",
        "Science": "environment/science",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # RSS mode
        self.use_rss = kwargs.get('use_rss', 'false').lower() == 'true'
        
        # Track pagination for stopping
        self.consecutive_old_articles = {}
        self.max_consecutive_old = 5
        
        # Setup categories
        self._setup_categories()
        
        self.logger.info(f"Categories: {list(self.category_map.keys())}")
        self.logger.info(f"Use RSS: {self.use_rss}")
    
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
        if self.use_rss:
            # RSS feed mode for broader coverage
            yield scrapy.Request(
                url=self.RSS_URL,
                callback=self.parse_rss,
                meta={"request_type": "rss"},
                errback=self.handle_request_failure,
            )
        else:
            # Category-based scraping
            for category, path in self.category_map.items():
                self.consecutive_old_articles[category] = 0
                yield self._make_category_request(category, path, page=0)
    
    def _make_category_request(
        self, category: str, path: str, page: int = 0
    ) -> scrapy.Request:
        """Create request for category page."""
        # Drupal uses 0-indexed pages
        url = f"{self.BASE_URL}/{path}"
        if page > 0:
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
    # RSS Parsing
    # ================================================================
    
    def parse_rss(self, response: Response) -> Generator:
        """Parse RSS feed for articles."""
        try:
            # Parse XML
            root = ET.fromstring(response.text)
            
            # Find all items (RSS 2.0 format)
            items = root.findall('.//item')
            
            self.logger.info(f"RSS feed: Found {len(items)} items")
            
            for item in items:
                # Extract from RSS item
                title = item.findtext('title', '')
                link = item.findtext('link', '')
                description = item.findtext('description', '')
                pub_date = item.findtext('pubDate', '')
                
                if not link:
                    continue
                
                # Check date
                if pub_date and not self._is_date_valid(pub_date):
                    continue
                
                if not self.is_url_in_db(link):
                    self.stats['articles_found'] += 1
                    
                    yield scrapy.Request(
                        url=link,
                        callback=self.parse_article,
                        meta={
                            "category": "RSS",
                            "rss_title": title,
                            "rss_description": description,
                            "rss_date": pub_date,
                        },
                        errback=self.handle_request_failure,
                    )
                    
        except ET.ParseError as e:
            self.logger.error(f"RSS parse error: {e}")
            self.stats['errors'] += 1
    
    # ================================================================
    # Category Page Parsing
    # ================================================================
    
    def parse_category_page(self, response: Response) -> Generator:
        """Parse category listing page."""
        category = response.meta["category"]
        path = response.meta["category_path"]
        page = response.meta["page"]
        
        # Find article links - Daily Star uses various article card formats
        articles = response.css('.card, .news-box, .panel-body article, .col-lg-12 article')
        
        if not articles:
            # Alternative selectors
            articles = response.css('article, .story, .story-box')
        
        self.logger.info(f"Category '{category}' page {page}: Found {len(articles)} articles")
        
        old_article_count = 0
        
        for article in articles:
            # Extract link
            link = article.css('a::attr(href)').get()
            
            if not link:
                continue
            
            full_url = f"{self.BASE_URL}{link}" if not link.startswith('http') else link
            
            # Skip non-article links
            if '/news/' not in full_url and '/opinion/' not in full_url \
               and '/business/' not in full_url and '/sports/' not in full_url \
               and '/lifestyle/' not in full_url and '/tech' not in full_url:
                continue
            
            # Extract date if available for early filtering
            date_el = article.css('time::attr(datetime)').get() or \
                      article.css('.time::text, .date::text').get()
            
            if date_el and not self._is_date_valid(date_el):
                if self._is_before_start(date_el):
                    old_article_count += 1
                continue
            
            if not self.is_url_in_db(full_url):
                self.stats['articles_found'] += 1
                
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_article,
                    meta={
                        "category": category,
                        "list_date": date_el,
                    },
                    errback=self.handle_request_failure,
                )
        
        # Track consecutive old articles for stopping
        if old_article_count > len(articles) / 2:
            self.consecutive_old_articles[category] = \
                self.consecutive_old_articles.get(category, 0) + 1
        else:
            self.consecutive_old_articles[category] = 0
        
        # Stop if too many consecutive pages with old articles
        if self.consecutive_old_articles[category] >= self.max_consecutive_old:
            self.logger.info(f"Stopping {category}: Too many old articles")
            return
        
        # Pagination - look for "More" link or next page
        next_page = page + 1
        
        if articles and next_page < self.max_pages:
            # Check for pagination link
            more_link = response.css('a[href*="?page="]::attr(href)').get()
            
            if more_link or len(articles) >= 10:
                yield self._make_category_request(category, path, next_page)
    
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
            '%Y-%m-%dT%H:%M:%S%z',  # ISO format with timezone
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%a, %d %b %Y %H:%M:%S %z',  # RSS format
            '%a, %d %b %Y %H:%M:%S',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B, %Y',
        ]
        
        # Clean timezone offset format if present
        clean_date = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', date_str.strip())
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        
        # Try without timezone
        clean_date = re.sub(r'[+-]\d{2}:?\d{2}$', '', date_str.strip())
        for fmt in formats:
            try:
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        
        return None
    
    # ================================================================
    # Article Parsing
    # ================================================================
    
    def parse_article(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page."""
        self.stats['articles_processed'] += 1
        
        category = response.meta.get("category", "Unknown")
        
        # Strategy 1: JSON-LD structured data (most reliable)
        item = self._extract_from_jsonld(response)
        
        # Strategy 2: HTML parsing
        if not item:
            item = self._extract_from_html(response)
        
        # Strategy 3: Meta tags
        if not item:
            item = self._extract_from_meta(response)
        
        if item:
            # Override category if more specific one found
            if category and category != "RSS":
                item['category'] = category
            
            # Validate date is in range (final check)
            pub_date = item.get('publication_date', '')
            if pub_date and pub_date != 'Unknown':
                if not self._is_date_valid(pub_date):
                    self.logger.debug(f"Skipping article outside date range: {response.url}")
                    return
            
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
                
                # Handle array format
                if isinstance(data, list):
                    data = next(
                        (item for item in data 
                         if item.get("@type") in ["Article", "NewsArticle", "WebPage"]),
                        None
                    )
                    if not data:
                        continue
                
                # Check for NewsArticle type
                item_type = data.get("@type", "")
                if item_type not in ["Article", "NewsArticle", "WebPage"]:
                    continue
                
                return self._create_item_from_jsonld(data, response)
                
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return None
    
    def _extract_from_html(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract from HTML selectors."""
        try:
            # Headline - multiple strategies
            headline = (
                response.css('h1.title::text').get() or
                response.css('article h1::text').get() or
                response.css('.article-title::text').get() or
                response.css('h1::text').get()
            )
            
            if not headline:
                return None
            
            # Body extraction - The Daily Star article body
            body_parts = []
            
            # Strategy 1: Article body div
            body_parts.extend(
                response.css('.article-body p::text, .story-body p::text').getall()
            )
            
            # Strategy 2: Main content area
            if not body_parts:
                body_parts.extend(
                    response.css('.field-item p::text, .content p::text').getall()
                )
            
            # Strategy 3: Generic article paragraphs
            if not body_parts:
                body_parts.extend(response.css('article p::text').getall())
            
            body = " ".join(p.strip() for p in body_parts if p.strip())
            
            if not body or len(body) < 50:
                return None
            
            # Extract other fields
            pub_date = (
                response.css('time::attr(datetime)').get() or
                response.css('meta[property="article:published_time"]::attr(content)').get() or
                response.css('.date::text, .time::text').get() or
                "Unknown"
            )
            
            mod_date = response.css(
                'meta[property="article:modified_time"]::attr(content)'
            ).get()
            
            author = (
                response.css('.author-name::text, .byline a::text').get() or
                response.css('meta[name="author"]::attr(content)').get() or
                "Unknown"
            )
            
            # Sub-title / description
            sub_title = (
                response.css('.article-lead::text, .lead::text').get() or
                response.css('meta[property="og:description"]::attr(content)').get()
            )
            
            # Image
            image_url = (
                response.css('meta[property="og:image"]::attr(content)').get() or
                response.css('.featured-image img::attr(src)').get() or
                response.css('article img::attr(src)').get()
            )
            
            # Keywords / Tags
            keywords = response.css('.tags a::text, .article-tags a::text').getall()
            keywords_str = ", ".join(k.strip() for k in keywords if k.strip())
            
            return self.create_article_item(
                headline=headline.strip(),
                article_body=body,
                url=response.url,
                sub_title=sub_title.strip() if sub_title else None,
                publication_date=pub_date,
                modification_date=mod_date if mod_date else None,
                author=author.strip() if author != "Unknown" else None,
                image_url=image_url,
                keywords=keywords_str if keywords_str else None,
            )
            
        except Exception as e:
            self.logger.debug(f"HTML extraction error: {e}")
            return None
    
    def _extract_from_meta(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract from meta tags (fallback)."""
        try:
            title = (
                response.css('meta[property="og:title"]::attr(content)').get() or
                response.css('title::text').get()
            )
            
            description = response.css(
                'meta[property="og:description"]::attr(content)'
            ).get()
            
            if not title or not description:
                return None
            
            return self.create_article_item(
                headline=title.strip(),
                article_body=description.strip(),
                url=response.url,
                publication_date=response.css(
                    'meta[property="article:published_time"]::attr(content)'
                ).get() or "Unknown",
                image_url=response.css(
                    'meta[property="og:image"]::attr(content)'
                ).get(),
            )
            
        except Exception as e:
            self.logger.debug(f"Meta extraction error: {e}")
            return None
    
    def _create_item_from_jsonld(
        self, data: Dict, response: Response
    ) -> NewsArticleItem:
        """Create item from JSON-LD data."""
        # Extract headline
        headline = data.get("headline") or data.get("name", "No headline")
        
        # Extract body - may be in articleBody or description
        body = data.get("articleBody", "")
        if not body:
            body = data.get("description", "")
        
        # Extract authors
        authors = data.get("author", [])
        if isinstance(authors, list):
            author_names = [
                a.get("name", "") if isinstance(a, dict) else str(a)
                for a in authors
            ]
            author = ", ".join(filter(None, author_names)) or None
        elif isinstance(authors, dict):
            author = authors.get("name")
        else:
            author = str(authors) if authors else None
        
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
        
        # Extract publisher
        publisher = data.get("publisher", {})
        publisher_name = None
        if isinstance(publisher, dict):
            publisher_name = publisher.get("name")
        
        # Extract keywords
        keywords = data.get("keywords")
        if isinstance(keywords, list):
            keywords = ", ".join(str(k) for k in keywords)
        
        # Extract dates
        pub_date = data.get("datePublished", "Unknown")
        mod_date = data.get("dateModified")
        
        # Description as subtitle
        description = data.get("description", "")
        
        return self.create_article_item(
            headline=headline,
            article_body=body if body else description,
            url=data.get("mainEntityOfPage", {}).get("@id") if isinstance(
                data.get("mainEntityOfPage"), dict
            ) else (data.get("url") or response.url),
            sub_title=description if body else None,
            publication_date=pub_date,
            modification_date=mod_date,
            author=author,
            image_url=image_url,
            keywords=keywords,
            publisher=publisher_name or "The Daily Star",
        )