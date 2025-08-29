import json
import sqlite3
from datetime import datetime

import pytz
import scrapy
from scrapy.http.request import Request

from BDNewsPaper.items import ArticleItem


class NewsSpider(scrapy.Spider):
    name = "kalerKantho"
    allowed_domains = ["en.api-kalerkantho.com", "kalerkantho.com"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }
    
    base_api_url = "https://en.api-kalerkantho.com/api/online/{category}?page={page}"
    base_article_url = "https://www.kalerkantho.com/online/{slug}/{f_date}/{n_id}"

    categories = ["country-news", "national", "Politics"]
    max_pages = 1000
    
    # Use more reasonable stop dates (past dates for actual stopping)
    dhaka_tz = pytz.timezone('Asia/Dhaka')
    stop_date = datetime(2024, 8, 5, tzinfo=dhaka_tz)
    
    processed_urls = set()
    should_stop = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_path = f"{self.name}_urls.db"
        self.init_database()

    def init_database(self):
        """Initialize database with error handling."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
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
        if self.should_stop:
            return
            
        for category in self.categories:
            for page in range(1, self.max_pages + 1):
                if self.should_stop:
                    break
                    
                url = self.base_api_url.format(category=category, page=page)
                yield Request(
                    url,
                    callback=self.parse_api,
                    errback=self.handle_error,
                    meta={"category": category, "page": page},
                )

    def parse_api(self, response):
        if self.should_stop:
            return

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return

        articles = data.get("category", {}).get("data", [])
        category = response.meta["category"]
        page = response.meta["page"]

        if not articles:
            self.logger.info(f"No articles found for category {category} on page {page}")
            return

        valid_articles_count = 0
        for article in articles:
            if self.should_stop:
                break

            try:
                f_date = article.get("f_date", "").replace("/", "-")
                if not f_date:
                    self.logger.warning("Article missing f_date, skipping")
                    continue

                # Parse article date with timezone awareness
                try:
                    article_date = datetime.strptime(f_date, "%Y-%m-%d")
                    article_date = self.dhaka_tz.localize(article_date)
                except ValueError as e:
                    self.logger.error(f"Invalid date format {f_date}: {e}")
                    continue

                # Check if article is before stop date
                if article_date < self.stop_date:
                    self.logger.info(f"Article date {article_date} is before stop date {self.stop_date}")
                    self.should_stop = True
                    self.crawler.engine.close_spider(self, reason="Reached stop date")
                    return

                n_id = article.get("n_id")
                n_head = article.get("n_head", "")
                cat_name = article.get("cat_name", {})
                slug = cat_name.get("slug", "") if isinstance(cat_name, dict) else ""

                if not all([n_id, slug]):
                    self.logger.warning(f"Article missing required fields: n_id={n_id}, slug={slug}")
                    continue

                article_url = self.base_article_url.format(
                    slug=slug, f_date=f_date, n_id=n_id
                )

                if article_url in self.processed_urls:
                    self.logger.debug(f"URL already processed in session: {article_url}")
                    continue

                if self.is_url_in_db(article_url):
                    self.logger.debug(f"URL already in database: {article_url}")
                    continue

                self.processed_urls.add(article_url)
                valid_articles_count += 1

                yield Request(
                    article_url,
                    callback=self.parse_article,
                    errback=self.handle_error,
                    meta={
                        "headline": n_head,
                        "publication_date": f_date,
                        "url": article_url,
                        "category": category,
                    },
                )

            except Exception as e:
                self.logger.error(f"Error processing article in category {category}: {e}")
                continue

        if valid_articles_count == 0:
            self.logger.info(f"No valid articles found for category {category} on page {page}")

    def parse_article(self, response):
        if self.should_stop:
            return

        headline = response.meta.get("headline", "Unknown")
        publication_date = response.meta.get("publication_date", "Unknown")
        url = response.meta.get("url", response.url)
        category = response.meta.get("category", "Unknown")

        # Extract article body with multiple fallback methods
        body_paragraphs = response.xpath(
            "//div[@class='single_news'][1]//div[@class='newsArticle']//article[@class='my-5']//p/text()"
        ).getall()

        if not body_paragraphs:
            # Try alternative extraction methods
            body_paragraphs = response.xpath(
                "//div[@class='newsArticle']//p/text()"
            ).getall()

        if not body_paragraphs:
            # Try even broader extraction
            body_paragraphs = response.xpath(
                "//article//p/text()[normalize-space()]"
            ).getall()

        # Clean and join body text
        if body_paragraphs:
            article_body = "\n".join(p.strip() for p in body_paragraphs if p.strip())
        else:
            self.logger.warning(f"No article body found for {url}")
            article_body = "Content not available"

        # Extract subtitle if available
        sub_title = response.xpath(
            "//div[@class='single_news']//h2[@class='sub-title']/text() | "
            "//h2[contains(@class, 'subtitle')]/text() | "
            "//p[@class='lead']/text()"
        ).get()
        
        if sub_title:
            sub_title = sub_title.strip()
        else:
            sub_title = "Unknown"

        # Create and yield article item
        article = ArticleItem(
            headline=headline.strip() if headline else "Unknown",
            sub_title=sub_title,
            publication_date=publication_date,
            article_body=article_body,
            paper_name="Kaler Kantho",
            url=url,
            category=category,
        )

        # Mark URL as scraped
        self.mark_url_scraped(url)
        yield article

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
