import scrapy
import re
from datetime import datetime
from BDNewsPaper.items import ArticleItem
import sqlite3  # Replace with your DB module if not using SQLite


class NewsSpider(scrapy.Spider):
    name = "BDpratidin"
    allowed_domains = ["en.bd-pratidin.com"]

    # Configurable variables
    categories = [
        "national",
        "international",
        "sports",
        "showbiz",
        "economy",
        "shuvosangho",
    ]
    start_page = 1  # Starting page number
    last_page = 1000  # Last page number
    stop_date = datetime.strptime("2024-06-01", "%Y-%m-%d")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Connect to your database
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()

    def is_url_in_db(self, url):
        """Checks if the URL is already in the database to avoid duplicates."""
        self.cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        return self.cursor.fetchone() is not None

    def start_requests(self):
        for category in self.categories:
            url = f"https://en.bd-pratidin.com/{category}?page={self.start_page}"
            yield scrapy.Request(
                url,
                callback=self.parse_category,
                meta={"category": category, "page_number": self.start_page},
            )

    def parse_category(self, response):
        category = response.meta["category"]
        page_number = int(response.meta["page_number"])

        # Extract news links using XPath
        news_links = response.xpath(
            "//div[@class='col-12']//a[@class='stretched-link']/@href"
        ).getall()
        for link in news_links:
            absolute_link = response.urljoin(link)

            # Skip URL if it already exists in the database
            if self.is_url_in_db(absolute_link):
                self.logger.info(f"URL already in DB, skipping: {absolute_link}")
                continue

            # Extract date from the link
            match = re.search(r"/(\d{4}/\d{2}/\d{2})/", absolute_link)
            if match:
                extracted_date = match.group(1)  # Extracts '2024/12/14'
                date_obj = datetime.strptime(extracted_date, "%Y/%m/%d")
            else:
                date_obj = None

            # If date is not found or older than the stop_date, skip the link
            if date_obj and date_obj < self.stop_date:
                continue

            yield scrapy.Request(
                absolute_link,
                callback=self.parse_news,
                meta={
                    "category": category,
                    "page_number": page_number,
                    "news_link": absolute_link,
                    "date": date_obj.strftime("%B %d, %Y") if date_obj else None,
                },
            )

        # Pagination logic
        if page_number < self.last_page:
            next_page = f"https://en.bd-pratidin.com/{category}?page={page_number + 1}"
            yield scrapy.Request(
                next_page,
                callback=self.parse_category,
                meta={"category": category, "page_number": page_number + 1},
            )

    def parse_news(self, response):
        item = ArticleItem()
        item["category"] = response.meta["category"]
        item["url"] = response.meta["news_link"]

        # Extract news title and content
        item["headline"] = response.xpath("//h1/text()").get()
        item["article_body"] = " ".join(
            response.xpath(
                "//div[@class='col-12']//div[@class='mt-3']//article//p/text()"
            ).getall()
        )
        item["paper_name"] = "bd-pratidin"
        item["publication_date"] = response.meta["date"]

        yield item

    def closed(self, reason):
        """Closes the database connection when the spider is closed."""
        self.conn.close()
