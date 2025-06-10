import scrapy
import json
from scrapy.http import JsonRequest
from BDNewsPaper.items import ArticleItem
from datetime import datetime
import time  # For handling Unix timestamps


class IttefaqSpider(scrapy.Spider):
    name = "ittefaq"
    start_urls = [
        "https://en.ittefaq.com.bd/api/theme_engine/get_ajax_contents?widget=28&start=0&count=250&page_id=1098&subpage_id=0&author=0&tags=&archive_time=&filter="
    ]

    headers = {
        "sec-ch-ua-platform": '"Linux"',
        "Referer": "https://en.ittefaq.com.bd/bangladesh",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
    }

    stop_timestamp = int(
        time.mktime(datetime.strptime("2024-08-05", "%Y-%m-%d").timetuple())
    )  # Convert stop date to Unix timestamp
    current_start = 0  # Start from the first page (start=0)

    def start_requests(self):
        # Initiate the first request
        yield JsonRequest(self.get_url(self.current_start, 250), headers=self.headers)

    def get_url(self, start, count):
        # Helper function to build the URL with the given start and count parameters
        return f"https://en.ittefaq.com.bd/api/theme_engine/get_ajax_contents?widget=28&start={start}&count={count}&page_id=1098&subpage_id=0&author=0&tags=&archive_time=&filter="

    def parse(self, response):
        data = json.loads(response.text)
        html_content = data.get("html", "")

        # Use Scrapy's Selector to parse HTML content
        selector = scrapy.Selector(text=html_content)

        # Extract hrefs based on the provided XPath
        links = selector.xpath(
            "//h2[@class='title']//a[@class='link_overlay']/@href"
        ).getall()

        # Normalize URLs and yield
        for link in links:
            full_url = response.urljoin(link)
            yield scrapy.Request(full_url, callback=self.parse_article)

        # Pagination logic: after processing 250 items, request the next page
        current_count = 250  # After processing 250 items, update this value
        next_start = self.current_start + current_count

        if next_start < 5000:  # Stop if we reach the 1000 limit
            self.current_start = next_start
            next_url = self.get_url(self.current_start, 250)
            yield JsonRequest(next_url, headers=self.headers)

    def parse_article(self, response):
        # This is the callback that will handle the data from the article page
        item = ArticleItem()  # Create an instance of ArticleItem

        # Extract the publication date
        publication_date = response.xpath(
            "//span[@class='tts_time' and @itemprop='datePublished']/@content"
        ).get()

        if publication_date:
            try:
                # Convert the extracted date to a Unix timestamp
                article_date = datetime.fromisoformat(publication_date)
                article_timestamp = int(time.mktime(article_date.timetuple()))
                print(f"paper published data is: {article_timestamp}")
                # Format the date as 'YYYY-MM-DD HH:MM:SS'
                item["publication_date"] = article_date.strftime("%Y-%m-%d %H:%M:%S")

                # Check if the date is older than the stop date
                if article_timestamp < self.stop_timestamp:
                    self.logger.info(
                        f"Stopping scraping, article date {article_date} is newer than stop date {datetime.fromtimestamp(self.stop_timestamp)}"
                    )
                    self.crawler.engine.close_spider(self, reason="Date condition met")
            except Exception as e:
                self.logger.error(f"Error parsing date: {e}")
                return

        # Extract other data
        item["paper_name"] = "The Daily ittefaq"
        item["category"] = (
            response.xpath("//h2[@class='secondary_logo']//span/text()")
            .get(default="Unknown")
            .strip()
        )
        item["headline"] = response.xpath("//h1/text()").get()
        item["sub_title"] = (
            response.xpath("//h2[@class='subtitle mb10']/text()")
            .get(default="Unknown")
            .strip()
        )
        item["url"] = response.url
        item["article_body"] = " ".join(
            response.xpath(
                "//article[@class='jw_detail_content_holder content mb16']//div[@itemprop='articleBody']//p/text()"
            ).getall()
        )

        # Yield the populated item
        yield item
