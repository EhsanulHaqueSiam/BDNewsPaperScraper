import sqlite3
import time
from datetime import datetime

import pytz
import scrapy
from scrapy.http import Request

from BDNewsPaper.bengalidate_to_englishdate import convert_bengali_date_to_english
from BDNewsPaper.items import ArticleItem


class BangladeshTodaySpider(scrapy.Spider):
    name = "bangladesh_today"
    allowed_domains = ["thebangladeshtoday.com"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }
    
    # Category configuration
    category_dict = {
        1: "Bangladesh",
        93: "Nationwide", 
        94: "Entertainment",
        97: "International",
        95: "Sports",
        96: "Feature"
    }
    
    # Categories to scrape (can be configured)
    categories_to_scrape = [1, 93, 97]  # Bangladesh, Nationwide, International
    
    # Date and pagination settings
    dhaka_tz = pytz.timezone('Asia/Dhaka')
    stop_date = datetime(2024, 8, 5, tzinfo=dhaka_tz)
    stop_timestamp = int(stop_date.timestamp())
    
    max_pages_per_category = 50  # Prevent infinite pagination
    processed_urls = set()
    should_stop = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_path = f"{self.name}_urls.db"
        self.init_database()

    def init_database(self):
        """Initialize database with error handling."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraped_urls (
                    url TEXT PRIMARY KEY,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")

    def is_url_scraped(self, url):
        """Check if URL was previously scraped."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            self.logger.error(f"Database error checking URL {url}: {e}")
            return False

    def mark_url_scraped(self, url):
        """Mark URL as scraped in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO scraped_urls (url) VALUES (?)", (url,))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Database error marking URL {url}: {e}")

    def start_requests(self):
        """Generate initial requests for all categories."""
        if self.should_stop:
            return
            
        for category_id in self.categories_to_scrape:
            start_url = f"https://thebangladeshtoday.com/?cat={category_id}&paged=1"
            yield Request(
                start_url,
                callback=self.parse,
                errback=self.handle_error,
                meta={
                    'category_id': category_id,
                    'page_no': 1,
                    'category_name': self.category_dict.get(category_id, "Unknown")
                }
            )

    def parse(self, response):
        """Parse category page and extract article links."""
        if self.should_stop:
            return

        category_id = response.meta['category_id']
        page_no = response.meta['page_no']
        category_name = response.meta['category_name']

        # Extract article links
        article_links = response.xpath("//a[@class='ct-link']/@href").getall()
        
        if not article_links:
            self.logger.info(f"No articles found on page {page_no} for category {category_name}")
            return

        valid_articles_count = 0
        for article_link in article_links:
            if self.should_stop:
                break

            full_url = response.urljoin(article_link)
            
            if full_url in self.processed_urls:
                self.logger.debug(f"URL already processed in session: {full_url}")
                continue
                
            if self.is_url_scraped(full_url):
                self.logger.debug(f"URL already scraped: {full_url}")
                continue

            self.processed_urls.add(full_url)
            valid_articles_count += 1

            yield Request(
                full_url,
                callback=self.parse_article,
                errback=self.handle_error,
                meta={
                    'category_id': category_id,
                    'category_name': category_name,
                    'url': full_url
                }
            )

        # Handle pagination with safety limits
        if (not self.should_stop and 
            valid_articles_count > 0 and 
            page_no < self.max_pages_per_category):
            
            next_page_no = page_no + 1
            next_page_url = f"https://thebangladeshtoday.com/?cat={category_id}&paged={next_page_no}"
            
            yield Request(
                next_page_url,
                callback=self.parse,
                errback=self.handle_error,
                meta={
                    'category_id': category_id,
                    'page_no': next_page_no,
                    'category_name': category_name
                }
            )
        else:
            self.logger.info(f"Pagination stopped for category {category_name}. "
                           f"Page: {page_no}, Valid articles: {valid_articles_count}, "
                           f"Should stop: {self.should_stop}")

    def parse_article(self, response):
        """Parse individual article and extract content."""
        if self.should_stop:
            return

        item = ArticleItem()
        url = response.meta.get('url', response.url)
        category_id = response.meta.get('category_id')
        category_name = response.meta.get('category_name', "Unknown")

        # Extract publication date with error handling
        publication_date_str = response.xpath(
            "/html/body/section[3]/div/div[1]/div/div[2]/span/text()"
        ).get()

        if publication_date_str:
            try:
                article_date = convert_bengali_date_to_english(publication_date_str.strip())
                if article_date:
                    # Convert to timezone-aware datetime
                    article_datetime = self.dhaka_tz.localize(
                        datetime.combine(article_date, datetime.min.time())
                    )
                    
                    # Check if article is before stop date
                    if article_datetime < self.stop_date:
                        self.logger.info(f"Article date {article_datetime} is before stop date {self.stop_date}")
                        self.should_stop = True
                        self.crawler.engine.close_spider(self, reason="Reached stop date")
                        return
                    
                    item['publication_date'] = article_datetime.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    self.logger.error(f"Failed to convert Bengali date: {publication_date_str}")
                    item['publication_date'] = "Unknown"
            except Exception as e:
                self.logger.error(f"Error processing publication date '{publication_date_str}': {e}")
                item['publication_date'] = "Unknown"
        else:
            self.logger.warning(f"No publication date found for {url}")
            item['publication_date'] = "Unknown"

        # Extract headline
        headline = response.xpath("//h1[@class='ct-headline']/span[@class='ct-span']/text()").get()
        item['headline'] = headline.strip() if headline else "Unknown"

        # Extract sub-title with multiple attempts
        sub_title = response.xpath(
            "//h2[contains(@class, 'subtitle')]/text() | "
            "//p[@class='lead']/text() | "
            "//div[@class='ct-subtitle']//text()"
        ).get()
        item['sub_title'] = sub_title.strip() if sub_title else "Unknown"

        # Extract article body with fallback methods
        article_paragraphs = response.xpath(
            "//span[@class='ct-span oxy-stock-content-styles']/p/text()"
        ).getall()

        if not article_paragraphs:
            # Try alternative extraction methods
            article_paragraphs = response.xpath(
                "//div[contains(@class, 'content')]//p/text() | "
                "//div[contains(@class, 'article')]//p/text()"
            ).getall()

        if not article_paragraphs:
            # Try even broader extraction
            article_paragraphs = response.xpath(
                "//p/text()[normalize-space()]"
            ).getall()

        # Clean and join article body
        if article_paragraphs:
            article_body = " ".join(p.strip() for p in article_paragraphs if p.strip())
        else:
            self.logger.warning(f"No article body found for {url}")
            article_body = "Content not available"

        # Set other fields
        item['paper_name'] = "The Bangladesh Today"
        item['category'] = category_name
        item['url'] = url
        item['article_body'] = article_body

        # Mark URL as scraped and yield item
        self.mark_url_scraped(url)
        yield item

    def handle_error(self, failure):
        """Handle request failures."""
        self.logger.error(f"Request failed: {failure.value}")
        if hasattr(failure.value, 'response') and failure.value.response:
            self.logger.error(f"Response status: {failure.value.response.status}")

    def closed(self, reason):
        """Log statistics when spider closes."""
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total unique URLs processed: {len(self.processed_urls)}")

