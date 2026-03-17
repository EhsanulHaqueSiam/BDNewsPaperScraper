"""
BBC Bangla Spider
=================
Scrapes articles from BBC Bengali (bbc.com/bengali) - International Bengali service

Features:
    - Embedded JSON extraction from SIMORGH_DATA (topic pages)
    - Article content from __NEXT_DATA__ (article pages)
    - Pagination support via ?page=N
    - Category filtering
"""

import json
import re
from html import unescape
from typing import Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider
from scrapy.selector import Selector
from w3lib.html import remove_tags


class BBCBanglaSpider(BaseNewsSpider):
    """
    Spider for BBC Bengali Service.
    
    Uses embedded SIMORGH_DATA JSON for article listings.
    
    Usage:
        scrapy crawl bbcbangla -a categories=bangladesh,world
        scrapy crawl bbcbangla -a max_pages=5
        scrapy crawl bbcbangla -a start_date=2024-01-01
    """
    
    name = 'bbcbangla'
    paper_name = 'BBC Bangla'
    allowed_domains = ['bbc.com', 'www.bbc.com']
    language = 'Bangla'
    
    # Base URL for topics
    BASE_URL = 'https://www.bbc.com/bengali'
    
    # API/filter capabilities
    supports_api_date_filter = False
    supports_api_category_filter = True
    
    # Topic IDs for different categories
    CATEGORIES = {
        'all': '',
        'bangladesh': 'topics/c2dwq2nd40xt',
        'india': 'topics/cdr56gv542vt',
        'world': 'topics/c907347rezkt',
        'health': 'topics/cg7265yyxn1t',
        'video': 'topics/cxy7jg418e7t',
        'science': 'topics/cnq6873qqykt',
        'entertainment': 'topics/cqywjyzk834t',
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
        self._rss_urls_seen = set()
        self.logger.info(f"BBC Bangla spider initialized")
        self.logger.info(f"Categories: {self.categories or 'all'}")
    
    def start_requests(self):
        """Generate initial requests: RSS/sitemap first, then category fallback."""
        self.stats['requests_made'] = 0

        # Primary: RSS feed
        self.stats['requests_made'] += 1
        yield Request(
            url='https://feeds.bbci.co.uk/bengali/rss.xml',
            callback=self.parse_rss,
            headers={'Accept': 'application/rss+xml, application/xml, text/xml'},
            errback=self._rss_failed,
            meta={'source': 'rss'},
        )

    def _generate_fallback_requests(self) -> Generator[Request, None, None]:
        """Generate fallback category requests."""
        
        if self.categories:
            for category in self.categories:
                cat_lower = category.lower().strip().replace('-', '').replace('_', '')
                
                if cat_lower in self.CATEGORIES:
                    topic_path = self.CATEGORIES[cat_lower]
                else:
                    self.logger.warning(f"Unknown category: {category}")
                    continue
                
                if topic_path:
                    url = f"{self.BASE_URL}/{topic_path}"
                else:
                    url = self.BASE_URL
                
                self.logger.info(f"Crawling category: {category}")
                self.stats['requests_made'] += 1
                
                yield Request(
                    url=url,
                    callback=self.parse_topic_page,
                    meta={
                        'category': category,
                        'page': 1,
                        'topic_path': topic_path,
                    },
                    errback=self.handle_request_failure,
                )
        else:
            # Crawl homepage for all categories
            self.logger.info("Crawling BBC Bangla homepage")
            self.stats['requests_made'] += 1
            
            yield Request(
                url=self.BASE_URL,
                callback=self.parse_topic_page,
                meta={
                    'category': 'all',
                    'page': 1,
                    'topic_path': '',
                },
                errback=self.handle_request_failure,
            )
    
    def parse_topic_page(self, response: Response) -> Generator:
        """Parse topic page and extract articles from SIMORGH_DATA."""
        category = response.meta.get('category', 'all')
        page = response.meta.get('page', 1)
        topic_path = response.meta.get('topic_path', '')
        
        # Extract SIMORGH_DATA from script tag
        simorgh_data = self._extract_simorgh_data(response)
        
        if not simorgh_data:
            self.logger.error(f"No SIMORGH_DATA found on {response.url}")
            return
        
        # Extract articles from curations
        page_data = simorgh_data.get('pageData', {})
        curations = page_data.get('curations', [])
        
        articles_found = 0
        
        for curation in curations:
            summaries = curation.get('summaries', [])
            
            for summary in summaries:
                article_url = summary.get('link', '')
                
                if not article_url or not article_url.startswith('http'):
                    continue
                
                # Skip if already in DB
                if self.is_url_in_db(article_url):
                    continue
                
                headline = summary.get('title', '')
                if not headline:
                    continue
                
                # Get summary text as initial body
                first_context = summary.get('firstContext', '')
                
                # Get publication date
                pub_date_str = summary.get('lastRecordPublishDateTime', '')
                pub_date = self._parse_date_string(pub_date_str)
                
                # Date filter
                if pub_date and not self.is_date_in_range(pub_date):
                    self.stats['date_filtered'] += 1
                    continue
                
                articles_found += 1
                self.stats['articles_found'] += 1
                
                # Request full article for complete body
                self.stats['requests_made'] += 1
                yield Request(
                    url=article_url,
                    callback=self.parse_article,
                    meta={
                        'category': category,
                        'headline': headline,
                        'summary': first_context,
                        'pub_date': pub_date,
                    },
                    errback=self.handle_request_failure,
                )
        
        self.logger.info(f"Found {articles_found} articles on {category} page {page}")
        
        # Pagination - get next page
        if articles_found > 0 and page < self.max_pages:
            next_page = page + 1
            
            if topic_path:
                next_url = f"{self.BASE_URL}/{topic_path}?page={next_page}"
            else:
                # Homepage doesn't have pagination
                return
            
            self.stats['requests_made'] += 1
            
            yield Request(
                url=next_url,
                callback=self.parse_topic_page,
                meta={
                    'category': category,
                    'page': next_page,
                    'topic_path': topic_path,
                },
                errback=self.handle_request_failure,
            )
    

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

    def parse_article(self, response: Response) -> Generator:
        """Parse individual article page for full content."""
        category = response.meta.get('category', 'all')
        headline = response.meta.get('headline', '')
        summary = response.meta.get('summary', '')
        pub_date = response.meta.get('pub_date')
        
        # Extract __NEXT_DATA__ for article content
        next_data = self._extract_next_data(response)
        
        article_body = ''
        author = None
        image_url = None
        
        if next_data:
            page_props = next_data.get('props', {}).get('pageProps', {})
            page_data = page_props.get('pageData', {})
            
            # Extract content blocks
            content = page_data.get('content', {})
            model = content.get('model', {})
            blocks = model.get('blocks', [])
            
            # Extract text from blocks
            text_parts = []
            for block in blocks:
                if block.get('type') == 'text':
                    text_parts.extend(self._extract_text_from_block(block))
            
            article_body = ' '.join(text_parts)
            
            # Extract author
            promo = page_data.get('promo', {})
            author_info = promo.get('byline', {})
            if isinstance(author_info, dict):
                author = author_info.get('name', '')
            
            # Extract image
            images = promo.get('images', {})
            if images:
                default_promo = images.get('defaultPromoImage', {})
                image_url = default_promo.get('src', '')
        
        # Fallback to SIMORGH_DATA if __NEXT_DATA__ not found
        if not article_body:
            simorgh_data = self._extract_simorgh_data(response)
            if simorgh_data:
                page_data = simorgh_data.get('pageData', {})
                content = page_data.get('content', {})
                model = content.get('model', {})
                blocks = model.get('blocks', [])
                
                text_parts = []
                for block in blocks:
                    if block.get('type') == 'text':
                        text_parts.extend(self._extract_text_from_block(block))
                
                article_body = ' '.join(text_parts)
        
        # Use summary if no body extracted
        if not article_body and summary:
            article_body = summary
        
        if len(article_body) < 50:
            self.logger.debug(f"Article too short: {response.url}")
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
    
    def _extract_simorgh_data(self, response: Response) -> Optional[dict]:
        """Extract SIMORGH_DATA from script tag."""
        # Look for window.SIMORGH_DATA assignment
        pattern = r'window\.SIMORGH_DATA\s*=\s*(\{.+?\});?\s*</script>'
        match = re.search(pattern, response.text, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                self.logger.debug("Failed to parse SIMORGH_DATA")
        
        return None
    
    def _extract_next_data(self, response: Response) -> Optional[dict]:
        """Extract __NEXT_DATA__ from script tag."""
        script = response.css('script#__NEXT_DATA__::text').get()
        
        if script:
            try:
                return json.loads(script)
            except json.JSONDecodeError:
                self.logger.debug("Failed to parse __NEXT_DATA__")
        
        return None
    
    def _extract_text_from_block(self, block: dict) -> list:
        """Recursively extract text from content blocks."""
        texts = []
        
        if 'text' in block.get('model', {}):
            text = block['model']['text']
            texts.append(unescape(text.strip()))
        
        # Check nested blocks
        nested_blocks = block.get('model', {}).get('blocks', [])
        for nested in nested_blocks:
            texts.extend(self._extract_text_from_block(nested))
        
        return texts
