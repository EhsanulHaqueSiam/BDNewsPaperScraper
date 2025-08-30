import re
import sqlite3
from datetime import datetime

import pytz
import scrapy

from BDNewsPaper.items import ArticleItem


class NewsSpider(scrapy.Spider):
    name = "BDpratidin"
    allowed_domains = ["en.bd-pratidin.com"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }

    # Category configuration
    categories = [
        "national",
        "international", 
        "sports",
        "showbiz",
        "economy",
        "shuvosangho",
    ]
    
    # Pagination and date settings
    start_page = 1
    last_page = 1000
    
    # Timezone configuration
    dhaka_tz = pytz.timezone('Asia/Dhaka')
    
    processed_urls = set()
    should_stop = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Parse date arguments
        try:
            # Default to scraping from 2025-01-01 to current date
            self.start_date = datetime.strptime(
                kwargs.get('start_date', '2025-01-01'), '%Y-%m-%d'
            ).replace(tzinfo=self.dhaka_tz)
            self.end_date = datetime.strptime(
                kwargs.get('end_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'
            ).replace(tzinfo=self.dhaka_tz)
        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            self.start_date = datetime(2025, 1, 1, tzinfo=self.dhaka_tz)
            self.end_date = datetime.now().replace(tzinfo=self.dhaka_tz)
        
        self.logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        self.db_path = kwargs.get('db_path', 'news_articles.db')
        self.init_database()

    def init_database(self):
        """Initialize database with proper error handling."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.conn = None
            self.cursor = None

    def is_url_in_db(self, url):
        """Check if URL exists in database with error handling."""
        if not self.conn or not self.cursor:
            return False
            
        try:
            self.cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
            return self.cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"Database error checking URL {url}: {e}")
            return False

    def mark_url_scraped(self, url):
        """Mark URL as scraped in database."""
        if not self.conn or not self.cursor:
            return
            
        try:
            self.cursor.execute("INSERT OR IGNORE INTO articles (url) VALUES (?)", (url,))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Database error marking URL {url}: {e}")

    def start_requests(self):
        """Generate initial requests for all categories."""
        if self.should_stop:
            return
            
        for category in self.categories:
            url = f"https://en.bd-pratidin.com/{category}?page={self.start_page}"
            yield scrapy.Request(
                url,
                callback=self.parse_category,
                errback=self.handle_error,
                meta={"category": category, "page_number": self.start_page},
            )

    def parse_category(self, response):
        """Parse category page and extract article links."""
        if self.should_stop:
            return

        category = response.meta["category"]
        page_number = int(response.meta["page_number"])

        # Extract news links with error handling
        try:
            news_links = response.xpath(
                "//div[@class='col-12']//a[@class='stretched-link']/@href"
            ).getall()
        except Exception as e:
            self.logger.error(f"Error extracting news links from {response.url}: {e}")
            return

        if not news_links:
            self.logger.info(f"No news links found on page {page_number} for category {category}")
            return

        valid_links_count = 0
        for link in news_links:
            if self.should_stop:
                break

            try:
                absolute_link = response.urljoin(link)
                
                if absolute_link in self.processed_urls:
                    self.logger.debug(f"URL already processed in session: {absolute_link}")
                    continue

                # Skip URL if it already exists in the database
                if self.is_url_in_db(absolute_link):
                    self.logger.debug(f"URL already in database: {absolute_link}")
                    continue

                # Extract and validate date from URL
                date_obj = self.extract_date_from_url(absolute_link)
                
                # Skip if date is not found or outside our date range
                if date_obj:
                    if date_obj < self.start_date:
                        self.logger.info(f"Article date {date_obj} is before start date {self.start_date}")
                        self.should_stop = True
                        self.crawler.engine.close_spider(self, reason="Reached start date limit")
                        return
                    elif date_obj > self.end_date:
                        self.logger.debug(f"Article date {date_obj} is after end date {self.end_date}, skipping")
                        continue

                self.processed_urls.add(absolute_link)
                valid_links_count += 1

                yield scrapy.Request(
                    absolute_link,
                    callback=self.parse_news,
                    errback=self.handle_error,
                    meta={
                        "category": category,
                        "page_number": page_number,
                        "news_link": absolute_link,
                        "date": date_obj.strftime("%Y-%m-%d %H:%M:%S") if date_obj else "Unknown",
                    },
                )

            except Exception as e:
                self.logger.error(f"Error processing link {link}: {e}")
                continue

        # Pagination logic with safety checks
        if (not self.should_stop and 
            valid_links_count > 0 and 
            page_number < self.last_page):
            
            next_page = f"https://en.bd-pratidin.com/{category}?page={page_number + 1}"
            yield scrapy.Request(
                next_page,
                callback=self.parse_category,
                errback=self.handle_error,
                meta={"category": category, "page_number": page_number + 1},
            )
        else:
            self.logger.info(f"Pagination stopped for category {category}. "
                           f"Page: {page_number}, Valid links: {valid_links_count}, "
                           f"Should stop: {self.should_stop}")

    def extract_date_from_url(self, url):
        """Extract date from URL with error handling."""
        try:
            match = re.search(r"/(\d{4}/\d{2}/\d{2})/", url)
            if match:
                extracted_date = match.group(1)  # Extracts '2024/12/14'
                date_obj = datetime.strptime(extracted_date, "%Y/%m/%d")
                # Convert to timezone-aware datetime
                return self.dhaka_tz.localize(date_obj)
            else:
                self.logger.warning(f"No date pattern found in URL: {url}")
                return None
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error parsing date from URL {url}: {e}")
            return None

    def parse_news(self, response):
        """Parse individual news article."""
        if self.should_stop:
            return

        item = ArticleItem()
        url = response.meta.get("news_link", response.url)
        
        # Extract headline
        headline = response.xpath("//h1/text()").get()
        item["headline"] = headline.strip() if headline else "Unknown"

        # Extract sub-title with multiple attempts
        sub_title = response.xpath(
            "//h2[contains(@class, 'subtitle')]/text() | "
            "//p[@class='lead']/text() | "
            "//div[@class='summary']//text()"
        ).get()
        item["sub_title"] = sub_title.strip() if sub_title else "Unknown"

        # Extract article body with fallback methods
        article_paragraphs = response.xpath(
            "//div[@class='col-12']//div[@class='mt-3']//article//p/text()"
        ).getall()

        if not article_paragraphs:
            # Try alternative extraction methods
            article_paragraphs = response.xpath(
                "//article//p/text() | "
                "//div[contains(@class, 'content')]//p/text()"
            ).getall()

        if not article_paragraphs:
            # Try broader extraction
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
        item["category"] = response.meta.get("category", "Unknown")
        item["url"] = url
        item["article_body"] = article_body
        item["paper_name"] = "BD Pratidin"
        item["publication_date"] = response.meta.get("date", "Unknown")

        # Mark URL as scraped and yield item
        self.mark_url_scraped(url)
        yield item

    def handle_error(self, failure):
        """Handle request failures."""
        self.logger.error(f"Request failed: {failure.value}")
        if hasattr(failure.value, 'response') and failure.value.response:
            self.logger.error(f"Response status: {failure.value.response.status}")

    def closed(self, reason):
        """Close database connection and log statistics."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total unique URLs processed: {len(self.processed_urls)}")
