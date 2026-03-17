"""
Somoyer TV Spider (Bangla)
==========================
Scrapes articles from Somoyer TV (somoyertv.com) using WordPress REST API

Features:
    - 24-hour live TV news portal
    - WordPress REST API with HTML scraping fallback
    - Server-side date filtering
    - Stealthy browser rendering via Scrapling
"""

import json
import re
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, Generator, List, Optional

import scrapy
from scrapy.http import Request, Response

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.spiders.base_spider import BaseNewsSpider


class SomoyerTVSpider(BaseNewsSpider):
    """
    Spider for Somoyer TV (24 Hours Live TV News).

    Uses WordPress REST API for efficient scraping, with HTML fallback.
    Uses Scrapling stealthy mode for browser rendering (site may have
    stale WP API data from 2019).

    Usage:
        scrapy crawl somoyertv
        scrapy crawl somoyertv -a start_date=2024-01-01
    """

    name = 'somoyertv'
    paper_name = 'Somoyer TV'
    allowed_domains = ['somoyertv.com']
    language = 'Bangla'

    # API capabilities
    supports_api_date_filter = True
    supports_api_category_filter = True

    # API endpoints
    API_BASE = 'https://somoyertv.com/wp-json/wp/v2'
    POSTS_ENDPOINT = f'{API_BASE}/posts'

    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
    }

    # HTML scraping categories (fallback if API returns stale data)
    CATEGORIES = {
        'national': 'national',
        'bangladesh': 'national',
        'politics': 'politics',
        'international': 'international',
        'world': 'international',
        'sports': 'sports',
        'entertainment': 'entertainment',
        'economy': 'economy',
        'business': 'economy',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Somoyer TV spider initialized (WordPress API + HTML fallback)")

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial API requests, plus HTML fallback."""
        self.stats['requests_made'] = 0

        params = ['per_page=20', 'page=1', '_embed=1']

        # Add date range if specified (uses base_spider's start_date/end_date)
        if self.start_date:
            after_date = self.start_date.strftime('%Y-%m-%dT00:00:00')
            params.append(f'after={after_date}')

        if self.end_date:
            before_date = (self.end_date + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00')
            params.append(f'before={before_date}')

        url = f"{self.POSTS_ENDPOINT}?{'&'.join(params)}"

        self.logger.info(f"Starting API request: {url}")
        self.stats['requests_made'] += 1

        yield Request(
            url=url,
            callback=self.parse_api_response,
            meta={'page': 1, 'scrapling': 'stealthy'},
            errback=self.handle_api_failure,
        )

        # Also try HTML scraping as fallback (API may return 2019 data)
        for cat in ['national', 'politics', 'sports', 'international']:
            cat_slug = self.CATEGORIES.get(cat, cat)
            cat_url = f"https://somoyertv.com/{cat_slug}"
            self.logger.info(f"HTML fallback category: {cat} -> {cat_url}")
            self.stats['requests_made'] += 1
            yield Request(
                url=cat_url,
                callback=self.parse_category_html,
                meta={'category': cat, 'cat_slug': cat_slug, 'page': 1, 'scrapling': 'stealthy'},
                errback=self.handle_request_failure,
            )

    def handle_api_failure(self, failure):
        """Handle API request failure - fall back to HTML scraping."""
        self.logger.warning(f"API request failed: {failure.value}. HTML fallback already in progress.")
        self.handle_request_failure(failure)

    def parse_api_response(self, response: Response) -> Generator:
        """Parse WordPress REST API response."""
        page = response.meta.get('page', 1)

        try:
            posts = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse API response as JSON")
            return

        if not posts:
            self.logger.info(f"No more posts found on page {page}")
            return

        self.logger.info(f"Processing {len(posts)} posts from page {page}")

        for post in posts:
            item = self._parse_post(post)
            if item:
                yield item

        # Pagination
        total_pages = int(response.headers.get('X-WP-TotalPages', 1))
        if page < min(total_pages, self.max_pages):
            next_page = page + 1
            next_url = re.sub(r'page=\d+', f'page={next_page}', response.url)

            self.stats['requests_made'] += 1
            yield Request(
                url=next_url,
                callback=self.parse_api_response,
                meta={'page': next_page, 'scrapling': 'stealthy'},
                errback=self.handle_request_failure,
            )

    def parse_category_html(self, response: Response) -> Generator:
        """Parse category page via HTML scraping (fallback for stale API)."""
        category = response.meta.get('category', 'Unknown')
        cat_slug = response.meta.get('cat_slug')
        page = response.meta.get('page', 1)

        # Extract article links
        article_links = response.css('a::attr(href)').getall()
        article_links = [l for l in article_links if 'somoyertv.com/' in l and l != response.url]
        # Filter out category/tag/page links
        article_links = [l for l in article_links if not re.search(r'/(category|tag|page|wp-|feed|author)/', l)]
        article_links = list(set(article_links))

        # ROBUST FALLBACK: Use universal link discovery if selectors fail
        if not article_links:
            self.logger.info("CSS selectors failed, using universal link discovery")
            article_links = self.discover_links(response, limit=50)

        self.logger.info(f"HTML fallback: found {len(article_links)} articles in {category} page {page}")

        if not article_links:
            return

        found_count = 0
        for url in article_links:
            if self.is_url_in_db(url):
                continue

            self.stats['articles_found'] += 1
            self.stats['requests_made'] += 1
            found_count += 1

            yield Request(
                url=url,
                callback=self.parse_article_html,
                meta={'category': category, 'scrapling': 'stealthy'},
                errback=self.handle_request_failure,
            )

        # Pagination for HTML fallback
        if found_count > 0 and page < self.max_pages:
            next_page_link = response.css('a.next::attr(href), a[rel="next"]::attr(href)').get()
            if next_page_link:
                self.stats['requests_made'] += 1
                yield Request(
                    url=next_page_link,
                    callback=self.parse_category_html,
                    meta={'category': category, 'cat_slug': cat_slug, 'page': page + 1, 'scrapling': 'stealthy'},
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

        # Manual extraction
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

    def _parse_post(self, post: Dict[str, Any]) -> Optional[NewsArticleItem]:
        """Parse individual post from API response."""
        try:
            url = post.get('link', '')
            if not url or self.is_url_in_db(url):
                return None

            self.stats['articles_found'] += 1

            # Extract headline
            headline = post.get('title', {}).get('rendered', '')
            headline = self._clean_html(headline)

            if not headline:
                return None

            # Extract body
            content = post.get('content', {}).get('rendered', '')
            article_body = self._clean_html(content)

            if len(article_body) < 100:
                return None

            if not self.filter_by_search_query(headline, article_body):
                return None

            # Parse date
            pub_date = None
            date_str = post.get('date', '')
            if date_str:
                try:
                    pub_date = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
                    pub_date = self.dhaka_tz.localize(pub_date)
                except ValueError:
                    pass

            if pub_date and not self.is_date_in_range(pub_date):
                self.stats['date_filtered'] += 1
                return None

            # Extract category from embedded data
            category = 'General'
            embedded = post.get('_embedded', {})
            terms = embedded.get('wp:term', [[]])
            if terms and terms[0]:
                category = terms[0][0].get('name', 'General')

            # Extract image
            image_url = None
            featured_media = embedded.get('wp:featuredmedia', [{}])
            if featured_media:
                image_url = featured_media[0].get('source_url', '')

            self.stats['articles_processed'] += 1

            return self.create_article_item(
                url=url,
                headline=headline,
                article_body=article_body,
                publication_date=pub_date.isoformat() if pub_date else None,
                category=category,
                image_url=image_url,
            )
        except Exception as e:
            self.logger.error(f"Error parsing post: {e}")
            self.stats['errors'] += 1
            return None

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content to plain text."""
        if not html_content:
            return ''
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
