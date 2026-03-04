"""
Auto News Spider - Universal Self-Healing Spider (Enhanced)
============================================================
A fully automatic spider that works on ANY news website without
custom selectors. Uses pattern-based link discovery and fallback extraction.

Features:
    - Pattern-based link discovery (no CSS selectors needed)
    - JSON-LD + generic selector extraction chain
    - Automatic pagination detection
    - Aggressive retry on failures
    - Multiple content extraction attempts

Usage:
    # Run on any news site
    scrapy crawl autonews -a url=https://example.com/news
    
    # Multiple sites
    scrapy crawl autonews -a urls="https://site1.com,https://site2.com"
    
    # With max pages limit
    scrapy crawl autonews -a url=https://example.com -a max_pages=10
"""

from typing import Generator
from urllib.parse import urlparse, urljoin
import re

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from BDNewsPaper.link_discovery import ArticleLinkDiscovery


class AutoNewsSpider(BaseNewsSpider):
    """
    Universal self-healing news spider (Enhanced).
    
    Works on ANY news website without custom CSS selectors.
    Uses pattern-based URL discovery and multi-layer extraction.
    """
    
    name = 'autonews'
    paper_name = 'Auto News'
    
    # Enhanced settings for robustness
    custom_settings = {
        'DOWNLOAD_DELAY': 1.5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'CONCURRENT_REQUESTS': 8,
        'AUTOTHROTTLE_ENABLED': True,
        'DOWNLOAD_TIMEOUT': 180,  # 3 minute timeout
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],
        'HTTPCACHE_ENABLED': False,  # Fresh requests
    }
    
    def __init__(self, url: str = None, urls: str = None, max_pages: int = 50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.start_urls = []
        self.max_listing_pages = int(max_pages)
        
        # Support single URL or comma-separated URLs
        if url:
            self.start_urls.append(url.strip())
        if urls:
            self.start_urls.extend([u.strip() for u in urls.split(',') if u.strip()])
        
        # Initialize link discoverer
        self.link_discoverer = ArticleLinkDiscovery()
        
        # Track visited pages for pagination
        self.visited_listing_pages = set()
        self.listing_page_counts = {}  # domain -> page count
        
        # Track extraction stats
        self.extraction_stats = {
            'jsonld_success': 0,
            'generic_success': 0,
            'failed': 0,
        }
        
        self.logger.info(f"AutoNewsSpider initialized with {len(self.start_urls)} URLs, max_pages={self.max_listing_pages}")
    
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests."""
        for url in self.start_urls:
            # Determine paper name from domain
            domain = urlparse(url).netloc.replace('www.', '')
            self.paper_name = domain.split('.')[0].title()
            self.allowed_domains = [domain, f'www.{domain}']
            
            self.listing_page_counts[domain] = 0
            
            self.logger.info(f"Starting auto-scrape of: {url} (domain: {domain})")
            
            yield Request(
                url=url,
                callback=self.parse_listing,
                errback=self.handle_request_failure,
                meta={'is_listing': True, 'domain': domain},
                dont_filter=True,
            )
    
    def parse_listing(self, response: Response) -> Generator:
        """Parse listing/index page - discover article links automatically."""
        url = response.url
        domain = response.meta.get('domain', urlparse(url).netloc.replace('www.', ''))
        
        if url in self.visited_listing_pages:
            return
        self.visited_listing_pages.add(url)
        
        # Track pages per domain
        self.listing_page_counts[domain] = self.listing_page_counts.get(domain, 0) + 1
        
        if self.listing_page_counts[domain] > self.max_listing_pages:
            self.logger.info(f"Reached max pages ({self.max_listing_pages}) for {domain}")
            return
        
        # Discover article links using pattern-based detection
        discovered_links = self.link_discoverer.discover_links(response)
        
        # Also try universal discover_links from base spider
        if not discovered_links:
            discovered_links = [{'url': u, 'text': '', 'score': 0} for u in self.discover_links(response, limit=100)]
        
        self.logger.info(f"Page {self.listing_page_counts[domain]}: Found {len(discovered_links)} article links on {url}")
        
        article_count = 0
        
        for link_info in discovered_links:
            article_url = link_info['url'] if isinstance(link_info, dict) else link_info
            
            # Skip if already in database
            if self.is_url_in_db(article_url):
                continue
            
            self.stats['articles_found'] += 1
            article_count += 1
            
            yield Request(
                url=article_url,
                callback=self.parse_article,
                errback=self.handle_request_failure,
                meta={
                    'link_text': link_info.get('text', '') if isinstance(link_info, dict) else '',
                    'link_score': link_info.get('score', 0) if isinstance(link_info, dict) else 0,
                    'domain': domain,
                },
            )
        
        self.logger.info(f"Yielded {article_count} new article requests from {url}")
        
        # Try to find pagination links
        if article_count > 0 and self.listing_page_counts[domain] < self.max_listing_pages:
            for next_url in self._find_pagination_links(response):
                if next_url not in self.visited_listing_pages:
                    yield Request(
                        url=next_url,
                        callback=self.parse_listing,
                        errback=self.handle_request_failure,
                        meta={'is_listing': True, 'domain': domain},
                    )
    
    def _find_pagination_links(self, response: Response) -> list:
        """Find pagination links (next page, page 2, etc.)."""
        pagination_links = []
        base_url = response.url
        
        # Common pagination patterns
        selectors = [
            'a.next::attr(href)',
            'a.pagination-next::attr(href)',
            'a[rel="next"]::attr(href)',
            '.pagination a::attr(href)',
            '.pager a::attr(href)',
            'a[href*="page="]::attr(href)',
            'a[href*="/page/"]::attr(href)',
            '.load-more a::attr(href)',
            'a:contains("Next")::attr(href)',
            'a:contains("পরবর্তী")::attr(href)',  # Bengali "next"
        ]
        
        for selector in selectors:
            try:
                links = response.css(selector).getall()
                for link in links:
                    if link:
                        full_url = urljoin(base_url, link)
                        if full_url not in pagination_links:
                            pagination_links.append(full_url)
            except Exception:
                pass
        
        # Also check for page=N patterns in URL
        if 'page=' in base_url or '/page/' in base_url:
            # Try incrementing page number
            new_url = re.sub(r'page[=/](\d+)', lambda m: f'page={int(m.group(1))+1}', base_url)
            if new_url != base_url and new_url not in pagination_links:
                pagination_links.append(new_url)
        
        return pagination_links[:3]  # Limit to 3 pagination links per page
    
    def parse_article(self, response: Response) -> Generator:
        """Parse article page - universal extraction with fallback chain."""
        url = response.url
        domain = response.meta.get('domain', urlparse(url).netloc.replace('www.', ''))
        
        # Try primary extraction (JSON-LD + generic selectors)
        extracted = self.extract_article_fallback(response)
        
        if extracted and extracted.get('headline') and extracted.get('article_body'):
            if len(extracted.get('article_body', '')) >= 50:
                self.extraction_stats['jsonld_success'] += 1
                yield from self._yield_article(response, extracted, domain)
                return
        
        # Second attempt: try generic selectors more aggressively
        extracted = self._aggressive_extraction(response)
        
        if extracted and extracted.get('headline') and extracted.get('article_body'):
            if len(extracted.get('article_body', '')) >= 50:
                self.extraction_stats['generic_success'] += 1
                yield from self._yield_article(response, extracted, domain)
                return
        
        self.extraction_stats['failed'] += 1
        self.logger.debug(f"Extraction failed for: {url}")
    
    def _aggressive_extraction(self, response: Response) -> dict:
        """More aggressive content extraction for difficult sites."""
        result = {}
        
        # Try multiple headline selectors
        headline_selectors = [
            'h1::text',
            'h1 *::text',
            '.article-title::text',
            '.news-title::text',
            '.entry-title::text',
            '.post-title::text',
            '[itemprop="headline"]::text',
            'meta[property="og:title"]::attr(content)',
            'title::text',
        ]
        
        for sel in headline_selectors:
            headline = response.css(sel).get()
            if headline and len(headline.strip()) > 10:
                result['headline'] = headline.strip()
                break
        
        # Try multiple body selectors
        body_selectors = [
            'article p::text',
            '.article-body p::text',
            '.article-content p::text',
            '.news-content p::text',
            '.entry-content p::text',
            '.post-content p::text',
            '.content p::text',
            '.story-body p::text',
            '[itemprop="articleBody"] p::text',
            'main p::text',
            '.main-content p::text',
        ]
        
        for sel in body_selectors:
            paragraphs = response.css(sel).getall()
            if paragraphs:
                body = ' '.join(p.strip() for p in paragraphs if p.strip())
                if len(body) >= 50:
                    result['article_body'] = body
                    break
        
        # Get image
        result['image_url'] = response.css('meta[property="og:image"]::attr(content)').get()
        
        return result
    
    def _yield_article(self, response: Response, extracted: dict, domain: str) -> Generator:
        """Yield an article item with proper validation."""
        url = response.url
        headline = extracted['headline'].strip()
        article_body = extracted.get('article_body', '')
        
        # Get publication date
        pub_date = None
        if extracted.get('publication_date'):
            pub_date = self.parse_article_date(str(extracted['publication_date']))
        
        # Date filter
        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return
        
        # Search query filter
        if not self.filter_by_search_query(headline, article_body):
            return
        
        self.stats['articles_processed'] += 1
        
        # Update paper name from domain
        self.paper_name = domain.split('.')[0].title()
        
        yield self.create_article_item(
            url=url,
            headline=headline,
            article_body=article_body,
            author=extracted.get('author') or self.extract_author(response),
            publication_date=pub_date.isoformat() if pub_date else None,
            modification_date=extracted.get('modification_date'),
            image_url=extracted.get('image_url'),
        )
        
        self.logger.info(f"✅ Extracted: {headline[:50]}...")
    
    def closed(self, reason):
        """Log final extraction stats."""
        self.logger.info(f"Extraction Stats: {self.extraction_stats}")
        super().closed(reason) if hasattr(super(), 'closed') else None
    
    # Alias for compatibility
    parse = parse_listing

