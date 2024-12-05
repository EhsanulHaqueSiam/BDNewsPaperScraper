import scrapy
from datetime import datetime
import pytz
import json
import sqlite3
from BDNewsPaper.items import ArticleItem


class ProthomaloSpider(scrapy.Spider):
    name = "prothomalo"
    allowed_domains = ["en.prothomalo.com"]
    start_urls = ["https://en.prothomalo.com"]

    local_timezone = pytz.timezone("Asia/Dhaka")
    startDateTime = "2024-06-01 00:00:00"
    endDateTime = "2024-12-13 23:59:59"

    start_dt = local_timezone.localize(
        datetime.strptime(startDateTime, "%Y-%m-%d %H:%M:%S")
    )
    end_dt = local_timezone.localize(
        datetime.strptime(endDateTime, "%Y-%m-%d %H:%M:%S")
    )
    startDateTimeUnix = int(start_dt.timestamp() * 1000)
    endDateTimeUnix = int(end_dt.timestamp() * 1000)

    offset = 0
    limit = 1000
    base_url = "https://en.prothomalo.com/api/v1/advanced-search"

    categories = {
        "Bangladesh": "16600,16725,16727,16728,17129,17134,17135,17136,17137,17139,35627",
        "Sports": "16603,16747,16748,17138",
        "Opinion": "16606,16751,16752,17202",
        "Entertainment": "16604,16762,35629,35639,35640",
        "Youth": "16622,16756,17140",
        "Environment": "16623,16767,16768",
        "Science & Tech": "16605,16770,16771,17143",
        "Corporate": "16624,16772,16773",
    }

    def __init__(self, *args, **kwargs):
        super(ProthomaloSpider, self).__init__(*args, **kwargs)
        # Initialize database connection to check for duplicate URLs
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()

    def start_requests(self):
        for category, section_id in self.categories.items():
            yield self.make_api_request(category, section_id)

    def make_api_request(self, category, section_id, offset=0):
        api_url = (
            f"{self.base_url}?section-id={section_id}"
            f"&published-after={self.startDateTimeUnix}"
            f"&published-before={self.endDateTimeUnix}"
            f"&sort=latest-published&offset={offset}&limit={self.limit}"
            "&fields=headline%2Csubheadline%2Cslug%2Curl%2Ctags%2Chero-image-s3-key"
            "%2Chero-image-caption%2Chero-image-metadata%2Clast-published-at%2Calternative"
            "%2Cauthors%2Cauthor-name%2Cauthor-id%2Csections%2Cstory-template%2Cmetadata"
            "%2Chero-image-attribution%2Caccess"
        )
        return scrapy.Request(
            api_url,
            callback=self.parse_api_response,
            meta={"category": category, "section_id": section_id, "offset": offset},
            errback=self.handle_request_failure,
        )

    def parse_api_response(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {response.url}")
            return
        category = response.meta["category"]
        section_id = response.meta["section_id"]
        offset = response.meta["offset"]

        total_results = data.get("total", 0)
        items = data.get("items", [])

        for item in items:
            url = item.get("url")
            if url:
                full_url = response.urljoin(url)
                if not self.is_url_in_db(full_url):
                    yield scrapy.Request(
                        full_url,
                        callback=self.parse_news_article,
                        meta={"category": category},
                        errback=self.handle_request_failure,
                    )

        # Paginate if there are more items
        if offset + self.limit < total_results:
            next_offset = offset + self.limit
            yield self.make_api_request(category, section_id, offset=next_offset)

    def is_url_in_db(self, url):
        """Checks if the URL is already in the database to avoid duplicates."""
        self.cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        return self.cursor.fetchone() is not None

    def parse_news_article(self, response):
        self.logger.info(f"Processing URL: {response.url}")
        # Extract all <script> tags with type application/ld+json
        scripts = response.xpath(
            "//script[@type='application/ld+json']/text()"
        ).getall()

        for script in scripts:
            try:
                # Attempt to parse JSON content
                data = json.loads(script)

                # Look for relevant types
                if data.get("@type") in ["Article", "NewsArticle"]:
                    item = self.extract_data(data, response)
                    if item:
                        yield item

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error in {response.url}: {e}")
            except KeyError as e:
                self.logger.error(f"Missing key error in {response.url}: {e}")
            except Exception as e:
                self.logger.exception(f"Unexpected error in {response.url}: {e}")

    def extract_data(self, data, response=None):
        """Extract and validate article data."""
        item = ArticleItem()
        item["headline"] = data.get("headline", "No headline available")

        # Image handling: If there are multiple images, store them all in a list
        image_data = data.get("image", [])
        if isinstance(image_data, list):
            item["image_url"] = [
                img.get("url")
                for img in image_data
                if isinstance(img, dict) and img.get("url")
            ]
        elif isinstance(image_data, dict):
            item["image_url"] = [image_data.get("url")]
        else:
            item["image_url"] = None

        # Date parsing
        item["publication_date"] = data.get("datePublished", "Unknown date")
        item["modification_date"] = data.get("dateModified", "Unknown date")

        # Body content
        item["article_body"] = data.get("articleBody", "No article body")

        # Keywords handling: If the keywords are a list, join them as a string, otherwise treat them as they are
        keywords = data.get("keywords", [])
        if isinstance(keywords, list):
            # Ensure each keyword is a valid string and join them with commas
            item["keywords"] = ", ".join(
                [
                    str(keyword).strip()
                    for keyword in keywords
                    if isinstance(keyword, str)
                ]
            )
        elif isinstance(keywords, str):
            # If keywords is a single string (e.g., comma-separated), just assign it
            item["keywords"] = keywords
        else:
            item["keywords"] = None

        item["url"] = data.get("url", response.url if response else "Unknown URL")

        # Publisher
        publisher_data = data.get("publisher", {})
        item["publisher"] = publisher_data.get("name", "Unknown publisher")

        # Author handling
        item["author"] = self.extract_authors(data)

        # Fixed source name
        item["paper_name"] = "ProthomAlo"

        return item

    def extract_authors(self, data):
        """Extract author(s) information."""
        authors = data.get("author", [])
        if isinstance(authors, list):
            return [author.get("name", "Unknown") for author in authors]
        elif isinstance(authors, dict):
            return [authors.get("name", "Unknown")]
        return ["Unknown"]

    def handle_request_failure(self, failure):
        self.logger.error(f"Request failed for {failure.request.url}: {failure.value}")

    def closeConnection(self, reason):
        self.conn.close()
