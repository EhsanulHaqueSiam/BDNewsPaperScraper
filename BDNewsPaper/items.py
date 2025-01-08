# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ArticleItem(scrapy.Item):
    headline = scrapy.Field()
    sub_title = scrapy.Field()
    image_url = scrapy.Field()
    publication_date = scrapy.Field()
    modification_date = scrapy.Field()
    article_body = scrapy.Field()
    keywords = scrapy.Field()
    author = scrapy.Field()
    paper_name = scrapy.Field()
    url = scrapy.Field()
    publisher = scrapy.Field()
    category = scrapy.Field()


