import scrapy
import json
from datetime import datetime
from BDNewsPaper.items import ArticleItem
import sqlite3
import re
import html
from scrapy.exceptions import CloseSpider


class DailysunSpider(scrapy.Spider):
    name = "dailysun"
    allowed_domains = ["www.daily-sun.com"]

    # List of categories to scrape
    categories = [
        "national",
        "economy",
        "diplomacy",
        "sports",
        "bashundhara-shuvosangho",
        "world",
        "opinion",
        "sun-faith",
        "feature",
        "sci-tech",
        "education-online",
        "health",
        "entertainment",
        "corporate",
    ]
    start_urls = [
        f"https://www.daily-sun.com/api/catpagination/online/{category}"
        for category in categories
    ]

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.daily-sun.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    # Pagination and date settings
    start_page = 1
    end_page = 10000
    end_date = datetime.strptime("2024-06-01", "%Y-%m-%d")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Connect to SQLite database
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()
        # Dictionary to track if scraping should continue for each category
        self.continue_scraping = {category: True for category in self.categories}

    def is_url_in_db(self, url):
        """Check if a URL exists in the database."""
        try:
            self.cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return False

    def start_requests(self):
        """Send requests for each category."""
        for start_url in self.start_urls:
            yield scrapy.Request(
                url=start_url,
                headers=self.headers,
                callback=self.parse_api,
                meta={"page": self.start_page, "category": start_url.split("/")[-1]},
            )

    def parse_api(self, response):
        """Parse JSON response and extract articles."""
        try:
            data = json.loads(response.text)
            articles = data.get("category", {}).get("data", [])
            category = response.meta["category"]

            if not self.continue_scraping[category]:
                self.logger.info(
                    f"Skipping category {category} as scraping has stopped."
                )
                return

            for article in articles:
                n_id = article.get("n_id")
                created_at = article.get("created_at")
                n_head = article.get("n_head")

                # Stop if the article's publish date is older than the end_date
                if created_at:
                    publish_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    if publish_date < self.end_date:
                        self.logger.info(
                            f"Stopping crawl for {category}: Article date {publish_date} < End date {self.end_date}"
                        )
                        self.continue_scraping[category] = False
                        break

                # Construct article URL
                post_url = f"https://www.daily-sun.com/post/{n_id}"

                # Skip if URL exists in the database
                if self.is_url_in_db(post_url):
                    self.logger.info(f"Skipping already scraped URL: {post_url}")
                    continue

                # Make a request to scrape the article with Playwright
                yield scrapy.Request(
                    url=post_url,
                    headers=self.headers,
                    callback=self.parse_post,
                    meta={
                        "playwright": True,
                        "publish_date": created_at,
                        "category": category,
                        "post_url": post_url,
                        "news_id": n_id,
                        "headline": n_head,
                    },
                )

            # Handle pagination
            current_page = response.meta["page"]
            if self.continue_scraping[category] and current_page < self.end_page:
                next_page = current_page + 1
                yield scrapy.Request(
                    url=response.url,
                    headers=self.headers,
                    callback=self.parse_api,
                    meta={"page": next_page, "category": category},
                    cb_kwargs={"page": next_page},
                )
            else:
                self.continue_scraping[category] = False
                # if all(not val for val in self.continue_scraping.values()):
                # CloseSpider("All categories processed.")
                # self.crawler.engine.close_spider(self, "All categories processed.")
        except Exception as e:
            self.logger.error(f"Error parsing JSON response: {e}")

    def parse_post(self, response):
        """Parse individual article pages."""
        item = ArticleItem()
        news_id = response.meta["news_id"]
        item["headline"] = response.meta["headline"]
        item["url"] = response.meta["post_url"]
        item["publication_date"] = response.meta["publish_date"]
        item["paper_name"] = "daily-sun"
        item["category"] = response.meta["category"]
        # Extract script data using XPath
        script_content = response.xpath(
            "//script[contains(text(), 'self.__next_f.push([1,\"\\u0026lt;')]/text()"
        ).get()

        if script_content:
            try:
                # Extract JSON-like data from the script content
                start = script_content.find("[")
                end = script_content.find("]") + 1
                data = script_content[start:end]

                # Parse the JSON data
                parsed_data = json.loads(data)

                # Decode the HTML content
                html_content = html.unescape(parsed_data[1])

                # Remove HTML tags using a regular expression
                plain_text = re.sub(r"<[^>]*>", "", html_content)
                item["article_body"] = plain_text.strip()
            except (json.JSONDecodeError, IndexError) as e:
                self.logger.error(f"Error parsing article body from script: {e}")
                item["article_body"] = ""
        else:
            self.logger.warning("No script tag found for article body extraction")
            item["article_body"] = ""
        return item

    def closed(self, reason):
        """Close database connection on spider close."""
        self.conn.close()
