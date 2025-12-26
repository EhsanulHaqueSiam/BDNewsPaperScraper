#!/usr/bin/env python3
"""
Playwright Spiders for Cloudflare-Protected Sites
===================================================
Scrape JavaScript-heavy and Cloudflare-protected sites using Playwright.

These spiders handle:
    - Cloudflare protection bypass
    - JavaScript rendering
    - Dynamic content loading
    - Anti-bot detection

Setup:
    pip install scrapy-playwright playwright
    playwright install chromium

Usage:
    scrapy crawl kalerkantho_playwright  # Specific spider for Kaler Kantho
    scrapy crawl generic_playwright -a url=https://example.com -a selector=".article"
"""

import scrapy
from scrapy import Request
from typing import Generator, Dict, Any, Optional
from datetime import datetime
import re
import json

# Import base spider
try:
    from BDNewsPaper.spiders.base_spider import BaseNewsSpider
    from BDNewsPaper.items import ArticleItem
except ImportError:
    BaseNewsSpider = scrapy.Spider
    ArticleItem = dict

# Import PageMethod for Playwright actions
try:
    from scrapy_playwright.page import PageMethod
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PageMethod = None
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightMixin:
    """Mixin for Playwright-based scraping with Cloudflare bypass."""
    
    playwright_enabled = True
    
    # Browser settings
    browser_type = "chromium"
    headless = True
    timeout = 60000  # 60 seconds
    
    # Cloudflare bypass settings
    wait_for_cloudflare = True
    cf_wait_time = 8000  # 8 seconds for Cloudflare challenge
    
    def get_playwright_meta(self, wait_for: str = None, timeout: int = None) -> Dict:
        """
        Get Playwright meta dictionary for request.
        
        Args:
            wait_for: CSS selector to wait for before returning
            timeout: Custom timeout in milliseconds
        """
        meta = {
            "playwright": True,
            "playwright_include_page": True,
            "playwright_context": "default",
        }
        
        # Page methods to execute (must be PageMethod objects, not dicts)
        page_methods = []
        
        if PLAYWRIGHT_AVAILABLE and PageMethod:
            if self.wait_for_cloudflare:
                # Wait for Cloudflare challenge to complete
                page_methods.append(
                    PageMethod("wait_for_timeout", self.cf_wait_time)
                )
            
            if wait_for:
                page_methods.append(
                    PageMethod("wait_for_selector", wait_for, timeout=timeout or self.timeout)
                )
        
        if page_methods:
            meta["playwright_page_methods"] = page_methods
        
        return meta


