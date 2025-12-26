"""
BDNewsPaper REST API
====================
FastAPI-based REST API for accessing scraped news articles.

Run with: uvicorn BDNewsPaper.api:app --reload
"""

import os
import sqlite3
from datetime import datetime, date
from typing import List, Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ==============================================================================
# Configuration
# ==============================================================================

DATABASE_PATH = os.getenv('DATABASE_PATH', 'news_articles.db')

app = FastAPI(
    title="BDNewsPaper API",
    description="REST API for accessing scraped Bangladeshi newspaper articles",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Pydantic Models
# ==============================================================================

class ArticleBase(BaseModel):
    """Base article model."""
    url: str
    paper_name: str
    headline: str
    article: Optional[str] = Field(None, alias='article_body')
    sub_title: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[str] = None
    keywords: Optional[str] = None
    word_count: Optional[int] = None


class ArticleSummary(BaseModel):
    """Summary model for list views."""
    id: int
    url: str
    paper_name: str
    headline: str
    category: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[str] = None


class ArticleDetail(ArticleBase):
    """Detailed article model."""
    id: int
    modification_date: Optional[str] = None
    image_url: Optional[str] = None
    source_language: Optional[str] = None
    content_hash: Optional[str] = None
    scraped_at: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[ArticleSummary]
    total: int
    page: int
    per_page: int
    pages: int


class StatsResponse(BaseModel):
    """Statistics response."""
    total_articles: int
    papers: dict
    categories: dict
    date_range: dict
    recent_articles: int


# ==============================================================================
# Database Helpers
# ==============================================================================

@contextmanager
def get_db():
    """Get database connection as context manager."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row) -> dict:
    """Convert sqlite row to dictionary."""
    return dict(row) if row else {}


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/", tags=["Health"])
async def root():
    """API health check."""
    return {
        "status": "ok",
        "message": "BDNewsPaper API is running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            count = cursor.fetchone()[0]
        return {
            "status": "healthy",
            "database": "connected",
            "articles_count": count,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@app.get("/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_stats():
    """Get database statistics."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total articles
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        
        # Articles by paper
        cursor.execute("""
            SELECT paper_name, COUNT(*) as count 
            FROM articles 
            GROUP BY paper_name 
            ORDER BY count DESC
        """)
        papers = {row['paper_name']: row['count'] for row in cursor.fetchall()}
        
        # Articles by category
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM articles 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC 
            LIMIT 20
        """)
        categories = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Date range
        cursor.execute("""
            SELECT MIN(publication_date) as earliest, 
                   MAX(publication_date) as latest 
            FROM articles 
            WHERE publication_date IS NOT NULL
        """)
        date_row = cursor.fetchone()
        
        # Recent articles (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE scraped_at >= datetime('now', '-1 day')
        """)
        recent = cursor.fetchone()[0]
        
        return {
            "total_articles": total,
            "papers": papers,
            "categories": categories,
            "date_range": {
                "earliest": date_row['earliest'],
                "latest": date_row['latest'],
            },
            "recent_articles": recent,
        }


@app.get("/articles", response_model=PaginatedResponse, tags=["Articles"])
async def list_articles(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    paper: Optional[str] = Query(None, description="Filter by paper name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    author: Optional[str] = Query(None, description="Filter by author"),
    search: Optional[str] = Query(None, description="Search in headline"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    sort: str = Query("desc", description="Sort order (asc/desc)"),
):
    """List articles with pagination and filtering."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build query
        conditions = []
        params = []
        
        if paper:
            conditions.append("paper_name = ?")
            params.append(paper)
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if author:
            conditions.append("author LIKE ?")
            params.append(f"%{author}%")
        
        if search:
            conditions.append("headline LIKE ?")
            params.append(f"%{search}%")
        
        if start_date:
            conditions.append("publication_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("publication_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order = "DESC" if sort.lower() == "desc" else "ASC"
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM articles WHERE {where_clause}", params)
        total = cursor.fetchone()[0]
        
        # Get paginated results
        offset = (page - 1) * per_page
        cursor.execute(f"""
            SELECT id, url, paper_name, headline, category, author, publication_date
            FROM articles 
            WHERE {where_clause}
            ORDER BY publication_date {order}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        
        items = [ArticleSummary(**row_to_dict(row)) for row in cursor.fetchall()]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }


@app.get("/articles/{article_id}", response_model=ArticleDetail, tags=["Articles"])
async def get_article(article_id: int):
    """Get article by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return ArticleDetail(**row_to_dict(row))


@app.get("/articles/url/", response_model=ArticleDetail, tags=["Articles"])
async def get_article_by_url(url: str = Query(..., description="Article URL")):
    """Get article by URL."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE url = ?", (url,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return ArticleDetail(**row_to_dict(row))


@app.get("/papers", tags=["Papers"])
async def list_papers():
    """List all newspapers with article counts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT paper_name, COUNT(*) as count,
                   MAX(publication_date) as latest_article
            FROM articles 
            GROUP BY paper_name 
            ORDER BY count DESC
        """)
        return [row_to_dict(row) for row in cursor.fetchall()]


@app.get("/categories", tags=["Categories"])
async def list_categories():
    """List all categories with article counts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM articles 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC
        """)
        return [row_to_dict(row) for row in cursor.fetchall()]


@app.get("/search", response_model=PaginatedResponse, tags=["Search"])
async def search_articles(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Full-text search in articles."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        search_term = f"%{q}%"
        
        # Get total count
        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE headline LIKE ? OR article LIKE ?
        """, (search_term, search_term))
        total = cursor.fetchone()[0]
        
        # Get results
        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT id, url, paper_name, headline, category, author, publication_date
            FROM articles 
            WHERE headline LIKE ? OR article LIKE ?
            ORDER BY publication_date DESC
            LIMIT ? OFFSET ?
        """, (search_term, search_term, per_page, offset))
        
        items = [ArticleSummary(**row_to_dict(row)) for row in cursor.fetchall()]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
