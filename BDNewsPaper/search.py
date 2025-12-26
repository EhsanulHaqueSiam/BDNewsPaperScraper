#!/usr/bin/env python3
"""
Full-Text Search Module
========================
Implements SQLite FTS5 full-text search for news articles.

Features:
    - Fast full-text search with relevance ranking
    - Highlighting of matched terms
    - Phrase search support
    - Auto-indexing of new articles

Usage:
    python search.py --query "bangladesh politics"
    python search.py --index    # Rebuild search index
    python search.py --stats    # Show index stats
"""

import argparse
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


DB_PATH = Path(__file__).parent.parent / "news_articles.db"


class FullTextSearch:
    """Full-text search using SQLite FTS5."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_fts_index(self) -> bool:
        """Create or rebuild the FTS5 index."""
        conn = self._get_conn()
        
        try:
            # Drop existing FTS table if exists
            conn.execute("DROP TABLE IF EXISTS articles_fts")
            
            # Create FTS5 virtual table
            conn.execute("""
                CREATE VIRTUAL TABLE articles_fts USING fts5(
                    headline,
                    article,
                    category,
                    paper_name,
                    content='articles',
                    content_rowid='id',
                    tokenize='porter unicode61'
                )
            """)
            
            # Populate FTS index
            conn.execute("""
                INSERT INTO articles_fts(rowid, headline, article, category, paper_name)
                SELECT id, headline, article, category, paper_name FROM articles
            """)
            
            conn.commit()
            
            # Get count
            count = conn.execute("SELECT COUNT(*) FROM articles_fts").fetchone()[0]
            print(f"✅ Created FTS5 index with {count:,} articles")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to create FTS index: {e}")
            conn.close()
            return False
    
    def ensure_index_exists(self) -> bool:
        """Ensure FTS index exists, create if not."""
        conn = self._get_conn()
        
        try:
            conn.execute("SELECT * FROM articles_fts LIMIT 1")
            conn.close()
            return True
        except sqlite3.OperationalError:
            conn.close()
            return self.create_fts_index()
    
    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        paper: str = None,
        category: str = None,
        highlight: bool = True
    ) -> Dict:
        """
        Search articles using FTS5.
        
        Args:
            query: Search query (supports phrases with "quotes")
            limit: Max results to return
            offset: Offset for pagination
            paper: Filter by paper name
            category: Filter by category
            highlight: Whether to highlight matched terms
        
        Returns:
            Dict with results, total count, and timing
        """
        if not self.ensure_index_exists():
            return {"error": "FTS index not available", "results": [], "total": 0}
        
        conn = self._get_conn()
        start_time = datetime.now()
        
        try:
            # Build FTS query
            # Escape special characters
            fts_query = re.sub(r'[^\w\s"*-]', '', query)
            
            # Build WHERE clause for filters
            filters = []
            params = []
            
            if paper:
                filters.append("a.paper_name = ?")
                params.append(paper)
            
            if category:
                filters.append("a.category = ?")
                params.append(category)
            
            filter_clause = " AND ".join(filters) if filters else "1=1"
            
            # Count total matches
            count_sql = f"""
                SELECT COUNT(*) FROM articles_fts f
                JOIN articles a ON f.rowid = a.id
                WHERE articles_fts MATCH ? AND {filter_clause}
            """
            total = conn.execute(count_sql, [fts_query] + params).fetchone()[0]
            
            # Get results with ranking
            if highlight:
                # Use highlight() for matched terms
                results_sql = f"""
                    SELECT 
                        a.id,
                        a.url,
                        a.paper_name,
                        highlight(articles_fts, 0, '<mark>', '</mark>') as headline,
                        snippet(articles_fts, 1, '<mark>', '</mark>', '...', 50) as snippet,
                        a.category,
                        a.publication_date,
                        bm25(articles_fts) as rank
                    FROM articles_fts f
                    JOIN articles a ON f.rowid = a.id
                    WHERE articles_fts MATCH ? AND {filter_clause}
                    ORDER BY bm25(articles_fts)
                    LIMIT ? OFFSET ?
                """
            else:
                results_sql = f"""
                    SELECT 
                        a.id,
                        a.url,
                        a.paper_name,
                        a.headline,
                        substr(a.article, 1, 200) as snippet,
                        a.category,
                        a.publication_date,
                        bm25(articles_fts) as rank
                    FROM articles_fts f
                    JOIN articles a ON f.rowid = a.id
                    WHERE articles_fts MATCH ? AND {filter_clause}
                    ORDER BY bm25(articles_fts)
                    LIMIT ? OFFSET ?
                """
            
            cursor = conn.execute(results_sql, [fts_query] + params + [limit, offset])
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "url": row["url"],
                    "paper_name": row["paper_name"],
                    "headline": row["headline"],
                    "snippet": row["snippet"],
                    "category": row["category"],
                    "publication_date": row["publication_date"],
                    "relevance": abs(row["rank"]) if row["rank"] else 0
                })
            
            duration = (datetime.now() - start_time).total_seconds()
            
            conn.close()
            
            return {
                "query": query,
                "results": results,
                "total": total,
                "limit": limit,
                "offset": offset,
                "pages": (total + limit - 1) // limit if limit > 0 else 0,
                "duration_ms": round(duration * 1000, 2)
            }
            
        except sqlite3.OperationalError as e:
            conn.close()
            # FTS query syntax error
            error_msg = str(e)
            if "fts5" in error_msg.lower():
                return {"error": f"Invalid search query: {query}", "results": [], "total": 0}
            raise
    
    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on prefix."""
        conn = self._get_conn()
        
        # Simple prefix matching on headlines
        cursor = conn.execute("""
            SELECT DISTINCT headline FROM articles
            WHERE headline LIKE ?
            ORDER BY publication_date DESC
            LIMIT ?
        """, (f"{prefix}%", limit))
        
        suggestions = [row["headline"] for row in cursor.fetchall()]
        conn.close()
        
        return suggestions
    
    def get_stats(self) -> Dict:
        """Get FTS index statistics."""
        conn = self._get_conn()
        
        try:
            fts_count = conn.execute("SELECT COUNT(*) FROM articles_fts").fetchone()[0]
            articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            
            conn.close()
            
            return {
                "fts_indexed": fts_count,
                "total_articles": articles_count,
                "index_coverage": f"{(fts_count/articles_count*100):.1f}%" if articles_count > 0 else "0%",
                "status": "ok" if fts_count == articles_count else "needs_rebuild"
            }
        except sqlite3.OperationalError:
            conn.close()
            return {
                "fts_indexed": 0,
                "total_articles": 0,
                "status": "not_created"
            }
    
    def sync_index(self) -> int:
        """Sync new articles to FTS index."""
        conn = self._get_conn()
        
        try:
            # Get max indexed rowid
            max_indexed = conn.execute("SELECT MAX(rowid) FROM articles_fts").fetchone()[0] or 0
            
            # Insert new articles
            conn.execute("""
                INSERT INTO articles_fts(rowid, headline, article, category, paper_name)
                SELECT id, headline, article, category, paper_name 
                FROM articles
                WHERE id > ?
            """, (max_indexed,))
            
            new_count = conn.total_changes
            conn.commit()
            conn.close()
            
            if new_count > 0:
                print(f"✅ Synced {new_count} new articles to FTS index")
            
            return new_count
            
        except sqlite3.OperationalError:
            conn.close()
            self.create_fts_index()
            return 0


