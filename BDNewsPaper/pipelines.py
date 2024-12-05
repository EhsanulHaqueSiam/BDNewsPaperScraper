# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import sqlite3
from itemadapter.adapter import ItemAdapter
import os
from scrapy.exceptions import DropItem
from w3lib.html import remove_tags
import re


class BdnewspaperSQLitePipeline:

    def open_spider(self, spider):
        # Open a connection to the SQLite database
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()

        # Create the table if it doesn't exist
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT,
                content TEXT,
                published_date TEXT,
                url TEXT UNIQUE,
                paper_name TEXT
            )
            """
        )
        self.conn.commit()

    def close_spider(self, spider):
        # Close the connection to the database
        self.conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url")

        # Check if the URL already exists in the database
        self.cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
        result = self.cursor.fetchone()

        if result is None:
            try:
                # If no duplicate is found, proceed with the insertion
                self.cursor.execute(
                    """
                    INSERT INTO articles (headline, content, published_date, url, paper_name)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        item["headline"],
                        item["article_body"],
                        item["publication_date"],
                        item["url"],
                        item["paper_name"],
                    ),
                )
                self.conn.commit()
            except sqlite3.Error as e:
                spider.logger.error(f"Error inserting item: {e}")
        else:
            spider.logger.info(f"Duplicate entry for URL: {url}")
        return item


class ProthomaloPipeline:
    def process_item(self, item, spider):
        if item.get("paper_name") == "ProthomAlo":
            # Clean up text fields
            item["article_body"] = (
                item["article_body"]
                .replace("&lt;p&gt;", "")
                .replace("&lt;/p&gt;", "")
                .strip()
            )
            item["keywords"] = ", ".join(item["keywords"]) if item["keywords"] else None
        return item


class CleanArticlePipeline:
    def process_item(self, item, spider):
        if item.get("paper_name") == "ProthomAlo":
            # Clean the article body
            if "article_body" in item:
                item["article_body"] = self.clean_article_body(item["article_body"])

            # Validate and clean other fields
            item["headline"] = self.clean_text(
                item.get("headline", "No headline available")
            )
            item["author"] = self.clean_text(item.get("author", "Unknown author"))
            item["publication_date"] = item.get("publication_date", "Unknown date")
            item["image_url"] = item.get("image_url", None)

            # Drop items with no article body
            if not item["article_body"]:
                raise DropItem(
                    f"Missing article body in {item.get('url', 'unknown URL')}"
                )

        return item

    def clean_article_body(self, article_body):
        """Cleans the article body content."""
        # Remove HTML tags
        cleaned_body = remove_tags(article_body)

        # Replace special HTML entities with actual characters
        cleaned_body = re.sub(r"&lt;", "<", cleaned_body)
        cleaned_body = re.sub(r"&gt;", ">", cleaned_body)
        cleaned_body = re.sub(r"&amp;", "&", cleaned_body)

        # Normalize spaces and line breaks
        cleaned_body = re.sub(r"\s+", " ", cleaned_body).strip()
        return cleaned_body

    def clean_text(self, text):
        """Generic text cleaner."""
        if text:
            # Ensure text is a string
            if isinstance(text, list):
                text = " ".join(text)  # Join list elements into a single string
            # Remove HTML tags
            text = remove_tags(text)
            # Normalize spaces
            text = re.sub(r"\s+", " ", text).strip()
            return text
        return None
