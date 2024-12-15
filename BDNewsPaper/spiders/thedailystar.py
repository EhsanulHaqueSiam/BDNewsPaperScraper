import scrapy
import json
import sqlite3
from BDNewsPaper.items import ArticleItem
from datetime import datetime


class DailyStarSpider(scrapy.Spider):
    name = "thedailystar"
    start_urls = ["https://www.thedailystar.net/views/ajax"]

    # Categories with their respective view_args
    categories = {
        "bangladesh": "283517/3758266,3758256,3758241,3758236,3758231,3758226,3758221,3758216,3758211,3758191,3758151,3758146,3758126,3758121,3757891,3758061,3758056,3756996",
        "investigative-stories": "283541/3702396,3623811,3572756,3572761,3572191,3571361,3511731,3507671",
        "sports": "283517/3758266,3758256,3758241,3758236,3758231,3758226,3758221,3758216,3758211,3758191,3758151,3758146,3758126,3758121,3757891,3758061,3758056,3756996",
        "business": "2/3758176,3757931,3757926,3758186,3758166,3758161,3757916,3757911,3757906,3757446,3757306,3757741,3757736,3757896,3757886,3757271,3757261,3757901,3757396,3757341,3757301,3757256,3757251,3756926,3756911,3757726,3757721,3757701,3757676,3756556,3755041,3754296,3754276,3753386,3743596,3503666,3502291,3464146",
        "entertainment": "283449/3758206,3758246,3758196,3757596,3758181,3752971,3729961,3747171,3735641,3530211,3520611,3520606,3493576,3484971,3757551,3757326,3757316,3757291,3756606,3756311,3756306,3755801,3755651,3755721,3757626,3757536,3757201,3756611,3756546,3756521,3756296,3755836,3755606,3755561,3756636,3756626,3755841,3755541",
        "star-multimedia": "17/3755026,3753386,3754176,3755951,3752116,3751151,3748101,3747206,3746566,3745471,3530211,3522621,3520611,3506731,3520606,3493576,3493566,3493561,3474186,3743596,3503666,3502291,3464146,3451826,3444341,3434766,3412636,3411846,3406691,3744751,3742626,3742341,3742286,3636561,3601776,3558866,3551016,3545476,3448351,3443461,3400846,3394701,3392551",
        "environment": "21/3758171,3757746,3757401,3757266,3756566,3756221,3756186,3755846,3753116,3748351,3745556,3745391,3745026,3744691,3744636,3744236,3735681,3733471",
    }

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.thedailystar.net",
        "referer": "https://www.thedailystar.net",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }
    # Configuration for pagination
    start_page = 0
    end_page = 10000

    # Stopping date
    stop_date = datetime.strptime("2024-06-01", "%Y-%m-%d")

    custom_settings = {
        "CONCURRENT_REQUESTS": 32,
        "DOWNLOAD_DELAY": 0.5,
    }

    # Database connection
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()
        self.stop_scraping = {category: False for category in self.categories}

    def is_url_in_db(self, url):
        """Check if the URL is already in the database to avoid duplicates."""
        try:
            self.cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return False

    def closeConnection(self, reason):
        """Close the database connection."""
        self.conn.close()

    def start_requests(self):
        """Start requests for each category."""
        for category, view_args in self.categories.items():
            for page in range(self.start_page, self.end_page + 1):
                if not self.stop_scraping[category]:
                    payload = {
                        "page": str(page),
                        "view_name": "category_load_more_news",
                        "view_display_id": "panel_pane_1",
                        "view_args": view_args,
                    }
                    yield scrapy.FormRequest(
                        url=self.start_urls[0],
                        formdata=dict(payload),
                        headers=self.headers,
                        callback=self.parse_ajax,
                        meta={"category": category, "page": page},
                    )

    def parse_ajax(self, response):
        """Parse the JSON response and extract news links."""
        try:
            data = json.loads(response.text)
            for item in data:
                if item.get("command") == "insert":
                    html_fragment = item.get("data")
                    if html_fragment:
                        selector = scrapy.Selector(text=html_fragment)
                        links = selector.xpath(
                            '//a[@href and contains(@href, "/news/")]/@href'
                        ).getall()
                        for link in links:
                            full_link = response.urljoin(link)
                            if not self.is_url_in_db(full_link):
                                yield scrapy.Request(
                                    url=full_link,
                                    callback=self.parse_news,
                                    meta={"category": response.meta["category"]},
                                )
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")

    def parse_news(self, response):
        """Extract detailed news data from individual pages."""
        item = ArticleItem()
        item["headline"] = response.xpath("//h1/text()").get()
        item["article_body"] = " ".join(
            response.xpath("//div[@class = 'pb-20 clearfix']//p/text()").getall()
        )
        date_text = response.xpath("//div[contains(@class, 'date')]/text()[1]").get()
        item["publication_date"] = date_text.strip() if date_text else None
        item["url"] = response.url
        item["paper_name"] = "thedailystar"
        item["category"] = response.meta["category"]

        # Parse the publication date
        if item["publication_date"]:
            try:
                pub_date = datetime.strptime(
                    item["publication_date"], "%a %b %d, %Y %I:%M %p"
                )
                if pub_date <= self.stop_date:
                    self.stop_scraping[response.meta["category"]] = True
                    self.logger.info(
                        f"Stopping scraping for category '{response.meta['category']}' as publication date {pub_date} is before or equal to stop date {self.stop_date}."
                    )
            except ValueError as e:
                self.logger.warning(f"Error parsing date: {e}")

        return item