# Global search instance
search_engine = FullTextSearch()


def main():
    parser = argparse.ArgumentParser(description="Full-text search for news articles")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--index", action="store_true", help="Rebuild search index")
    parser.add_argument("--sync", action="store_true", help="Sync new articles to index")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--limit", type=int, default=10, help="Max results")
    parser.add_argument("--paper", help="Filter by paper")
    
    args = parser.parse_args()
    
    fts = FullTextSearch()
    
    if args.index:
        fts.create_fts_index()
    elif args.sync:
        fts.sync_index()
    elif args.stats:
        stats = fts.get_stats()
        print(f"📊 FTS Index Statistics")
        print(f"   Indexed: {stats['fts_indexed']:,}")
        print(f"   Total: {stats['total_articles']:,}")
        print(f"   Coverage: {stats['index_coverage']}")
        print(f"   Status: {stats['status']}")
    elif args.query:
        results = fts.search(args.query, limit=args.limit, paper=args.paper)
        
        if "error" in results:
            print(f"❌ {results['error']}")
        else:
            print(f"🔍 Found {results['total']} results in {results['duration_ms']}ms\n")
            
            for i, r in enumerate(results['results'], 1):
                headline = r['headline'].replace('<mark>', '\033[1m').replace('</mark>', '\033[0m')
                print(f"{i}. {headline}")
                print(f"   {r['paper_name']} | {r['category']} | {r['publication_date']}")
                print(f"   {r['url']}\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
