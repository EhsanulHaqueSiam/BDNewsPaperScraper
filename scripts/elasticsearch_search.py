#!/usr/bin/env python3
"""
Elasticsearch Integration
==========================
Better full-text search with Elasticsearch.

Features:
    - Full-text search with relevance
    - Fuzzy matching
    - Faceted search
    - Autocomplete suggestions

Setup:
    docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0
    pip install elasticsearch

Usage:
    python elasticsearch_search.py --index            # Index articles
    python elasticsearch_search.py --search "query"   # Search
    python elasticsearch_search.py --suggest "qu"     # Autocomplete
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"

# Try to import Elasticsearch
try:
    from elasticsearch import Elasticsearch, helpers
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False

ES_HOST = "http://localhost:9200"
ES_INDEX = "bdnews_articles"


class ElasticsearchManager:
    """Manage Elasticsearch integration."""
    
    def __init__(self, host: str = ES_HOST):
        self.host = host
        self.index = ES_INDEX
        self.client = None
        
        if ES_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """Connect to Elasticsearch."""
        try:
            self.client = Elasticsearch(
                self.host,
                verify_certs=False,
                request_timeout=30
            )
            
            if self.client.ping():
                print(f"✅ Connected to Elasticsearch: {self.host}")
            else:
                print("❌ Elasticsearch not responding")
                self.client = None
        except Exception as e:
            print(f"❌ Elasticsearch connection failed: {e}")
            self.client = None
    
    @property
    def is_available(self) -> bool:
        return self.client is not None
    
    def create_index(self):
        """Create index with mapping."""
        if not self.is_available:
            return False
        
        # Check if exists
        if self.client.indices.exists(index=self.index):
            print(f"ℹ️ Index {self.index} already exists")
            return True
        
        mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "bangla_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "headline": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "article_body": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "paper_name": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "author": {"type": "keyword"},
                    "source_language": {"type": "keyword"},
                    "url": {"type": "keyword"},
                    "publication_date": {"type": "date", "ignore_malformed": True},
                    "scraped_at": {"type": "date"},
                    "word_count": {"type": "integer"}
                }
            }
        }
        
        self.client.indices.create(index=self.index, body=mapping)
        print(f"✅ Created index: {self.index}")
        return True
    
    def index_articles(self, batch_size: int = 500) -> int:
        """Index all articles from database."""
        if not self.is_available:
            print("❌ Elasticsearch not available")
            return 0
        
        if not DB_PATH.exists():
            print("❌ Database not found")
            return 0
        
        self.create_index()
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT id, url, headline, article_body, paper_name, category,
                   author, publication_date, source_language, word_count, scraped_at
            FROM articles
        """)
        
        def generate_actions():
            for row in cursor:
                doc = {
                    "_index": self.index,
                    "_id": row["id"],
                    "_source": {
                        "headline": row["headline"],
                        "article_body": row["article_body"] or "",
                        "paper_name": row["paper_name"],
                        "category": row["category"],
                        "author": row["author"],
                        "url": row["url"],
                        "source_language": row["source_language"],
                        "word_count": row["word_count"],
                        "publication_date": row["publication_date"],
                        "scraped_at": row["scraped_at"]
                    }
                }
                yield doc
        
        print("📤 Indexing articles...")
        success, failed = helpers.bulk(
            self.client,
            generate_actions(),
            chunk_size=batch_size,
            raise_on_error=False
        )
        
        conn.close()
        
        print(f"✅ Indexed {success} articles ({failed} failed)")
        return success
    
    def search(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        paper: str = None,
        category: str = None,
        highlight: bool = True
    ) -> Dict:
        """Search articles."""
        if not self.is_available:
            return {"error": "Elasticsearch not available"}
        
        # Build query
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["headline^3", "article_body"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        ]
        
        filters = []
        if paper:
            filters.append({"term": {"paper_name": paper}})
        if category:
            filters.append({"term": {"category": category}})
        
        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filters
                }
            },
            "from": (page - 1) * per_page,
            "size": per_page,
            "sort": [
                {"_score": "desc"},
                {"scraped_at": "desc"}
            ]
        }
        
        if highlight:
            body["highlight"] = {
                "fields": {
                    "headline": {"number_of_fragments": 0},
                    "article_body": {"number_of_fragments": 3, "fragment_size": 150}
                }
            }
        
        result = self.client.search(index=self.index, body=body)
        
        hits = []
        for hit in result["hits"]["hits"]:
            article = hit["_source"]
            article["id"] = hit["_id"]
            article["score"] = hit["_score"]
            
            if "highlight" in hit:
                article["highlight"] = hit["highlight"]
            
            hits.append(article)
        
        return {
            "total": result["hits"]["total"]["value"],
            "page": page,
            "per_page": per_page,
            "results": hits,
            "took_ms": result["took"]
        }
    
    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions."""
        if not self.is_available:
            return []
        
        body = {
            "suggest": {
                "headline-suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "headline.suggest",
                        "size": limit,
                        "skip_duplicates": True
                    }
                }
            }
        }
        
        result = self.client.search(index=self.index, body=body)
        
        suggestions = []
        for option in result["suggest"]["headline-suggest"][0]["options"]:
            suggestions.append(option["text"])
        
        return suggestions
    
    def get_facets(self) -> Dict:
        """Get facets for filtering."""
        if not self.is_available:
            return {}
        
        body = {
            "size": 0,
            "aggs": {
                "papers": {"terms": {"field": "paper_name", "size": 50}},
                "categories": {"terms": {"field": "category", "size": 50}},
                "languages": {"terms": {"field": "source_language", "size": 10}}
            }
        }
        
        result = self.client.search(index=self.index, body=body)
        
        return {
            "papers": [{"name": b["key"], "count": b["doc_count"]} for b in result["aggregations"]["papers"]["buckets"]],
            "categories": [{"name": b["key"], "count": b["doc_count"]} for b in result["aggregations"]["categories"]["buckets"]],
            "languages": [{"name": b["key"], "count": b["doc_count"]} for b in result["aggregations"]["languages"]["buckets"]]
        }
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        if not self.is_available:
            return {"available": False}
        
        try:
            stats = self.client.indices.stats(index=self.index)
            
            return {
                "available": True,
                "documents": stats["indices"][self.index]["primaries"]["docs"]["count"],
                "size_bytes": stats["indices"][self.index]["primaries"]["store"]["size_in_bytes"]
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Elasticsearch integration")
    parser.add_argument("--index", action="store_true", help="Index articles")
    parser.add_argument("--search", help="Search query")
    parser.add_argument("--suggest", help="Autocomplete prefix")
    parser.add_argument("--facets", action="store_true", help="Get facets")
    parser.add_argument("--stats", action="store_true", help="Get stats")
    parser.add_argument("--page", type=int, default=1, help="Page number")
    parser.add_argument("--paper", help="Filter by paper")
    parser.add_argument("--category", help="Filter by category")
    
    args = parser.parse_args()
    
    if not ES_AVAILABLE:
        print("❌ Install: pip install elasticsearch")
        return
    
    es = ElasticsearchManager()
    
    if args.index:
        es.index_articles()
    
    elif args.search:
        results = es.search(args.search, page=args.page, paper=args.paper, category=args.category)
        
        print(f"\n🔍 Found {results.get('total', 0)} results in {results.get('took_ms', 0)}ms\n")
        
        for r in results.get("results", [])[:10]:
            print(f"  [{r.get('score', 0):.1f}] {r['headline'][:70]}...")
            print(f"       📰 {r['paper_name']} | 📁 {r.get('category', 'N/A')}")
            
            if "highlight" in r and "article_body" in r["highlight"]:
                snippet = r["highlight"]["article_body"][0][:100]
                print(f"       ...{snippet}...")
            print()
    
    elif args.suggest:
        suggestions = es.suggest(args.suggest)
        print(f"\n💡 Suggestions for '{args.suggest}':\n")
        for s in suggestions:
            print(f"  • {s}")
    
    elif args.facets:
        facets = es.get_facets()
        print("\n📊 Facets:\n")
        print(json.dumps(facets, indent=2))
    
    elif args.stats:
        stats = es.get_stats()
        print(f"\n📊 Elasticsearch Stats:\n")
        print(f"   Available: {stats.get('available')}")
        print(f"   Documents: {stats.get('documents', 0):,}")
        print(f"   Size: {stats.get('size_bytes', 0) / 1024 / 1024:.1f} MB")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
