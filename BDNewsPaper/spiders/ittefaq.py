import json
import sqlite3
import time
from datetime import datetime

import pytz
import scrapy
from scrapy.http import JsonRequest

from BDNewsPaper.items import ArticleItem


class IttefaqSpider(scrapy.Spider):
    name = "ittefaq"
    allowed_domains = ["ittefaq.com.bd", "en.ittefaq.com.bd"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ROBOTSTXT_OBEY': False,
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.BaseDupeFilter',
    }

    base_api_url = "https://en.ittefaq.com.bd/api/theme_engine/get_ajax_contents"
    
    headers = {
        "sec-ch-ua-platform": '"Linux"',
        "Referer": "https://en.ittefaq.com.bd/bangladesh",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
    }

    dhaka_tz = pytz.timezone('Asia/Dhaka')
    stop_date = datetime(2024, 8, 5, tzinfo=dhaka_tz)
    stop_timestamp = int(stop_date.timestamp())
    current_start = 0
    max_articles = 5000
    articles_per_page = 250
    processed_urls = set()
    should_stop = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Parse date arguments
        try:
            self.start_date = datetime.strptime(
                kwargs.get('start_date', '2024-06-01'), '%Y-%m-%d'
            ).replace(tzinfo=self.dhaka_tz)
            self.end_date = datetime.strptime(
                kwargs.get('end_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'
            ).replace(tzinfo=self.dhaka_tz)
        except ValueError as e:
            self.logger.error(f"Invalid date format: {e}")
            self.start_date = datetime(2024, 6, 1, tzinfo=self.dhaka_tz)
            self.end_date = datetime.now().replace(tzinfo=self.dhaka_tz)
        
        # Update stop_date to use start_date for consistency
        self.stop_date = self.start_date
        
        self.logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        self.db_path = kwargs.get('db_path', 'news_articles.db')
        self.init_database()

    def init_database(self):
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
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO scraped_urls (url) VALUES (?)", (url,))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Database error marking URL {url}: {e}")

    def start_requests(self):
        if self.should_stop:
            return
        
        yield JsonRequest(
            self.get_api_url(self.current_start, self.articles_per_page),
            headers=self.headers,
            callback=self.parse_api_response,
            errback=self.handle_error,
            meta={'current_start': self.current_start}
        )

    def get_api_url(self, start, count):
        return (f"{self.base_api_url}?widget=28&start={start}&count={count}"
                f"&page_id=1098&subpage_id=0&author=0&tags=&archive_time=&filter=")

    def parse_api_response(self, response):
        if self.should_stop:
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return

        html_content = data.get("html", "")
        if not html_content:
            self.logger.warning("No HTML content found in API response")
            return

        selector = scrapy.Selector(text=html_content)
        
        links = selector.xpath("//h2[@class='title']//a[@class='link_overlay']/@href").getall()
        
        if not links:
            self.logger.info("No more article links found, stopping pagination")
            return

        valid_links_count = 0
        for link in links:
            if self.should_stop:
                break
                
            full_url = response.urljoin(link)
            
            if full_url in self.processed_urls:
                self.logger.debug(f"URL already processed in current session: {full_url}")
                continue
                
            if self.is_url_scraped(full_url):
                self.logger.debug(f"URL already scraped in database: {full_url}")
                continue
            
            self.processed_urls.add(full_url)
            valid_links_count += 1
            
            yield scrapy.Request(
                full_url,
                callback=self.parse_news_article,
                errback=self.handle_error,
                meta={'url': full_url}
            )

        current_start = response.meta.get('current_start', 0)
        next_start = current_start + self.articles_per_page

        if (not self.should_stop and 
            next_start < self.max_articles and 
            valid_links_count > 0):
            
            self.current_start = next_start
            yield JsonRequest(
                self.get_api_url(self.current_start, self.articles_per_page),
                headers=self.headers,
                callback=self.parse_api_response,
                errback=self.handle_error,
                meta={'current_start': self.current_start}
            )
        else:
            self.logger.info(f"Pagination stopped. Next start: {next_start}, Should stop: {self.should_stop}, Valid links: {valid_links_count}")

    def parse_news_article(self, response):
        if self.should_stop:
            return

        item = ArticleItem()
        url = response.meta.get('url', response.url)

        publication_date_str = response.xpath("//span[@class='tts_time' and @itemprop='datePublished']/@content").get()
        
        if publication_date_str:
            try:
                article_date = datetime.fromisoformat(publication_date_str.replace('Z', '+00:00'))
                
                if article_date.tzinfo is None:
                    article_date = self.dhaka_tz.localize(article_date)
                else:
                    article_date = article_date.astimezone(self.dhaka_tz)
                
                article_timestamp = int(article_date.timestamp())
                
                if article_timestamp < self.stop_timestamp:
                    self.logger.info(f"Article date {article_date} is before stop date {self.stop_date}")
                    self.should_stop = True
                    self.crawler.engine.close_spider(self, reason="Reached stop date")
                    return
                
                item["publication_date"] = article_date.strftime("%Y-%m-%d %H:%M:%S")
                
            except (ValueError, TypeError) as e:
                self.logger.error(f"Error parsing publication date '{publication_date_str}': {e}")
                item["publication_date"] = "Unknown"
        else:
            self.logger.warning(f"No publication date found for {url}")
            item["publication_date"] = "Unknown"

        item["paper_name"] = "The Daily Ittefaq"
        
        category = response.xpath("//h2[@class='secondary_logo']//span/text()").get()
        item["category"] = category.strip() if category else "Unknown"
        
        headline = response.xpath("//h1/text()").get()
        item["headline"] = headline.strip() if headline else "Unknown"
        
        sub_title = response.xpath("//h2[@class='subtitle mb10']/text()").get()
        item["sub_title"] = sub_title.strip() if sub_title else "Unknown"
        
        item["url"] = url
        
        article_paragraphs = response.xpath(
            "//article[@class='jw_detail_content_holder content mb16']//div[@itemprop='articleBody']//p/text()"
        ).getall()
        
        if article_paragraphs:
            item["article_body"] = " ".join(p.strip() for p in article_paragraphs if p.strip())
        else:
            alternative_body = response.xpath(
                "//div[@itemprop='articleBody']//text()[normalize-space()]"
            ).getall()
            item["article_body"] = " ".join(t.strip() for t in alternative_body if t.strip())

        if not item["article_body"]:
            self.logger.warning(f"No article body found for {url}")
            item["article_body"] = "Content not available"

        self.mark_url_scraped(url)
        yield item

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.value}")
        if hasattr(failure.value, 'response') and failure.value.response:
            self.logger.error(f"Response status: {failure.value.response.status}")

    def closed(self, reason):
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Total unique URLs processed: {len(self.processed_urls)}")