class KalerKanthoPlaywrightSpider(scrapy.Spider, PlaywrightMixin):
    """
    Playwright spider for Kaler Kantho (Cloudflare protected).
    
    Kaler Kantho uses Cloudflare protection which blocks regular scrapy requests.
    This spider uses Playwright to render the JavaScript and bypass the protection.
    
    Usage:
        scrapy crawl kalerkantho_playwright
        scrapy crawl kalerkantho_playwright -a category=national
        scrapy crawl kalerkantho_playwright -s CLOSESPIDER_ITEMCOUNT=20
    
    Note: This spider scrapes the Bangla version of Kaler Kantho.
    """
    
    name = "kalerkantho_playwright"
    allowed_domains = ["kalerkantho.com"]
    
    paper_name = "Kaler Kantho"
    source_language = "bn"
    
    # Custom settings for Playwright
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
        "PLAYWRIGHT_CONTEXTS": {
            "default": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        },
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 5,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 5,
        "AUTOTHROTTLE_MAX_DELAY": 30,
    }
    
    # News categories with their URL paths
    categories = {
        "national": "/online/country-news",
        "politics": "/online/politics",
        "international": "/online/world",
        "sports": "/online/khela",
        "entertainment": "/online/entertainment",
        "economy": "/online/money-and-economy",
        "technology": "/online/technology",
        "lifestyle": "/online/lifestyle",
        "opinion": "/online/muktomoncho",
        "education": "/online/education",
    }
    
    def __init__(self, category: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_category = category
        self.articles_scraped = 0
        
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests with Playwright for category pages."""
        
        # Filter categories if specified
        if self.target_category:
            if self.target_category in self.categories:
                cats_to_scrape = {self.target_category: self.categories[self.target_category]}
            else:
                self.logger.error(f"Unknown category: {self.target_category}")
                self.logger.info(f"Available categories: {list(self.categories.keys())}")
                return
        else:
            cats_to_scrape = self.categories
        
        for cat_name, cat_path in cats_to_scrape.items():
            url = f"https://www.kalerkantho.com{cat_path}"
            self.logger.info(f"Starting category: {cat_name} -> {url}")
            
            yield Request(
                url=url,
                callback=self.parse_category,
                meta={
                    # Updated wait_for selectors for 2024-2025 layout
                    **self.get_playwright_meta(wait_for=".container, .catLead, .row, h4"),
                    "category": cat_name
                },
                errback=self.errback_playwright,
                dont_filter=True
            )
    
    async def parse_category(self, response) -> Generator[Dict, None, None]:
        """Parse category page for article links."""
        category = response.meta.get("category", "unknown")
        page = response.meta.get("playwright_page")
        
        self.logger.info(f"Parsing category page: {category}")
        
        if page:
            try:
                # Scroll to load more content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
            except Exception as e:
                self.logger.warning(f"Error scrolling page: {e}")
            finally:
                await page.close()
        
        # Extract article links - updated selectors based on current site layout
        article_links = set()
        
        # Updated selectors for current Kalerkantho layout (2024-2025)
        # Primary: Use href pattern matching for /online/ links
        selectors = [
            "a[href*='/online/']::attr(href)",  # Best: any link with /online/ in path
            ".catLead a::attr(href)",           # Lead story container
            ".row a::attr(href)",               # Row-based listings
            "h4 a::attr(href)",                 # Headlines in h4
            "h5 a::attr(href)",                 # Headlines in h5
            "h3 a::attr(href)",                 # Headlines in h3
            "h2 a::attr(href)",                 # Headlines in h2
            ".col-md-6 a::attr(href)",          # Bootstrap column items
            ".col-md-4 a::attr(href)",          # Bootstrap column items
        ]
        
        for selector in selectors:
            links = response.css(selector).getall()
            for link in links:
                if link and "/online/" in link:
                    full_url = response.urljoin(link)
                    # Filter to only article URLs (has date pattern)
                    if any(f"/{year}/" in full_url for year in ['2024', '2025', '2023']):
                        article_links.add(full_url)
        
        self.logger.info(f"Found {len(article_links)} article links in {category}")
        
        # Request each article
        for url in list(article_links)[:30]:  # Limit per category
            yield Request(
                url=url,
                callback=self.parse_article,
                meta={
                    # Updated: use generic selectors that exist on article pages
                    **self.get_playwright_meta(wait_for=".container, h1, .row"),
                    "category": category
                },
                errback=self.errback_playwright
            )
    
    async def parse_article(self, response) -> Generator[Dict, None, None]:
        """Parse individual article with Playwright."""
        page = response.meta.get("playwright_page")
        category = response.meta.get("category", "")
        
        if page:
            try:
                await page.wait_for_selector("h1, .container", timeout=10000)
            except:
                pass
            finally:
                await page.close()
        
        # Extract headline
        headline = (
            response.css("h1.headline::text").get() or
            response.css("h1::text").get() or
            response.css(".title::text").get() or
            response.css("article h1::text").get() or
            ""
        ).strip()
        
        # Extract article body
        body_parts = (
            response.css(".news_content p::text").getall() or
            response.css(".single_news p::text").getall() or
            response.css("article p::text").getall() or
            response.css(".newsArticle p::text").getall() or
            []
        )
        body = "\n".join(p.strip() for p in body_parts if p.strip())
        
        # Extract metadata
        author = (
            response.css(".author_name::text").get() or
            response.css(".reporter::text").get() or
            response.css(".author::text").get() or
            ""
        ).strip()
        
        date_str = (
            response.css("time::attr(datetime)").get() or
            response.css(".publish_time::text").get() or
            response.css(".date::text").get() or
            ""
        )
        
        # Only yield if we have meaningful content
        if headline and len(body) > 100:
            self.articles_scraped += 1
            
            yield {
                "url": response.url,
                "headline": headline,
                "article_body": body,
                "author": author or "Kaler Kantho",
                "publication_date": date_str,
                "category": category,
                "paper_name": self.paper_name,
                "source_language": self.source_language,
                "scraped_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"✓ Article scraped: {headline[:50]}...")
        else:
            self.logger.warning(f"✗ Insufficient content: {response.url}")
    
    async def errback_playwright(self, failure):
        """Handle Playwright errors gracefully."""
        self.logger.error(f"Playwright error: {failure}")
        
        # Try to close page if it exists
        try:
            page = failure.request.meta.get("playwright_page")
            if page:
                await page.close()
        except:
            pass
    
    def closed(self, reason):
        """Log statistics when spider closes."""
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total articles scraped: {self.articles_scraped}")


class GenericPlaywrightSpider(scrapy.Spider, PlaywrightMixin):
    """
    Generic Playwright spider for any Cloudflare-protected or JS-heavy site.
    
    This spider can scrape any website that requires JavaScript rendering
    or has Cloudflare protection.
    
    Usage:
        # Basic usage
        scrapy crawl generic_playwright -a url=https://example.com
        
        # With custom article selector
        scrapy crawl generic_playwright -a url=https://example.com -a selector=".article"
        
        # With custom headline selector
        scrapy crawl generic_playwright -a url=https://example.com -a headline_selector="h1.title"
        
        # With link following
        scrapy crawl generic_playwright -a url=https://example.com -a follow_links=true -a link_selector="a.article-link"
    
    Arguments:
        url: Target URL to scrape (required)
        selector: CSS selector for article containers (default: "article")
        headline_selector: CSS selector for headlines (default: "h1, h2")
        body_selector: CSS selector for body content (default: "p")
        follow_links: Whether to follow links (default: false)
        link_selector: CSS selector for links to follow (default: "a")
        paper_name: Name of the newspaper (default: extracted from domain)
    """
    
    name = "generic_playwright"
    
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        },
        "PLAYWRIGHT_CONTEXTS": {
            "default": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        },
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 3,
    }
    
    def __init__(
        self,
        url: str = None,
        selector: str = None,
        headline_selector: str = None,
        body_selector: str = None,
        follow_links: str = "false",
        link_selector: str = None,
        paper_name: str = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self.target_url = url
        self.content_selector = selector or "article, .article, .post, .content"
        self.headline_selector = headline_selector or "h1, h2, .headline, .title"
        self.body_selector = body_selector or "p, .body, .content p"
        self.follow_links = follow_links.lower() == "true"
        self.link_selector = link_selector or "a"
        self.custom_paper_name = paper_name
        self.articles_scraped = 0
    
    def start_requests(self):
        """Generate initial request."""
        if not self.target_url:
            self.logger.error("❌ No URL provided!")
            self.logger.error("Usage: scrapy crawl generic_playwright -a url=https://example.com")
            return
        
        # Extract domain for paper name
        from urllib.parse import urlparse
        parsed = urlparse(self.target_url)
        self.domain = parsed.netloc
        self.paper_name = self.custom_paper_name or self.domain.replace("www.", "").split(".")[0].title()
        
        self.logger.info(f"🚀 Starting Playwright spider for: {self.target_url}")
        self.logger.info(f"📰 Paper name: {self.paper_name}")
        self.logger.info(f"🔍 Content selector: {self.content_selector}")
        
        yield Request(
            url=self.target_url,
            callback=self.parse,
            meta=self.get_playwright_meta(wait_for=self.content_selector),
            errback=self.errback_playwright
        )
    
    async def parse(self, response):
        """Parse the page with Playwright."""
        page = response.meta.get("playwright_page")
        
        if page:
            try:
                # Take screenshot for debugging
                await page.screenshot(path="playwright_debug.png")
                self.logger.info("📸 Debug screenshot saved: playwright_debug.png")
                
                # Get page content info
                content = await page.content()
                self.logger.info(f"📄 Page loaded: {len(content):,} bytes")
                
                # Scroll to load lazy content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                self.logger.warning(f"Page interaction error: {e}")
            finally:
                await page.close()
        
        # Follow links if enabled
        if self.follow_links:
            links = response.css(f"{self.link_selector}::attr(href)").getall()
            self.logger.info(f"Found {len(links)} links to follow")
            
            for link in links[:20]:  # Limit links
                full_url = response.urljoin(link)
                if full_url.startswith(("http://", "https://")):
                    yield Request(
                        url=full_url,
                        callback=self.parse_article,
                        meta=self.get_playwright_meta(wait_for=self.content_selector),
                        errback=self.errback_playwright
                    )
        
        # Also parse current page as article
        # Also parse current page as article
        for item in self.extract_articles(response):
            yield item
    
    async def parse_article(self, response):
        """Parse individual article page."""
        page = response.meta.get("playwright_page")
        
        if page:
            try:
                await page.wait_for_selector(self.content_selector, timeout=10000)
            except:
                pass
            finally:
                await page.close()
        
        for item in self.extract_articles(response):
            yield item
    
    def extract_articles(self, response):
        """Extract articles from response."""
        articles = response.css(self.content_selector)
        self.logger.info(f"Found {len(articles)} article containers")
        
        if not articles:
            # If no containers found, try to extract from the whole page
            headline = response.css(f"{self.headline_selector}::text").get("").strip()
            body_parts = response.css(f"{self.body_selector}::text").getall()
            body = " ".join(p.strip() for p in body_parts if p.strip())
            
            if headline and body:
                self.articles_scraped += 1
                yield {
                    "url": response.url,
                    "headline": headline,
                    "article_body": body,
                    "paper_name": self.paper_name,
                    "scraped_at": datetime.now().isoformat()
                }
        
        for article in articles:
            headline = article.css(f"{self.headline_selector}::text").get("").strip()
            body_parts = article.css(f"{self.body_selector}::text").getall()
            body = " ".join(p.strip() for p in body_parts if p.strip())
            
            if headline or body:
                self.articles_scraped += 1
                yield {
                    "url": response.url,
                    "headline": headline or "Untitled",
                    "article_body": body or article.get(),
                    "paper_name": self.paper_name,
                    "scraped_at": datetime.now().isoformat()
                }
    
    async def errback_playwright(self, failure):
        """Handle Playwright errors."""
        self.logger.error(f"❌ Playwright error: {failure}")
        
        try:
            page = failure.request.meta.get("playwright_page")
            if page:
                await page.close()
        except:
            pass
    
    def closed(self, reason):
        """Log statistics."""
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total articles scraped: {self.articles_scraped}")


class DailySunPlaywrightSpider(scrapy.Spider, PlaywrightMixin):
    """
    Playwright spider for Daily Sun (Cloudflare protected).
    
    Daily Sun uses Cloudflare protection which blocks regular HTTP requests.
    This spider uses Playwright to render the JavaScript and bypass the protection.
    
    Usage:
        scrapy crawl dailysun_playwright
        scrapy crawl dailysun_playwright -a category=bangladesh
        scrapy crawl dailysun_playwright -s CLOSESPIDER_ITEMCOUNT=10
    """
    
    name = "dailysun_playwright"
    allowed_domains = ["daily-sun.com", "www.daily-sun.com"]
    
    paper_name = "Daily Sun"
    source_language = "en"  # English newspaper
    
    # Custom settings for Playwright
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
        "PLAYWRIGHT_CONTEXTS": {
            "default": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        },
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 5,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 5,
        "AUTOTHROTTLE_MAX_DELAY": 30,
    }
    
    # News categories with their URL paths
    categories = {
        "bangladesh": "/bangladesh",
        "business": "/business",
        "world": "/world",
        "entertainment": "/entertainment",
        "sports": "/sports",
        "lifestyle": "/lifestyle",
        "tech": "/tech",
        "opinion": "/opinion",
    }
    
    BASE_URL = "https://www.daily-sun.com"
    
    def __init__(self, category: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_category = category
        self.articles_scraped = 0
        self.processed_urls = set()
        
    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests with Playwright for category pages."""
        
        # Filter categories if specified
        if self.target_category:
            if self.target_category.lower() in self.categories:
                cats = {self.target_category.lower(): self.categories[self.target_category.lower()]}
            else:
                self.logger.error(f"Unknown category: {self.target_category}")
                return
        else:
            # Default to a few main categories
            cats = {k: v for k, v in list(self.categories.items())[:3]}
        
        for cat_name, cat_path in cats.items():
            url = f"{self.BASE_URL}{cat_path}"
            self.logger.info(f"📰 Starting category: {cat_name} ({url})")
            
            yield Request(
                url=url,
                callback=self.parse_category,
                errback=self.errback_playwright,
                meta={
                    # Updated wait_for selectors for 2024-2025 layout
                    **self.get_playwright_meta(wait_for=".container, .row, h4, h5"),
                    "category": cat_name,
                }
            )
    
    async def parse_category(self, response) -> Generator:
        """Parse category page for article links."""
        category = response.meta.get("category", "Unknown")
        
        self.logger.info(f"📑 Parsing category: {category}")
        
        # Close the page after getting content
        page = response.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except:
                pass
        
        # Extract article links - updated selectors for current Daily Sun layout (2024-2025)
        # Primary: Use href pattern matching for /post/ links
        articles = response.css(
            'a[href^="/post/"]::attr(href), '         # Best: any link starting with /post/
            'a.row::attr(href), '                      # Row-based article links
            '.container a[href^="/post/"]::attr(href), '  # Container posts
            '.row a::attr(href), '                     # Row links
            'h4 a::attr(href), '                       # Headlines in h4
            'h5 a::attr(href)'                         # Headlines in h5
        ).getall()
        
        # Filter and deduplicate
        valid_articles = []
        for href in articles:
            if not href or href in self.processed_urls:
                continue
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            full_url = response.urljoin(href)
            
            # Only process article URLs (must have /post/ pattern)
            if '/post/' in full_url:
                if full_url not in self.processed_urls:
                    valid_articles.append(full_url)
                    self.processed_urls.add(full_url)
        
        self.logger.info(f"Found {len(valid_articles)} article links in {category}")
        
        for article_url in valid_articles[:20]:  # Limit per category
            yield Request(
                url=article_url,
                callback=self.parse_article,
                errback=self.errback_playwright,
                meta={
                    **self.get_playwright_meta(wait_for=".article-content, .post-content, .detail-content, .news-details"),
                    "category": category,
                }
            )
    
    async def parse_article(self, response) -> Generator:
        """Parse individual article with Playwright."""
        category = response.meta.get("category", "Unknown")
        
        # Close the page
        page = response.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except:
                pass
        
        # Extract headline
        headline = (
            response.css('h1.post-title::text').get() or
            response.css('h1.detail-title::text').get() or
            response.css('h1::text').get() or
            response.css('.article-headline::text').get() or
            ""
        ).strip()
        
        if not headline:
            self.logger.warning(f"No headline found: {response.url}")
            return
        
        # Extract article body
        body_parts = response.css('.article-content p::text, .post-content p::text, .detail-content p::text, .news-details p::text').getall()
        article_body = ' '.join([p.strip() for p in body_parts if p.strip()])
        
        if not article_body or len(article_body) < 50:
            self.logger.warning(f"Article too short: {response.url}")
            return
        
        # Extract date
        pub_date = (
            response.css('.post-date::text').get() or
            response.css('.article-date::text').get() or
            response.css('time::attr(datetime)').get() or
            response.css('.date::text').get() or
            "Unknown"
        )
        
        # Extract author
        author = (
            response.css('.author::text').get() or
            response.css('.post-author::text').get() or
            "Daily Sun"
        )
        
        # Extract image
        image_url = (
            response.css('.article-image img::attr(src)').get() or
            response.css('.post-image img::attr(src)').get() or
            response.css('article img::attr(src)').get()
        )
        
        self.articles_scraped += 1
        self.logger.info(f"✅ [{self.articles_scraped}] Scraped: {headline[:50]}...")
        
        yield {
            "paper_name": self.paper_name,
            "url": response.url,
            "headline": headline,
            "article_body": article_body,
            "category": category,
            "author": author,
            "publication_date": pub_date,
            "image_url": image_url,
            "source_language": self.source_language,
        }
    
    async def errback_playwright(self, failure):
        """Handle Playwright errors gracefully."""
        self.logger.error(f"❌ Playwright error: {failure}")
        
        try:
            page = failure.request.meta.get("playwright_page")
            if page:
                await page.close()
        except:
            pass
    
    def closed(self, reason):
        """Log statistics when spider closes."""
        self.logger.info("=" * 50)
        self.logger.info(f"DAILY SUN PLAYWRIGHT SPIDER STATISTICS")
        self.logger.info("=" * 50)
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total articles scraped: {self.articles_scraped}")
        self.logger.info(f"URLs processed: {len(self.processed_urls)}")
        self.logger.info("=" * 50)
