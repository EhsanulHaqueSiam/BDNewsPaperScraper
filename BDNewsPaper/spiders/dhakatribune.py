import scrapy


class DhakatribuneSpider(scrapy.Spider):
    name = "dhakatribune"
    allowed_domains = ["www.dhakatribune.com"]
    start_urls = ["https://www.dhakatribune.com"]

    def parse(self, response):
        pass
