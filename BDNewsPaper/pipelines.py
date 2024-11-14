# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import sqlite3
from itemadapter import ItemAdapter
import os


class BdnewspaperSQLitePipeline:
    def open_spider(self, spider):
        # Check if the database file exists before opening a connection
        db_exists = os.path.exists("news_articles.db")

        # Open a connection to the SQLite database (or create it if it doesn't exist)
        self.conn = sqlite3.connect("news_articles.db")
        self.cursor = self.conn.cursor()

        # Only create the table if the database was just created
        if not db_exists:
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
                        adapter.get("headline"),
                        adapter.get("content"),
                        adapter.get("published_date"),
                        adapter.get("url"),
                        adapter.get("paper_name"),
                    ),
                )
                self.conn.commit()
            except sqlite3.Error as e:
                spider.logger.error(f"Error inserting item: {e}")
        else:
            spider.logger.info(f"Duplicate entry for URL: {url}")
        return item
