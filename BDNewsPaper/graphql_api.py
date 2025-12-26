"""
GraphQL API
===========
GraphQL interface for querying news articles using Strawberry.

Run with: uvicorn BDNewsPaper.graphql_api:app --reload
"""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

try:
    import strawberry
    from strawberry.fastapi import GraphQLRouter
    STRAWBERRY_AVAILABLE = True
except ImportError:
    STRAWBERRY_AVAILABLE = False

from fastapi import FastAPI


DATABASE_PATH = os.getenv('DATABASE_PATH', 'news_articles.db')


@contextmanager
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


if STRAWBERRY_AVAILABLE:
    @strawberry.type
    class Article:
        """GraphQL Article type."""
        id: int
        url: str
        paper_name: str
        headline: str
        article: Optional[str] = None
        sub_title: Optional[str] = None
        category: Optional[str] = None
        author: Optional[str] = None
        publication_date: Optional[str] = None
        keywords: Optional[str] = None
        word_count: Optional[int] = None
        scraped_at: Optional[str] = None

    @strawberry.type
    class PaperStats:
        """Newspaper statistics."""
        paper_name: str
        article_count: int
        latest_article: Optional[str] = None

    @strawberry.type
    class SearchResult:
        """Search result with relevance."""
        article: Article
        relevance: float

    @strawberry.type
    class Query:
        @strawberry.field
        def article(self, id: int) -> Optional[Article]:
            """Get article by ID."""
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM articles WHERE id = ?", (id,))
                row = cursor.fetchone()
                if row:
                    return Article(
                        id=row['id'],
                        url=row['url'],
                        paper_name=row['paper_name'],
                        headline=row['headline'],
                        article=row['article'],
                        sub_title=row['sub_title'],
                        category=row['category'],
                        author=row['author'],
                        publication_date=row['publication_date'],
                        keywords=row['keywords'],
                        word_count=row['word_count'],
                        scraped_at=row['scraped_at'],
                    )
                return None

        @strawberry.field
        def articles(
            self,
            paper: Optional[str] = None,
            category: Optional[str] = None,
            limit: int = 20,
            offset: int = 0,
        ) -> List[Article]:
            """List articles with filtering."""
            with get_db() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if paper:
                    conditions.append("paper_name = ?")
                    params.append(paper)
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                
                where = " AND ".join(conditions) if conditions else "1=1"
                
                cursor.execute(f"""
                    SELECT * FROM articles 
                    WHERE {where}
                    ORDER BY publication_date DESC
                    LIMIT ? OFFSET ?
                """, params + [limit, offset])
                
                return [
                    Article(
                        id=row['id'],
                        url=row['url'],
                        paper_name=row['paper_name'],
                        headline=row['headline'],
                        article=row['article'],
                        sub_title=row['sub_title'],
                        category=row['category'],
                        author=row['author'],
                        publication_date=row['publication_date'],
                        keywords=row['keywords'],
                        word_count=row['word_count'],
                        scraped_at=row['scraped_at'],
                    )
                    for row in cursor.fetchall()
                ]

        @strawberry.field
        def search(self, query: str, limit: int = 20) -> List[Article]:
            """Search articles by headline/content."""
            with get_db() as conn:
                cursor = conn.cursor()
                search_term = f"%{query}%"
                
                cursor.execute("""
                    SELECT * FROM articles 
                    WHERE headline LIKE ? OR article LIKE ?
                    ORDER BY publication_date DESC
                    LIMIT ?
                """, (search_term, search_term, limit))
                
                return [
                    Article(
                        id=row['id'],
                        url=row['url'],
                        paper_name=row['paper_name'],
                        headline=row['headline'],
                        article=row['article'],
                        sub_title=row['sub_title'],
                        category=row['category'],
                        author=row['author'],
                        publication_date=row['publication_date'],
                        keywords=row['keywords'],
                        word_count=row['word_count'],
                        scraped_at=row['scraped_at'],
                    )
                    for row in cursor.fetchall()
                ]

        @strawberry.field
        def papers(self) -> List[PaperStats]:
            """Get all newspapers with stats."""
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT paper_name, COUNT(*) as count, 
                           MAX(publication_date) as latest
                    FROM articles 
                    GROUP BY paper_name 
                    ORDER BY count DESC
                """)
                
                return [
                    PaperStats(
                        paper_name=row['paper_name'],
                        article_count=row['count'],
                        latest_article=row['latest'],
                    )
                    for row in cursor.fetchall()
                ]

        @strawberry.field
        def categories(self) -> List[str]:
            """Get all categories."""
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT category FROM articles 
                    WHERE category IS NOT NULL 
                    ORDER BY category
                """)
                return [row['category'] for row in cursor.fetchall()]

        @strawberry.field
        def stats(self) -> "Stats":
            """Get database statistics."""
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM articles")
                total = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM articles 
                    WHERE scraped_at >= datetime('now', '-24 hours')
                """)
                recent = cursor.fetchone()[0]
                
                return Stats(total_articles=total, articles_last_24h=recent)

    @strawberry.type
    class Stats:
        total_articles: int
        articles_last_24h: int

    # Create schema
    schema = strawberry.Schema(query=Query)
    graphql_app = GraphQLRouter(schema)

# Create FastAPI app
app = FastAPI(title="BDNewsPaper GraphQL API")

if STRAWBERRY_AVAILABLE:
    app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
async def root():
    if STRAWBERRY_AVAILABLE:
        return {"message": "GraphQL API available at /graphql"}
    return {"error": "strawberry-graphql not installed. Run: pip install strawberry-graphql[fastapi]"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
