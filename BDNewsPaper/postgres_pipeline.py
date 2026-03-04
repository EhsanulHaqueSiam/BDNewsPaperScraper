"""
PostgreSQL Database Pipeline
=============================
Pipeline for storing articles in PostgreSQL with full-text search support.

Requires: psycopg2-binary or asyncpg
"""

import logging
import os
import hashlib
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class PostgreSQLPipeline:
    """
    PostgreSQL database pipeline with full-text search.
    
    Features:
        - Connection pooling
        - Full-text search index
        - Automatic schema creation
        - Duplicate detection by URL and content hash
    
    Configuration (via settings or environment):
        - POSTGRES_HOST: Database host (default: localhost)
        - POSTGRES_PORT: Database port (default: 5432)
        - POSTGRES_DB: Database name (default: bdnews)
        - POSTGRES_USER: Username (default: postgres)
        - POSTGRES_PASSWORD: Password
    """
    
    def __init__(self, host: str, port: int, database: str, 
                 user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._pool = None
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            host=crawler.settings.get('POSTGRES_HOST', os.getenv('POSTGRES_HOST', 'localhost')),
            port=crawler.settings.getint('POSTGRES_PORT', int(os.getenv('POSTGRES_PORT', 5432))),
            database=crawler.settings.get('POSTGRES_DB', os.getenv('POSTGRES_DB', 'bdnews')),
            user=crawler.settings.get('POSTGRES_USER', os.getenv('POSTGRES_USER', 'postgres')),
            password=crawler.settings.get('POSTGRES_PASSWORD', os.getenv('POSTGRES_PASSWORD', '')),
        )
    
    def open_spider(self, spider):
        """Initialize database connection and schema."""
        import psycopg2
        from psycopg2 import pool
        
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            
            self._create_schema()
            spider.logger.info(f"PostgreSQL connected: {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            spider.logger.error(f"PostgreSQL connection failed: {e}")
            raise
    
    def close_spider(self, spider):
        """Close connection pool."""
        if self._pool:
            self._pool.closeall()
            spider.logger.info("PostgreSQL connection closed")
    
    @contextmanager
    def _get_connection(self):
        """Get connection from pool."""
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)
    
    def _create_schema(self):
        """Create database schema with full-text search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    paper_name TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    article TEXT NOT NULL,
                    sub_title TEXT,
                    category TEXT,
                    author TEXT,
                    publication_date TIMESTAMPTZ,
                    modification_date TIMESTAMPTZ,
                    image_url TEXT,
                    keywords TEXT,
                    source_language TEXT,
                    detected_language TEXT,
                    word_count INTEGER,
                    content_hash TEXT,
                    scraped_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    -- Full-text search vector
                    search_vector TSVECTOR
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_paper ON articles(paper_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(publication_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_hash ON articles(content_hash)")
            
            # Create GIN index for full-text search
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_search 
                ON articles USING GIN(search_vector)
            """)
            
            # Create trigger for automatic search vector update
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_search_vector() 
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search_vector := 
                        setweight(to_tsvector('english', COALESCE(NEW.headline, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(NEW.sub_title, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(NEW.article, '')), 'C');
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            cursor.execute("""
                DROP TRIGGER IF EXISTS trigger_update_search_vector ON articles;
                CREATE TRIGGER trigger_update_search_vector
                BEFORE INSERT OR UPDATE ON articles
                FOR EACH ROW EXECUTE FUNCTION update_search_vector();
            """)
            
            conn.commit()
            logger.info("PostgreSQL schema created with FTS")
    
    def process_item(self, item, spider):
        """Store article in PostgreSQL."""
        adapter = ItemAdapter(item)
        url = adapter.get('url')
        
        if not url:
            raise DropItem("Missing URL")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate
            cursor.execute("SELECT id FROM articles WHERE url = %s", (url,))
            if cursor.fetchone():
                raise DropItem(f"Duplicate URL: {url}")
            
            # Check content hash
            content_hash = adapter.get('content_hash')
            if content_hash:
                cursor.execute("SELECT id FROM articles WHERE content_hash = %s", (content_hash,))
                if cursor.fetchone():
                    raise DropItem(f"Duplicate content: {url}")
            
            # Parse publication date
            pub_date = None
            pub_date_str = adapter.get('publication_date')
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            # Insert article
            cursor.execute("""
                INSERT INTO articles (
                    url, paper_name, headline, article, sub_title, category,
                    author, publication_date, modification_date, image_url,
                    keywords, source_language, detected_language, word_count, content_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                url,
                adapter.get('paper_name', spider.name),
                adapter.get('headline', ''),
                adapter.get('article_body', ''),
                adapter.get('sub_title'),
                adapter.get('category'),
                adapter.get('author'),
                pub_date,
                None,  # modification_date
                adapter.get('image_url'),
                adapter.get('keywords'),
                adapter.get('source_language'),
                adapter.get('detected_language'),
                adapter.get('word_count'),
                content_hash,
            ))
            
            article_id = cursor.fetchone()[0]
            spider.logger.debug(f"Saved article {article_id}: {adapter.get('headline', '')[:50]}...")
        
        return item


def full_text_search(query: str, limit: int = 20, offset: int = 0,
                     host: str = 'localhost', database: str = 'bdnews',
                     user: str = 'postgres', password: str = ''):
    """
    Perform full-text search on articles.
    
    Args:
        query: Search query string
        limit: Maximum results
        offset: Offset for pagination
    
    Returns:
        List of matching articles with rank
    """
    import psycopg2
    
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
    )
    cursor = conn.cursor()
    
    # Parse query into tsquery
    cursor.execute("""
        SELECT 
            id, url, paper_name, headline, 
            ts_rank(search_vector, plainto_tsquery('english', %s)) as rank
        FROM articles
        WHERE search_vector @@ plainto_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT %s OFFSET %s
    """, (query, query, limit, offset))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'url': row[1],
            'paper_name': row[2],
            'headline': row[3],
            'rank': float(row[4]),
        })
    
    conn.close()
    return results
