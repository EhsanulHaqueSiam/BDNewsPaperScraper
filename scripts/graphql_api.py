#!/usr/bin/env python3
"""
GraphQL API
============
Alternative GraphQL API for querying news articles.

Features:
    - Flexible queries
    - Nested data fetching
    - Pagination
    - Filtering & search

Usage:
    python graphql_api.py                    # Start server
    python graphql_api.py --port 8001        # Custom port

Dependencies:
    pip install strawberry-graphql[fastapi] uvicorn
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"


# GraphQL Types
@strawberry.type
class Article:
    id: int
    url: str
    headline: str
    paper_name: str
    article_body: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[str] = None
    source_language: Optional[str] = None
    word_count: Optional[int] = None
    scraped_at: Optional[str] = None
    
    @strawberry.field
    def read_time(self) -> int:
        """Estimated reading time in minutes."""
        if self.word_count:
            return max(1, round(self.word_count / 200))
        return 1


@strawberry.type
class ArticleConnection:
    items: List[Article]
    total: int
    page: int
    per_page: int
    has_next: bool


@strawberry.type
class NewspaperStats:
    paper_name: str
    article_count: int
    latest_article: Optional[str] = None


@strawberry.type
class CategoryStats:
    category: str
    article_count: int


@strawberry.type
class SearchResult:
    article: Article
    relevance: float


@strawberry.type
class Stats:
    total_articles: int
    total_papers: int
    total_categories: int
    articles_today: int
    articles_week: int


# Database helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_article(row) -> Article:
    return Article(
        id=row["id"],
        url=row["url"],
        headline=row["headline"],
        paper_name=row["paper_name"],
        article_body=row.get("article_body"),
        category=row.get("category"),
        author=row.get("author"),
        publication_date=row.get("publication_date"),
        source_language=row.get("source_language"),
        word_count=row.get("word_count"),
        scraped_at=row.get("scraped_at")
    )


# GraphQL Query
@strawberry.type
class Query:
    
    @strawberry.field
    def articles(
        self,
        page: int = 1,
        per_page: int = 20,
        paper: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ArticleConnection:
        """Get paginated articles with optional filters."""
        conn = get_db()
        
        conditions = ["1=1"]
        params = []
        
        if paper:
            conditions.append("paper_name = ?")
            params.append(paper)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if language:
            conditions.append("source_language = ?")
            params.append(language)
        if start_date:
            conditions.append("scraped_at >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("scraped_at <= ?")
            params.append(end_date)
        
        where = " AND ".join(conditions)
        
        # Count total
        total = conn.execute(f"SELECT COUNT(*) FROM articles WHERE {where}", params).fetchone()[0]
        
        # Get page
        offset = (page - 1) * per_page
        cursor = conn.execute(f"""
            SELECT * FROM articles WHERE {where}
            ORDER BY scraped_at DESC LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        
        items = [row_to_article(row) for row in cursor.fetchall()]
        conn.close()
        
        return ArticleConnection(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            has_next=(page * per_page) < total
        )
    
    @strawberry.field
    def article(self, id: int) -> Optional[Article]:
        """Get article by ID."""
        conn = get_db()
        cursor = conn.execute("SELECT * FROM articles WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        
        return row_to_article(row) if row else None
    
    @strawberry.field
    def search(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20
    ) -> List[SearchResult]:
        """Search articles by headline."""
        conn = get_db()
        
        offset = (page - 1) * per_page
        cursor = conn.execute("""
            SELECT *, 
                   (CASE WHEN headline LIKE ? THEN 2.0 ELSE 1.0 END) as relevance
            FROM articles
            WHERE headline LIKE ? OR article_body LIKE ?
            ORDER BY relevance DESC, scraped_at DESC
            LIMIT ? OFFSET ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", per_page, offset))
        
        results = [
            SearchResult(article=row_to_article(row), relevance=row["relevance"])
            for row in cursor.fetchall()
        ]
        conn.close()
        
        return results
    
    @strawberry.field
    def newspapers(self) -> List[NewspaperStats]:
        """Get all newspapers with stats."""
        conn = get_db()
        cursor = conn.execute("""
            SELECT paper_name, COUNT(*) as count, MAX(scraped_at) as latest
            FROM articles GROUP BY paper_name ORDER BY count DESC
        """)
        
        results = [
            NewspaperStats(
                paper_name=row["paper_name"],
                article_count=row["count"],
                latest_article=row["latest"]
            )
            for row in cursor.fetchall()
        ]
        conn.close()
        
        return results
    
    @strawberry.field
    def categories(self) -> List[CategoryStats]:
        """Get all categories with counts."""
        conn = get_db()
        cursor = conn.execute("""
            SELECT category, COUNT(*) as count
            FROM articles WHERE category IS NOT NULL
            GROUP BY category ORDER BY count DESC
        """)
        
        results = [
            CategoryStats(category=row["category"], article_count=row["count"])
            for row in cursor.fetchall()
        ]
        conn.close()
        
        return results
    
    @strawberry.field
    def stats(self) -> Stats:
        """Get overall statistics."""
        conn = get_db()
        
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        papers = conn.execute("SELECT COUNT(DISTINCT paper_name) FROM articles").fetchone()[0]
        categories = conn.execute("SELECT COUNT(DISTINCT category) FROM articles WHERE category IS NOT NULL").fetchone()[0]
        
        today = datetime.now().date().isoformat()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        today_count = conn.execute("SELECT COUNT(*) FROM articles WHERE scraped_at >= ?", (today,)).fetchone()[0]
        week_count = conn.execute("SELECT COUNT(*) FROM articles WHERE scraped_at >= ?", (week_ago,)).fetchone()[0]
        
        conn.close()
        
        return Stats(
            total_articles=total,
            total_papers=papers,
            total_categories=categories,
            articles_today=today_count,
            articles_week=week_count
        )


# Create schema
schema = strawberry.Schema(query=Query)

# FastAPI app
app = FastAPI(
    title="BD News GraphQL API",
    description="GraphQL API for Bangladeshi news articles",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GraphQL route
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
async def root():
    return {
        "message": "BD News GraphQL API",
        "graphql_endpoint": "/graphql",
        "graphql_playground": "/graphql"
    }


def main():
    parser = argparse.ArgumentParser(description="GraphQL API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=8001, help="Port")
    
    args = parser.parse_args()
    
    import uvicorn
    print(f"🚀 Starting GraphQL API at http://{args.host}:{args.port}/graphql")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
