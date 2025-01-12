import scrapy
from scrapy.http import Request
from NewspaperBD.items import ArticleItem
from datetime import datetime
import time
from NewspaperBD.bengalidate_to_englishdate import convert_bengali_date_to_english

class BangladeshTodaySpider(scrapy.Spider):
    name = "bangladesh_today"
    allowed_domains = ["thebangladeshtoday.com"]
    # Dynamic category ID and starting page
    catagory_id = 1  # Set your category ID here
    category_dict = {
    1: "Bangladesh",
    93: "Nationwide",
    94: "Entertainment",
    97: "International",
    95: "Sports",
    96: "Feature"
    }
    page_no = 1
    stop_date = "2024-08-05"  # Stop scraping articles older than this date

    # Convert the stop date to a Unix timestamp
    stop_timestamp = int(time.mktime(datetime.strptime(stop_date, "%Y-%m-%d").timetuple()))

    # Generate the start URL dynamically
    def start_requests(self):
        start_url = f"https://thebangladeshtoday.com/?cat={self.catagory_id}&paged={self.page_no}"
        yield Request(start_url, callback=self.parse)

    def parse(self, response):
        # Parse all articles on the current page
        articles = response.xpath("//a[@class='ct-link']/@href").getall()
        for article in articles:
            full_url = response.urljoin(article)
            yield Request(full_url, callback=self.parse_article)

        # Handle pagination
        self.page_no += 1
        next_page_url = f"https://thebangladeshtoday.com/?cat={self.catagory_id}&paged={self.page_no}"
        yield Request(next_page_url, callback=self.parse)

    def parse_article(self, response):
        # Extract article details
        item = ArticleItem()

        # Publication date extraction
        publication_date = response.xpath("/html/body/section[3]/div/div[1]/div/div[2]/span/text()").get()

        if publication_date:
            # Convert the Bengali date to English date
            article_date = convert_bengali_date_to_english(publication_date)
            if article_date:
                item['publication_date'] = article_date.strftime('%Y-%m-%d')

                # Stop condition based on the date
                article_timestamp = int(time.mktime(article_date.timetuple()))
                if article_timestamp < self.stop_timestamp:
                    self.logger.info(f"Stopping spider. Article date {article_date} is older than stop date.")
                    self.crawler.engine.close_spider(self, reason="Date condition met")
                    return
            else:
                self.logger.error(f"Error converting date: {publication_date}")

        # Extract other fields
        item['paper_name'] = "The Bangladesh Today"
        item['category'] = self.category_dict.get(self.catagory_id, "Category not found")  # Corrected line
        item['headline'] = response.xpath("//h1[@class='ct-headline']/span[@class='ct-span']/text()").get()
        item['url'] = response.url
        item['article_body'] = " ".join(response.xpath("//span[@class='ct-span oxy-stock-content-styles']/p/text()").getall())

        yield item

