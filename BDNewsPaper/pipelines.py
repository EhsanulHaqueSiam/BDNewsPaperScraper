# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import sqlite3
from itemadapter.adapter import ItemAdapter
import os
from scrapy.exceptions import DropItem
from w3lib.html import remove_tags
import re
import hashlib
from datetime import datetime
import logging


class ValidationPipeline:
    """Enhanced validation pipeline for data quality."""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Required fields validation
        required_fields = ['headline', 'url', 'paper_name']
        for field in required_fields:
            if not adapter.get(field):
                raise DropItem(f"Missing required field: {field} in {adapter.get('url', 'unknown URL')}")
        
        # URL validation
        url = adapter.get('url')
        if not self._is_valid_url(url):
            raise DropItem(f"Invalid URL format: {url}")
        
        # Content length validation
        article_body = adapter.get('article_body', '')
        if len(article_body.strip()) < 50:  # Minimum content length
            raise DropItem(f"Article too short ({len(article_body)} chars): {url}")
        
        return item
    
    def _is_valid_url(self, url):
        """Basic URL validation."""
        if not url or not isinstance(url, str):
            return False
        return url.startswith(('http://', 'https://'))


class SharedSQLitePipeline:
    """Single shared SQLite database for all spiders with essential fields only."""

    def open_spider(self, spider):
        self.conn = sqlite3.connect("news_articles.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Enable WAL mode for better performance
        self.cursor.execute("PRAGMA journal_mode=WAL;")
        self.cursor.execute("PRAGMA synchronous=NORMAL;")
        self.cursor.execute("PRAGMA cache_size=10000;")
        self.cursor.execute("PRAGMA temp_store=MEMORY;")

        # Simplified table schema with only essential fields
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                paper_name TEXT NOT NULL,
                headline TEXT NOT NULL,
                article TEXT NOT NULL,
                publication_date TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        # Create indexes for better query performance
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON articles(url);")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_name ON articles(paper_name);")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_publication_date ON articles(publication_date);")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraped_at ON articles(scraped_at);")
        
        self.conn.commit()
        spider.logger.info(f"Database initialized for spider: {spider.name}")

    def close_spider(self, spider):
        # Get final count
        self.cursor.execute("SELECT COUNT(*) FROM articles WHERE paper_name = ?", (spider.name,))
        count = self.cursor.fetchone()[0]
        spider.logger.info(f"Spider {spider.name} saved {count} articles to shared database")
        
        # Optimize database on close
        self.cursor.execute("VACUUM;")
        self.conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url")
        
        # Check for duplicates by URL only (simpler and faster)
        self.cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
        result = self.cursor.fetchone()

        if result is None:
            try:
                # Extract only essential fields
                headline = self._clean_text(adapter.get("headline", ""))
                article_body = self._clean_text(adapter.get("article_body", ""))
                paper_name = adapter.get("paper_name", spider.name)
                publication_date = adapter.get("publication_date")
                
                # Validate essential fields
                if not headline or not article_body:
                    raise DropItem(f"Missing essential content for URL: {url}")
                
                self.cursor.execute(
                    """
                    INSERT INTO articles (url, paper_name, headline, article, publication_date)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (url, paper_name, headline, article_body, publication_date)
                )
                self.conn.commit()
                spider.logger.info(f"Saved article: {headline[:50]}...")
                
            except sqlite3.Error as e:
                spider.logger.error(f"Database error for {url}: {e}")
                raise DropItem(f"Database error: {e}")
        else:
            spider.logger.debug(f"Duplicate URL skipped: {url}")
            raise DropItem(f"Duplicate entry for URL: {url}")
        
        return item
    
    def _clean_text(self, text):
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Convert to string if needed
        if isinstance(text, list):
            text = " ".join(str(t) for t in text if t)
        
        text = str(text)
        
        # Remove HTML tags
        text = remove_tags(text)
        
        # Replace common HTML entities
        html_entities = {
            '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"',
            '&apos;': "'", '&nbsp;': ' ', '&#39;': "'", '&#x27;': "'"
        }
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove unwanted patterns
        unwanted_patterns = [
            r'^\s*Advertisement\s*',
            r'\s*Read more:.*$',
            r'\s*Subscribe.*$',
            r'\s*Click here.*$'
        ]
        for pattern in unwanted_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()


class CleanArticlePipeline:
    """Enhanced article cleaning pipeline for text processing."""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Clean the article body
        if adapter.get("article_body"):
            item["article_body"] = self._clean_article_body(adapter.get("article_body"))

        # Clean headline
        item["headline"] = self._clean_text(adapter.get("headline", ""))
        
        # Handle author field (convert list to string if needed)
        author = adapter.get("author")
        if isinstance(author, list):
            item["author"] = ", ".join(str(a) for a in author if a)
        else:
            item["author"] = self._clean_text(author) if author else None
        
        # Clean other fields
        item["keywords"] = self._clean_text(adapter.get("keywords")) if adapter.get("keywords") else None
        
        # Drop items with insufficient content
        if not item["article_body"] or len(item["article_body"].strip()) < 50:
            raise DropItem(f"Insufficient article content in {adapter.get('url', 'unknown URL')}")

        return item
    
    def _clean_article_body(self, article_body):
        """Enhanced article body cleaning."""
        if not article_body:
            return ""
            
        # Remove HTML tags
        cleaned_body = remove_tags(str(article_body))

        # Replace HTML entities
        html_entities = {
            '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"',
            '&apos;': "'", '&nbsp;': ' ', '&#39;': "'", '&#x27;': "'"
        }
        for entity, char in html_entities.items():
            cleaned_body = cleaned_body.replace(entity, char)

        # Remove excessive whitespace and normalize
        cleaned_body = re.sub(r'\s+', ' ', cleaned_body).strip()
        
        return cleaned_body.strip()

    def _clean_text(self, text):
        """Enhanced generic text cleaner."""
        if not text:
            return ""
            
        # Convert to string if needed
        if isinstance(text, list):
            text = " ".join(str(t) for t in text if t)
        
        text = str(text)
        
        # Remove HTML tags
        text = remove_tags(text)
        
        # Replace HTML entities
        text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
