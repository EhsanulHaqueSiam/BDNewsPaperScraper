"""
Maasranga TV Spider (Bangla)
============================
Scrapes articles from Maasranga TV (maasranga.tv)

Features:
    - WordPress REST API support with HTTP fallback
    - Stealthy browser rendering via Scrapling
    - Extended timeout and retries (server barely responsive)
    - Category-based scraping via API
    - Date filtering (server-side via API)
    - Pagination support
"""

import json
import re
from html import unescape
from typing import Any, Dict, Generator, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class MaasrangaSpider(BaseNewsSpider):
    """
    Spider for Maasranga TV using WordPress REST API.

    maasranga.tv has TLS timeout issues. Uses HTTP fallback, Scrapling
    stealthy mode, extended timeout (60s), and 3 retries for resilience.

    Usage:
        scrapy crawl maasranga
        scrapy crawl maasranga -a categories=national,sports
        scrapy crawl maasranga -a max_pages=10
    """

    name = 'maasranga'
    paper_name = 'Maasranga TV'
    allowed_domains = ['maasranga.tv']
    language = 'Bangla'

    # API capabilities
    supports_api_date_filter = True
    supports_api_category_filter = True

    # WordPress API base - try HTTP to avoid TLS timeout
    API_BASE = 'http://maasranga.tv/wp-json/wp/v2'
    POSTS_PER_PAGE = 20

    # Category ID mappings (from WP API)
    CATEGORY_IDS = {
        'editors-pick': 5,
        'popular': 7,
        'trending': 9,
        'kids': 23,
    }

    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 6,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
        'DOWNLOAD_TIMEOUT': 60,
        'RETRY_TIMES': 3,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Maasranga TV spider initialized (WordPress API, HTTP fallback)")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial API requests, trying HTTP first then HTTPS."""
        self.stats['requests_made'] = 0

        # Build base API URL with date filters
        base_params = self._build_date_params()

        if self.categories:
            for category in self.categories:
                cat_id = self.CATEGORY_IDS.get(category.lower().strip())
                params = base_params.copy()

                if cat_id:
                    params['categories'] = cat_id

                # Try HTTP first (TLS timeout workaround)
                url = self._build_api_url(params)
                self.logger.info(f"Crawling category: {category} -> {url}")
                self.stats['requests_made'] += 1

                yield Request(
                    url=url,
                    callback=self.parse_api_response,
                    meta={'category': category, 'page': 1, 'params': params, 'scrapling': 'stealthy'},
                    errback=self.handle_api_failure,
                )
        else:
            # Fetch all recent posts via HTTP API
            url = self._build_api_url(base_params)
            self.logger.info(f"Crawling all posts: {url}")
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_api_response,
                meta={'category': 'General', 'page': 1, 'params': base_params, 'scrapling': 'stealthy'},
                errback=self.handle_api_failure,
            )

        # Also try HTML scraping as fallback
        html_url = 'http://maasranga.tv'
        self.logger.info(f"HTML fallback: {html_url}")
        self.stats['requests_made'] += 1
        yield Request(
            url=html_url,
            callback=self.parse_homepage_html,
            meta={'scrapling': 'stealthy'},
            errback=self.handle_request_failure,
        )

    def handle_api_failure(self, failure):
        """Handle API failure - try HTTPS as last resort."""
        url = failure.request.url
        self.stats['errors'] += 1
        self.logger.warning(f"HTTP API request failed: {failure.value}")

        # If HTTP failed, try HTTPS as fallback
        if url.startswith('http://'):
            https_url = url.replace('http://', 'https://', 1)
            self.logger.info(f"Retrying with HTTPS: {https_url}")
            self.stats['requests_made'] += 1
            yield Request(
                url=https_url,
                callback=self.parse_api_response,
                meta=failure.request.meta.copy(),
                errback=self.handle_request_failure,
            )

    def _build_date_params(self) -> Dict[str, Any]:
        """Build API parameters with date filters."""
        params = {
            'per_page': self.POSTS_PER_PAGE,
            'page': 1,
            '_embed': 1,  # Include embedded data (author, media)
        }

        # Add date filters
        if self.start_date:
            params['after'] = self.start_date.strftime('%Y-%m-%dT%H:%M:%S')
        if self.end_date:
            params['before'] = self.end_date.strftime('%Y-%m-%dT%H:%M:%S')

        return params

    def _build_api_url(self, params: Dict[str, Any]) -> str:
        """Build the API URL with query parameters."""
        from urllib.parse import urlencode
        query = urlencode(params)
        return f"{self.API_BASE}/posts?{query}"

    def parse_api_response(self, response: Response) -> Generator:
        """Parse WordPress REST API response."""
        category = response.meta.get('category', 'General')
        page = response.meta.get('page', 1)
        params = response.meta.get('params', {})

        try:
            posts = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse API response: {response.url}")
            return

        if not posts:
            self.logger.info(f"No more posts found for {category} at page {page}")
            return

        self.logger.info(f"Found {len(posts)} posts in {category} page {page}")

        for post in posts:
            article = self._parse_post(post, category)
            if article:
                yield article

        # Pagination - fetch next page if we have results
        if len(posts) >= self.POSTS_PER_PAGE and page < self.max_pages:
            next_params = params.copy()
            next_params['page'] = page + 1
            next_url = self._build_api_url(next_params)

            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={'category': category, 'page': page + 1, 'params': next_params, 'scrapling': 'stealthy'},
                errback=self.handle_request_failure,
            )

    def parse_homepage_html(self, response: Response) -> Generator:
        """Parse homepage HTML for article links (fallback if API is down)."""
        article_links = response.css('a::attr(href)').getall()
        article_links = [
            l for l in article_links
            if 'maasranga.tv/' in l
            and not re.search(r'/(category|tag|page|wp-|feed|author)/', l)
            and l != response.url
        ]
        article_links = list(set(article_links))

        # ROBUST FALLBACK: Use universal link discovery if selectors fail
        if not article_links:
            self.logger.info("CSS selectors failed, using universal link discovery")
            article_links = self.discover_links(response, limit=50)

        self.logger.info(f"HTML fallback: found {len(article_links)} article links from homepage")

        for url in article_links:
            # Prefer HTTP to avoid TLS issues
            if url.startswith('https://'):
                url = url.replace('https://', 'http://', 1)

            if self.is_url_in_db(url):
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1

            yield Request(
                url=url,
                callback=self.parse_article_html,
                meta={'category': 'General', 'scrapling': 'stealthy'},
                errback=self.handle_request_failure,
            )

    def parse_article_html(self, response: Response) -> Generator[NewsArticleItem, None, None]:
        """Parse individual article page via HTML (fallback)."""
        url = response.url

        # ROBUST FALLBACK: Try universal extraction first
        fallback = self.extract_article_fallback(response)
        if fallback and fallback.get('headline') and fallback.get('article_body'):
            if len(fallback.get('article_body', '')) >= 100:
                pub_date = self.parse_article_date(str(fallback.get('publication_date', ''))) if fallback.get('publication_date') else None
                if pub_date and not self.is_date_in_range(pub_date):
                    self.stats['date_filtered'] += 1
                    return
                if not self.filter_by_search_query(fallback['headline'], fallback['article_body']):
                    return
                self.stats['articles_processed'] += 1
                yield self.create_article_item(
                    url=url,
                    headline=fallback['headline'],
                    article_body=fallback['article_body'],
                    author=fallback.get('author') or self.extract_author(response),
                    publication_date=pub_date.isoformat() if pub_date else None,
                    image_url=fallback.get('image_url'),
                    category=response.meta.get('category', 'General'),
                )
                return

        # Manual HTML extraction
        headline = (
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            ''
        )
        if not headline:
            return

        headline = unescape(headline.strip())

        body_parts = response.css('article p::text, .entry-content p::text, .post-content p::text').getall()
        if not body_parts:
            body_parts = response.css('p::text').getall()

        article_body = ' '.join(unescape(p.strip()) for p in body_parts if p.strip())
        if len(article_body) < 100:
            return

        if not self.filter_by_search_query(headline, article_body):
            return

        pub_date = None
        date_text = response.css('meta[property="article:published_time"]::attr(content)').get()
        if date_text:
            pub_date = self._parse_date_string(date_text.strip())

        if pub_date and not self.is_date_in_range(pub_date):
            self.stats['date_filtered'] += 1
            return

        image_url = response.css('meta[property="og:image"]::attr(content)').get()

        self.stats['articles_processed'] += 1
        yield self.create_article_item(
            url=url,
            headline=headline,
            article_body=article_body,
            publication_date=pub_date.isoformat() if pub_date else None,
            category=response.meta.get('category', 'General'),
            image_url=image_url,
        )

    def _parse_post(self, post: Dict[str, Any], category: str) -> Optional[NewsArticleItem]:
        """Parse a single post from API response."""
        try:
            url = post.get('link', '')
            if not url or self.is_url_in_db(url):
                return None

            self.stats['articles_found'] += 1

            # Extract headline
            title_data = post.get('title', {})
            headline = title_data.get('rendered', '') if isinstance(title_data, dict) else str(title_data)
            headline = self._clean_html(headline)

            if not headline:
                return None

            # Extract body
            content_data = post.get('content', {})
            content = content_data.get('rendered', '') if isinstance(content_data, dict) else str(content_data)
            article_body = self._clean_html(content)

            if len(article_body) < 100:
                return None

            # Search filter
            if not self.filter_by_search_query(headline, article_body):
                return None

            # Parse date
            pub_date = None
            date_str = post.get('date_gmt') or post.get('date')
            if date_str:
                pub_date = self._parse_date_string(date_str)

            # Date filter (backup - API should handle this)
            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                return None

            # Extract image
            image_url = None
            embedded = post.get('_embedded', {})
            featured_media = embedded.get('wp:featuredmedia', [])
            if featured_media and len(featured_media) > 0:
                media = featured_media[0]
                image_url = media.get('source_url') or media.get('link')

            # Extract author
            author = None
            authors = embedded.get('author', [])
            if authors and len(authors) > 0:
                author = authors[0].get('name')

            # Extract excerpt as subtitle
            excerpt_data = post.get('excerpt', {})
            excerpt = excerpt_data.get('rendered', '') if isinstance(excerpt_data, dict) else ''
            sub_title = self._clean_html(excerpt)[:500] if excerpt else None

            self.stats['articles_processed'] += 1

            return self.create_article_item(
                url=url,
                headline=headline,
                article_body=article_body,
                sub_title=sub_title,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=category,
                author=author,
                image_url=image_url,
            )

        except Exception as e:
            self.logger.error(f"Error parsing post: {e}")
            self.stats['errors'] += 1
            return None

    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean up content."""
        if not html_content:
            return ''

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        # Decode HTML entities
        text = unescape(text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
