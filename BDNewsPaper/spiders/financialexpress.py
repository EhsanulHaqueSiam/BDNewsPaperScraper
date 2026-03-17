"""
The Financial Express Spider
==============================
Scrapes English news articles from The Financial Express.

Website Structure:
    - Standard HTML pagination
    - Category-based URL structure
    - Article URLs with slugs

Features:
    - Category-based scraping
    - HTML pagination
    - Client-side date filtering
"""

import json
from datetime import datetime
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector
from w3lib.html import remove_tags
from html import unescape


class FinancialExpressSpider(BaseNewsSpider):
    """
    The Financial Express scraper using HTML pagination.
    
    Usage:
        scrapy crawl financialexpress -a start_date=2024-12-01 -a end_date=2024-12-25
        scrapy crawl financialexpress -a categories=national,economy,stock
    """
    
    name = "financialexpress"
    paper_name = "The Financial Express"
    allowed_domains = ["thefinancialexpress.com.bd"]
    
    # API capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    supports_keyword_search = False
    
    # Custom settings
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.5,
        'AUTOTHROTTLE_MAX_DELAY': 3.0,
    }
    
    BASE_URL = "https://thefinancialexpress.com.bd"
    
    # Category mappings
    CATEGORIES = {
        "national": "national",
        "politics": "national/politics",
        "country": "national/country",
        "crime": "national/crime",
        "economy": "economy",
        "bangladesh": "economy/bangladesh",
        "global": "economy/global",
        "stock": "stock",
        "trade": "trade",
        "world": "world",
        "views": "views",
        "editorial": "views/editorial",
        "sports": "sports",
        "lifestyle": "lifestyle",
        "education": "education",
        "sci-tech": "sci-tech",
    }
    
    DEFAULT_CATEGORIES = ["national", "economy", "stock", "trade"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_urls_seen = set()
        
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
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.thefinancialexpress.com.bd/feed',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

        # Supplementary: News sitemap for date-filtered discovery
        self.stats['requests_made'] += 1
        yield Request(
            url='https://www.thefinancialexpress.com.bd/news-sitemap.xml',
            callback=self.parse_sitemap,
            headers={'Accept': 'application/xml, text/xml'},
            errback=self.handle_request_failure,
            meta={'source': 'sitemap'},
        )

    def _generate_fallback_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate fallback category requests."""
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
        
        # Find article links
        article_links = response.css(
            'article a::attr(href), '
            '.news-item a::attr(href), '
            'h2 a::attr(href), '
            'h3 a::attr(href), '
            '.hotnews a::attr(href)'
        ).getall()
        
        # Filter to unique article URLs
        seen_urls = set()
        valid_links = []
        for link in article_links:
            if not link or link in seen_urls:
                continue
            
            # Skip non-article links
            if '/page/' in link or link.endswith('/'):
                continue
            
            full_url = link if link.startswith('http') else f"{self.BASE_URL}{link}"
            
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
    

    # ================================================================
    # RSS Feed Parsing (Primary Source)
    # ================================================================

    def parse_rss(self, response):
        """Parse RSS feed XML to extract articles."""
        sel = Selector(response)
        sel.remove_namespaces()
        items = sel.xpath('//item')

        self.logger.info(f"RSS feed: Found {len(items)} items")

        rss_yielded = 0

        for item in items:
            headline = item.xpath('title/text()').get('').strip()
            url = item.xpath('link/text()').get('').strip()
            pub_date_str = item.xpath('pubDate/text()').get('').strip()
            author = item.xpath('creator/text()').get('').strip()
            body_html = item.xpath('encoded/text()').get('')
            description = item.xpath('description/text()').get('').strip()
            category = item.xpath('category/text()').get('General').strip()

            if not url:
                continue

            self._rss_urls_seen.add(url)

            if self.is_url_in_db(url):
                continue

            # Clean HTML from body
            body = ''
            if body_html:
                body = remove_tags(body_html).strip()

            # Date filtering
            if pub_date_str:
                parsed_date = self._parse_date_string(pub_date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            # Search query filter
            if headline and body:
                if not self.filter_by_search_query(headline, body):
                    continue

            if headline and body and len(body) > 100:
                # Full article available from RSS
                self.stats['articles_found'] += 1
                self.stats['articles_processed'] += 1
                rss_yielded += 1

                yield self.create_article_item(
                    url=url,
                    headline=unescape(headline),
                    article_body=body,
                    publication_date=pub_date_str if pub_date_str else None,
                    author=author if author else None,
                    category=category,
                )
            elif headline and url:
                # RSS item lacks full body -- visit article page
                self.stats['articles_found'] += 1
                self.stats['requests_made'] += 1
                yield Request(
                    url=url,
                    callback=self.parse_article,
                    meta={'category': category},
                    errback=self.handle_request_failure,
                )

        self.logger.info(f"RSS feed: Yielded {rss_yielded} complete articles directly")

        # If RSS returned few items, also launch category fallback
        if len(items) < 5:
            self.logger.info("RSS returned few items, launching category fallback")
            yield from self._generate_fallback_requests()

    def _rss_failed(self, failure):
        """If RSS fails, fall back to existing scraping."""
        self.logger.warning(f"RSS feed failed: {failure.value}. Falling back to category scraping.")
        self.stats['errors'] += 1
        yield from self._generate_fallback_requests()


    # ================================================================
    # Sitemap Parsing (Supplementary Source)
    # ================================================================

    def parse_sitemap(self, response):
        """Parse news sitemap XML for date-filtered article discovery."""
        sel = Selector(response)
        sel.remove_namespaces()
        urls = sel.xpath('//url')

        self.logger.info(f"Sitemap: Found {len(urls)} URLs")

        sitemap_count = 0

        for url_node in urls:
            loc = url_node.xpath('loc/text()').get('').strip()
            lastmod = url_node.xpath('lastmod/text()').get('').strip()
            pub_date = url_node.xpath('news/publication_date/text()').get('').strip()

            if not loc:
                continue

            # Skip if already seen via RSS
            if hasattr(self, '_rss_urls_seen') and loc in self._rss_urls_seen:
                continue

            if self.is_url_in_db(loc):
                continue

            # Date filter on lastmod or pub_date
            date_str = pub_date or lastmod
            if date_str:
                parsed_date = self._parse_date_string(date_str)
                if parsed_date and not self.is_date_in_range(parsed_date):
                    self.stats['date_filtered'] += 1
                    continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            sitemap_count += 1

            yield Request(
                url=loc,
                callback=self.parse_article,
                meta={'category': 'General'},
                errback=self.handle_request_failure,
            )

        self.logger.info(f"Sitemap: Queued {sitemap_count} articles for scraping")

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
                    publisher="The Financial Express",
                )
                
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return None
    
    def _extract_from_html(self, response: Response) -> Optional[NewsArticleItem]:
        """Extract article data from HTML."""
        try:
            # Headline
            headline = (
                response.css('h1.news-title::text').get() or
                response.css('article h1::text').get() or
                response.css('h1::text').get()
            )
            
            if not headline:
                return None
            
            headline = headline.strip()
            
            # Body
            body_parts = response.css(
                '.news-content p::text, '
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
                publisher="The Financial Express",
            )
            
        except Exception as e:
            self.logger.debug(f"HTML extraction error: {e}")
            return None
