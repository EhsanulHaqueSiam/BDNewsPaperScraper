"""
SharedSQLitePipeline Unit Tests
================================
Tests for the thread-safe SQLite database pipeline.
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from scrapy.exceptions import DropItem

from BDNewsPaper.items import NewsArticleItem
from BDNewsPaper.pipelines import SharedSQLitePipeline


class TestSharedSQLitePipeline:
    """Tests for SharedSQLitePipeline."""

    def _make_pipeline(self, tmp_path):
        """Helper to create a pipeline with a temp DB path."""
        db_path = str(tmp_path / "test.db")
        return SharedSQLitePipeline(db_path=db_path)

    def _make_item(self, url="https://example.com/test-article", **overrides):
        """Helper to create a valid NewsArticleItem for insertion."""
        defaults = dict(
            headline="Test Headline with Sufficient Length",
            article_body="This is a test article body with enough content to pass validation. " * 10,
            url=url,
            paper_name="Test Paper",
            publication_date="2024-12-25T10:00:00+06:00",
            category="National",
            author="Test Author",
            sub_title="A brief subtitle",
            image_url="https://example.com/image.jpg",
            keywords="test, article, news",
            source_language="English",
        )
        defaults.update(overrides)
        return NewsArticleItem(**defaults)

    # ------------------------------------------------------------------
    # Schema creation
    # ------------------------------------------------------------------

    def test_open_spider_creates_schema(self, tmp_path, mock_spider):
        """open_spider should create the articles table with all expected columns."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(articles);")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected_columns = {
            "id",
            "url",
            "paper_name",
            "headline",
            "article",
            "sub_title",
            "category",
            "author",
            "publication_date",
            "modification_date",
            "image_url",
            "keywords",
            "source_language",
            "word_count",
            "content_hash",
            "scraped_at",
        }
        assert columns == expected_columns

    # ------------------------------------------------------------------
    # Basic insertion
    # ------------------------------------------------------------------

    def test_process_item_inserts_article(self, tmp_path, mock_spider):
        """process_item should insert a row into the articles table."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        item = self._make_item()
        result = pipeline.process_item(item, mock_spider)

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles;")
        count = cursor.fetchone()[0]
        conn.close()

        assert result is item
        assert count == 1

    # ------------------------------------------------------------------
    # All fields stored correctly
    # ------------------------------------------------------------------

    def test_process_item_stores_all_fields(self, tmp_path, mock_spider):
        """process_item should persist every field to the correct column."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        item = self._make_item()
        pipeline.process_item(item, mock_spider)

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE url = ?", (item["url"],))
        row = cursor.fetchone()
        conn.close()

        assert row["url"] == item["url"]
        assert row["paper_name"] == item["paper_name"]
        assert row["headline"] == item["headline"]
        assert row["article"] == item["article_body"]
        assert row["sub_title"] == item.get("sub_title")
        assert row["category"] == item.get("category")
        assert row["author"] == item.get("author")
        assert row["publication_date"] == item.get("publication_date")
        assert row["image_url"] == item.get("image_url")
        assert row["keywords"] == item.get("keywords")
        assert row["source_language"] == item.get("source_language")
        assert row["word_count"] == item.get("word_count")
        assert row["content_hash"] == item.get("content_hash")

    # ------------------------------------------------------------------
    # Duplicate URL detection
    # ------------------------------------------------------------------

    def test_duplicate_url_raises_drop_item(self, tmp_path, mock_spider):
        """Inserting the same URL twice should raise DropItem."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        item1 = self._make_item(url="https://example.com/dup-url")
        pipeline.process_item(item1, mock_spider)

        item2 = self._make_item(url="https://example.com/dup-url")
        with pytest.raises(DropItem, match="Duplicate URL"):
            pipeline.process_item(item2, mock_spider)

    # ------------------------------------------------------------------
    # Duplicate content_hash detection
    # ------------------------------------------------------------------

    def test_duplicate_content_hash_raises_drop_item(self, tmp_path, mock_spider):
        """Two items with different URLs but the same content_hash should raise DropItem."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        shared_body = "Identical article body used for hashing. " * 10
        item1 = self._make_item(
            url="https://example.com/article-1",
            headline="Same Headline",
            article_body=shared_body,
        )
        pipeline.process_item(item1, mock_spider)

        # Build a second item that ends up with the same content_hash
        item2 = self._make_item(
            url="https://example.com/article-2",
            headline="Same Headline",
            article_body=shared_body,
        )
        # Verify precondition: hashes are truly equal
        assert item1["content_hash"] == item2["content_hash"]

        with pytest.raises(DropItem, match="Duplicate content"):
            pipeline.process_item(item2, mock_spider)

    # ------------------------------------------------------------------
    # Missing URL
    # ------------------------------------------------------------------

    def test_missing_url_raises_drop_item(self, tmp_path, mock_spider):
        """An item without a url field should raise DropItem."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        item = NewsArticleItem(
            headline="No URL Headline",
            article_body="Some body text. " * 10,
            paper_name="Test Paper",
        )

        with pytest.raises(DropItem, match="Missing URL"):
            pipeline.process_item(item, mock_spider)

    # ------------------------------------------------------------------
    # close_spider logging
    # ------------------------------------------------------------------

    def test_close_spider_logs_count(self, tmp_path, mock_spider):
        """close_spider should log the number of articles for the spider."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        # Insert two articles with distinct bodies so content_hash differs.
        # paper_name must match mock_spider.name because close_spider
        # queries WHERE paper_name = spider.name.
        pipeline.process_item(
            self._make_item(url="https://example.com/a1", headline="First Article",
                            article_body="First article body content. " * 10,
                            paper_name=mock_spider.name),
            mock_spider,
        )
        pipeline.process_item(
            self._make_item(url="https://example.com/a2", headline="Second Article",
                            article_body="Second article body content. " * 10,
                            paper_name=mock_spider.name),
            mock_spider,
        )

        pipeline.close_spider(mock_spider)

        # The logger should have been called with info containing the count
        log_messages = [
            str(call) for call in mock_spider.logger.info.call_args_list
        ]
        matched = any("2" in msg and "articles" in msg for msg in log_messages)
        assert matched, f"Expected log with '2' and 'articles', got: {log_messages}"

    # ------------------------------------------------------------------
    # WAL mode
    # ------------------------------------------------------------------

    def test_wal_mode_enabled(self, tmp_path, mock_spider):
        """The pipeline connection should use WAL journal mode."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        conn = pipeline._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]

        assert mode == "wal"

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    def test_indexes_created(self, tmp_path, mock_spider):
        """open_spider should create all expected indexes on the articles table."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='articles';"
        )
        index_names = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_indexes = {
            "idx_url",
            "idx_paper_name",
            "idx_publication_date",
            "idx_category",
            "idx_content_hash",
        }
        assert expected_indexes.issubset(index_names)

    # ------------------------------------------------------------------
    # Thread safety with concurrent inserts
    # ------------------------------------------------------------------

    def test_thread_safety_concurrent_inserts(self, tmp_path, mock_spider):
        """Concurrent inserts from multiple threads should all succeed without errors."""
        pipeline = self._make_pipeline(tmp_path)
        pipeline.open_spider(mock_spider)

        num_items = 20

        def insert_item(idx):
            item = self._make_item(
                url=f"https://example.com/thread-{idx}",
                headline=f"Thread Article {idx}",
                article_body=f"Unique body content for thread article number {idx}. " * 10,
            )
            pipeline.process_item(item, mock_spider)
            return idx

        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(insert_item, i): i for i in range(num_items)
            }
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == num_items

        # Verify all rows are actually in the database
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles;")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == num_items
