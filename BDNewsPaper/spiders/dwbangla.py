"""
DW Bangla Spider
================
Scrapes articles from DW Bengali (dw.com/bn) - Deutsche Welle Bengali Service

Features:
    - Embedded JSON extraction from window.__APP_STATE__
    - GraphQL-like data structure parsing
    - Category/topic support
    - Full article content extraction
"""

import json
import re
from datetime import datetime
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class DWBanglaSpider(BaseNewsSpider):
    """
    Spider for DW (Deutsche Welle) Bengali Service.
    
    Uses embedded __APP_STATE__ JSON for article listings and content.
    
    Usage:
        scrapy crawl dwbangla
        scrapy crawl dwbangla -a max_pages=5
        scrapy crawl dwbangla -a categories=politics,world
    """
    
    name = 'dwbangla'
    paper_name = 'DW Bangla'
    allowed_domains = ['dw.com', 'www.dw.com']
    language = 'Bangla'
    
    # Base URL
    BASE_URL = 'https://www.dw.com/bn'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Topic paths for categories
    CATEGORIES = {
        'all': '',
        'bangladesh': 'বাংলাদেশ',
        'world': 'বিশ্ব',
        'science': 'বিজ্ঞান-প্রযুক্তি',
        'culture': 'সংস্কৃতি-জীবনধারা',
        'sports': 'খেলা',
        'opinion': 'মতামত-বিশ্লেষণ',
    }
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
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
        self.logger.info(f"DW Bangla spider initialized")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests for homepage and categories."""
        self.stats['requests_made'] = 0
        
        # Start with homepage to get all category content
        self.logger.info("Crawling DW Bangla homepage")
        self.stats['requests_made'] += 1
        
        yield Request(
            url=self.BASE_URL,
            callback=self.parse_homepage,
            meta={'page': 1},
            errback=self.handle_request_failure,
        )
    
    def parse_homepage(self, response: Response) -> Generator:
        """Parse homepage using __APP_STATE__ JSON."""
        page = response.meta.get('page', 1)
        
        # Extract __APP_STATE__ from script
        app_state = self._extract_app_state(response)
        
        if not app_state:
            self.logger.error(f"No __APP_STATE__ found on {response.url}")
            return
        
        articles_found = 0
        
        # Find content data - look for navigation key containing articles
        for key, value in app_state.items():
            if not isinstance(value, dict) or 'data' not in value:
                continue
            
            content = value.get('data', {}).get('content', {})
            composition = content.get('contentComposition', {})
            info_spaces = composition.get('informationSpaces', [])
            
            for space in info_spaces:
                contents = space.get('contents', [])
                
                for item in contents:
                    article_type = item.get('__typename', '')
                    
                    # Only process articles
                    if article_type not in ('Article', 'Video', 'Liveblog'):
                        continue
                    
                    # Get article URL
                    named_url = item.get('namedUrl', '')
                    if not named_url:
                        continue
                    
                    article_url = f"https://www.dw.com{named_url}"
                    
                    # Skip if already in DB
                    if self.is_url_in_db(article_url):
                        continue
                    
                    headline = item.get('title', '')
                    if not headline:
                        continue
                    
                    teaser = item.get('teaser', '')
                    
                    # Get publication date
                    pub_date_str = item.get('contentDate', '')
                    pub_date = self._parse_date_string(pub_date_str)
                    
                    # Date filter
                    if pub_date and not self.is_date_in_range(pub_date):
                        self.stats['date_filtered'] += 1
                        continue
                    
                    articles_found += 1
                    self.stats['articles_found'] += 1
                    
                    # Request full article for complete content
                    self.stats['requests_made'] += 1
                    yield Request(
                        url=article_url,
                        callback=self.parse_article,
                        meta={
                            'headline': headline,
                            'teaser': teaser,
                            'pub_date': pub_date,
                        },
                        errback=self.handle_request_failure,
                    )
        
        self.logger.info(f"Found {articles_found} articles on DW Bangla homepage")
    
    def parse_article(self, response: Response) -> Generator:
        """Parse individual article page for full content."""
        headline = response.meta.get('headline', '')
        teaser = response.meta.get('teaser', '')
        pub_date = response.meta.get('pub_date')
        
        # Extract __APP_STATE__ for article content
        app_state = self._extract_app_state(response)
        
        article_body = ''
        author = None
        category = None
        image_url = None
        
        if app_state:
            # Find article content key
            for key, value in app_state.items():
                if '/content/article/' not in key:
                    continue
                
                if not isinstance(value, dict) or 'data' not in value:
                    continue
                
                content = value.get('data', {}).get('content', {})
                
                # Get full text (HTML)
                text_html = content.get('text', '')
                if text_html:
                    article_body = self._clean_html_content(text_html)
                
                # Get headline if not already set
                if not headline:
                    headline = content.get('title', '')
                
                # Get author
                authors = content.get('firstPersonArray', [])
                if authors:
                    author_names = [a.get('name', '') for a in authors if a.get('name')]
                    author = ', '.join(author_names) if author_names else None
                
                # Get category
                topics = content.get('topStoryTopic', {})
                if topics:
                    category = topics.get('name', '')
                
                # Get image
                main_image = content.get('mainContentImageLink', {})
                if main_image:
                    image_url = main_image.get('target', {}).get('staticUrl', '')
                
                # Get date if not parsed earlier
                if not pub_date:
                    pub_date_str = content.get('contentDate', '')
                    pub_date = self._parse_date_string(pub_date_str)
                
                break
        
        # If no body from JSON, try to extract from HTML
        if not article_body:
            article_body = self._extract_body_from_html(response)
        
        # Use teaser if body still empty
        if not article_body and teaser:
            article_body = teaser
        
        if not headline or len(article_body) < 50:
            self.logger.debug(f"Article incomplete: {response.url}")
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
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
    
    def _extract_app_state(self, response: Response) -> Optional[dict]:
        """Extract __APP_STATE__ from script tag."""
        # Look for window.__APP_STATE__ assignment
        pattern = r'window\.__APP_STATE__\s*=\s*(\{.+?\})\s*;\s*(?:window\.|</script>)'
        match = re.search(pattern, response.text, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                self.logger.debug(f"Failed to parse __APP_STATE__: {e}")
        
        # Alternative: look for script tag content
        scripts = response.css('script::text').getall()
        for script in scripts:
            if '__APP_STATE__' in script:
                match = re.search(r'__APP_STATE__\s*=\s*(\{.+?\})\s*;', script, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        continue
        
        return None
    
    def _clean_html_content(self, html: str) -> str:
        """Clean HTML content to extract text."""
        # Remove script and style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace paragraph and block elements with newlines
        html = re.sub(r'<(?:p|div|br|li|h[1-6])[^>]*>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</(?:p|div|li|h[1-6])>', '\n', html, flags=re.IGNORECASE)
        
        # Remove all other tags
        html = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        text = unescape(html)
        
        # Normalize whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()
        
        return text
    
    def _extract_body_from_html(self, response: Response) -> str:
        """Extract article body from HTML as fallback."""
        # Try common article body selectors
        selectors = [
            'div.rich-text',
            'article .content-body',
            'div[data-tracking-name="news-main-text"]',
            'div.article-body',
        ]
        
        for selector in selectors:
            body = response.css(f'{selector}').get()
            if body:
                return self._clean_html_content(body)
        
        return ''
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date from DW format."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # DW uses ISO 8601 format
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
        ]
        
        # Remove Z and add UTC offset for parsing
        clean_date = date_str.replace('Z', '+00:00')
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return self.dhaka_tz.localize(dt)
            except ValueError:
                continue
        
        # Try with fromisoformat for newer Python
        try:
            dt = datetime.fromisoformat(clean_date)
            return self.dhaka_tz.localize(dt.replace(tzinfo=None))
        except ValueError:
            pass
        
        return None
