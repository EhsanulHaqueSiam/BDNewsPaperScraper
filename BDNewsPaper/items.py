# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BdnewspaperItem(scrapy.Item):
    headline = scrapy.Field()
    content = scrapy.Field()
    published_date = scrapy.Field()
    url = scrapy.Field()
    paper_name = scrapy.Field()
    # Additional fields as needed
