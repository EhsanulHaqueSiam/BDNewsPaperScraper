import scrapy
from scrapy.http.request import Request
from datetime import datetime
import sqlite3
from BDNewsPaper.items import ArticleItem


class NewsSpider(scrapy.Spider):
    name = "kalerKantho"
    allowed_domains = ["en.api-kalerkantho.com", "kalerkantho.com"]
    base_api_url = "https://en.api-kalerkantho.com/api/online/{category}?page={page}"
    base_article_url = "https://www.kalerkantho.com/online/{slug}/{f_date}/{n_id}"

    categories = ["country-news", "national", "Politics"]
    max_pages = 1000
    end_dates = {
        "country-news": "2024-12-31",
        "national": "2024-12-30",
        "Politics": "2024-12-29",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Creates the articles table if it doesn't exist."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE
            )
        """
        )
        self.conn.commit()

    def is_url_in_db(self, url):
        """Checks if the URL is already in the database to avoid duplicates."""
        self.cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        return self.cursor.fetchone() is not None

    def start_requests(self):
        for category in self.categories:
            end_date = self.end_dates.get(category, "2024-12-31")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            current_date = datetime.now()

            if current_date > end_date_obj:
                self.log(
                    f"End date {end_date} reached for category {category}. Skipping."
                )
                continue

            for page in range(1, self.max_pages + 1):
                url = self.base_api_url.format(category=category, page=page)
                yield Request(
                    url,
                    callback=self.parse_api,
                    meta={"category": category, "end_date": end_date, "page": page},
                )

    def parse_api(self, response):
        data = response.json()
        articles = data.get("category", {}).get("data", [])
        end_date_obj = datetime.strptime(response.meta["end_date"], "%Y-%m-%d")
        category = response.meta["category"]
        page = response.meta["page"]

        if not articles:
            self.log(
                f"No articles found for category {category} on page {page}. Stopping pagination."
            )
            return

        for article in articles:
            f_date = article["f_date"].replace("/", "-")
            article_date_obj = datetime.strptime(f_date, "%Y-%m-%d")

            if article_date_obj > end_date_obj:
                self.log(
                    f"Skipping article dated {f_date} as it exceeds end date {response.meta['end_date']}."
                )
                continue

            n_id = article["n_id"]
            n_head = article["n_head"]
            slug = article["cat_name"]["slug"]

            article_url = self.base_article_url.format(
                slug=slug, f_date=f_date, n_id=n_id
            )
            if self.is_url_in_db(article_url):
                self.log(f"URL {article_url} already in database. Skipping.")
                continue

            yield Request(
                article_url,
                callback=self.parse_article,
                meta={
                    "headline": n_head,
                    "publication_date": f_date,
                    "url": article_url,
                    "category": category,
                },
            )

    def parse_article(self, response):
        headline = response.meta["headline"]
        publication_date = response.meta["publication_date"]
        url = response.meta["url"]
        category = response.meta["category"]
        body = response.xpath(
            "//div[@class='single_news'][1]//div[@class='newsArticle']//article[@class='my-5']//p/text()"
        ).getall()

        article = ArticleItem(
            headline=headline,
            publication_date=publication_date,
            article_body="\n".join(body),
            paper_name="Kaler Kantho",
            url=url,
            category=category,
        )
        yield article

    def closed(self, reason):
        """Close the database connection when the spider finishes."""
        self.conn.close()
