"""
VOA Bangla Spider
=================
Scrapes articles from Voice of America Bengali (voabangla.com)

Features:
    - RSS feed for article discovery
    - window.analyticsData extraction for metadata
    - JSON-LD structured data support
    - Full article content extraction
"""

import json
import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response, XmlResponse

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class VOABanglaSpider(BaseNewsSpider):
    """
    Spider for Voice of America Bengali Service.
    
    Uses RSS feed for article discovery and analyticsData for metadata.
    
    Usage:
        scrapy crawl voabangla
        scrapy crawl voabangla -a max_pages=5
    """
    
    name = 'voabangla'
    paper_name = 'VOA Bangla'
    allowed_domains = ['voabangla.com', 'www.voabangla.com']
    language = 'Bangla'
    
    # Base URLs
    BASE_URL = 'https://www.voabangla.com'
    RSS_URL = 'https://www.voabangla.com/api/z_yqyes$i_'  # Main RSS feed
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = False
    
    # Category RSS feeds (if available)
    CATEGORY_FEEDS = {
        'all': '/api/z_yqyes$i_',
        'bangladesh': '/api/zk_pvemovym',
        'usa': '/api/z-$y_qyqempt',
        'world': '/api/zmqt_qvvyi',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'AUTOTHROTTLE_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'bn,en;q=0.9',
        },
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"VOA Bangla spider initialized")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests for RSS feeds."""
        self.stats['requests_made'] = 0
        
        # Start with main RSS feed
        self.logger.info("Fetching VOA Bangla RSS feed")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=f"{self.BASE_URL}/api/",
            callback=self.parse_rss,
            meta={'page': 1},
            errback=self.handle_request_failure,
        )
    
    def parse_rss(self, response: Response) -> Generator:
        """Parse RSS feed to extract article URLs."""
        page = response.meta.get('page', 1)
        
        # Extract items from RSS
        # RSS uses namespaces, so we use XPath with local-name()
        items = response.xpath('//*[local-name()="item"]')
        
        if not items:
            # Try alternative RSS parsing
            items = response.css('item')
        
        articles_found = 0
        
        for item in items:
            # Get article URL
            link = item.xpath('link/text()').get()
            if not link:
                link = item.xpath('*[local-name()="link"]/text()').get()
            
            if not link:
                continue
            
            # Ensure full URL
            if link.startswith('/'):
                link = f"{self.BASE_URL}{link}"
            
            # Skip if already in DB
            if self.is_url_in_db(link):
                continue
            
            # Get title from RSS
            title = item.xpath('title/text()').get()
            if not title:
                title = item.xpath('*[local-name()="title"]/text()').get()
            title = title.strip() if title else ''
            
            # Get publication date from RSS
            pub_date_str = item.xpath('pubDate/text()').get()
            if not pub_date_str:
                pub_date_str = item.xpath('*[local-name()="pubDate"]/text()').get()
            
            pub_date = self._parse_rss_date(pub_date_str)
            
            # Date filter
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                continue
            
            # Get description/teaser
            description = item.xpath('description/text()').get()
            if not description:
                description = item.xpath('*[local-name()="description"]/text()').get()
            description = self._clean_html(description) if description else ''
            
            articles_found += 1
            self.stats['articles_found'] += 1
            
            # Request full article
            self.stats['requests_made'] += 1
            yield Request(
                url=link,
                callback=self.parse_article,
                meta={
                    'headline': title,
                    'teaser': description,
                    'pub_date': pub_date,
                },
                errback=self.handle_request_failure,
            )
        
        self.logger.info(f"Found {articles_found} articles in VOA Bangla RSS feed")
    
    def parse_article(self, response: Response) -> Generator:
        """Parse individual article page for full content."""
        headline = response.meta.get('headline', '')
        teaser = response.meta.get('teaser', '')
        pub_date = response.meta.get('pub_date')
        
        author = None
        category = None
        image_url = None
        
        # Extract analyticsData from script
        analytics_data = self._extract_analytics_data(response)
        
        if analytics_data:
            # Get headline if not already set
            if not headline:
                headline = analytics_data.get('page_title', '')
            
            # Get author
            author = analytics_data.get('byline', '')
            
            # Get category
            categories = analytics_data.get('categories', '')
            if categories:
                # Take first meaningful category
                cat_list = [c.strip() for c in categories.split(',') if c.strip()]
                category = cat_list[0] if cat_list else None
            
            # Get publication date
            if not pub_date:
                pub_date_str = analytics_data.get('pub_datetime', '')
                pub_date = self._parse_analytics_date(pub_date_str)
        
        # Try JSON-LD as fallback
        json_ld = self._extract_json_ld(response)
        if json_ld:
            if not headline:
                headline = json_ld.get('headline', '')
            if not author:
                author_data = json_ld.get('author', {})
                if isinstance(author_data, dict):
                    author = author_data.get('name', '')
                elif isinstance(author_data, list) and author_data:
                    author = author_data[0].get('name', '')
            if not image_url:
                image_url = json_ld.get('image', {}).get('url', '')
        
        # Extract article body
        article_body = self._extract_article_body(response)
        
        # Use teaser if body is empty
        if not article_body and teaser:
            article_body = teaser
        
        if not headline or len(article_body) < 50:
            self.logger.debug(f"Article incomplete: {response.url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        # Get image from meta if not found
        if not image_url:
            image_url = response.css('meta[property="og:image"]::attr(content)').get()
        
        self.stats['articles_processed'] += 1
        
        yield self.create_article_item(
            url=response.url,
            headline=headline,
            article_body=article_body,
            publication_date=pub_date.isoformat() if pub_date else None,
            category=category,
            author=author,
            image_url=image_url,
        )
    
    def _extract_analytics_data(self, response: Response) -> Optional[dict]:
        """Extract window.analyticsData from script tags."""
        # Look for analyticsData object in script
        pattern = r'window\.analyticsData\s*=\s*(\{[^;]+\})'
        
        scripts = response.css('script::text').getall()
        for script in scripts:
            if 'analyticsData' in script:
                match = re.search(pattern, script, re.DOTALL)
                if match:
                    try:
                        # Clean up the JSON - it may have trailing comments
                        json_str = match.group(1)
                        # Remove trailing comma before closing brace
                        json_str = re.sub(r',\s*}', '}', json_str)
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
        
        # Try alternative pattern
        pattern2 = r'analyticsData\s*:\s*(\{[^}]+\})'
        for script in scripts:
            match = re.search(pattern2, script, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _extract_json_ld(self, response: Response) -> Optional[dict]:
        """Extract JSON-LD structured data."""
        scripts = response.css('script[type="application/ld+json"]::text').getall()
        
        for script in scripts:
            try:
                data = json.loads(script)
                # Look for NewsArticle type
                if isinstance(data, dict):
                    if data.get('@type') == 'NewsArticle':
                        return data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'NewsArticle':
                            return item
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _extract_article_body(self, response: Response) -> str:
        """Extract article body from HTML."""
        # VOA uses .wsw class for article content
        selectors = [
            '#article-content .wsw',
            'div.body-container .wsw',
            'div.wsw',
            'div[itemprop="articleBody"]',
            '.article__body',
        ]
        
        for selector in selectors:
            container = response.css(selector)
            if container:
                # Get all paragraph text
                paragraphs = container.css('p::text, p *::text').getall()
                if paragraphs:
                    text = ' '.join(p.strip() for p in paragraphs if p.strip())
                    if text:
                        return text
                
                # Fallback: get all text
                all_text = container.css('::text').getall()
                if all_text:
                    text = ' '.join(t.strip() for t in all_text if t.strip())
                    if text:
                        return text
        
        return ''
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML content to extract text."""
        if not html:
            return ''
        
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode entities
        text = unescape(text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from RSS format."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # RSS uses RFC 822 format: "Mon, 14 Mar 2025 20:25:27 +0000"
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt.replace(tzinfo=None))
            except ValueError:
                continue
        
        return None
    
    def _parse_analytics_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from analyticsData format."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Format: "2025-03-14 20:25:27Z"
        formats = [
            '%Y-%m-%d %H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        return None
