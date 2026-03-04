#!/usr/bin/env python3
"""
Content Similarity & Duplicate Detection
==========================================
Find similar and duplicate articles using text similarity.

Features:
    - TF-IDF based similarity
    - Cosine similarity scoring
    - Fuzzy headline matching
    - Duplicate clustering

Usage:
    python content_similarity.py --duplicates     # Find duplicates
    python content_similarity.py --similar "headline"
    python content_similarity.py --report         # Generate report
"""

import argparse
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import json

DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"

# Try to import ML libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class ContentSimilarity:
    """Find similar and duplicate articles."""
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.vectorizer = None
        self.vectors = None
        self.articles = []
    
    def clean_text(self, text: str) -> str:
        """Clean text for comparison."""
        if not text:
            return ""
        
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special characters
        text = re.sub(r'[^\w\s]', '', text)
        
        return text
    
    def load_articles(self, days: int = 7, limit: int = 2000) -> List[Dict]:
        """Load recent articles."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute("""
            SELECT id, headline, paper_name, url, scraped_at
            FROM articles WHERE scraped_at >= ?
            ORDER BY scraped_at DESC LIMIT ?
        """, (cutoff, limit))
        
        self.articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return self.articles
    
    def build_vectors(self):
        """Build TF-IDF vectors for all articles."""
        if not ML_AVAILABLE:
            print("❌ Install: pip install scikit-learn numpy")
            return False
        
        if not self.articles:
            self.load_articles()
        
        texts = [self.clean_text(a['headline']) for a in self.articles]
        
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=5000,
            stop_words='english'
        )
        
        self.vectors = self.vectorizer.fit_transform(texts)
        return True
    
    def find_duplicates(self, threshold: float = None) -> List[Dict]:
        """Find duplicate articles based on headline similarity."""
        threshold = threshold or self.threshold
        
        if not self.build_vectors():
            return []
        
        print(f"🔍 Analyzing {len(self.articles)} articles for duplicates...")
        
        # Calculate pairwise similarities
        similarities = cosine_similarity(self.vectors)
        
        # Find duplicate pairs
        duplicates = []
        seen_pairs = set()
        
        for i in range(len(self.articles)):
            for j in range(i + 1, len(self.articles)):
                sim = similarities[i, j]
                
                if sim >= threshold:
                    pair_key = tuple(sorted([self.articles[i]['id'], self.articles[j]['id']]))
                    
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        
                        duplicates.append({
                            "similarity": round(float(sim), 3),
                            "article1": {
                                "id": self.articles[i]['id'],
                                "headline": self.articles[i]['headline'],
                                "paper": self.articles[i]['paper_name'],
                                "url": self.articles[i]['url']
                            },
                            "article2": {
                                "id": self.articles[j]['id'],
                                "headline": self.articles[j]['headline'],
                                "paper": self.articles[j]['paper_name'],
                                "url": self.articles[j]['url']
                            }
                        })
        
        # Sort by similarity
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        
        return duplicates
    
    def find_similar(self, query: str, top_n: int = 10) -> List[Dict]:
        """Find articles similar to query."""
        if not self.build_vectors():
            return []
        
        # Vectorize query
        query_vec = self.vectorizer.transform([self.clean_text(query)])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vec, self.vectors)[0]
        
        # Get top matches
        top_indices = np.argsort(similarities)[-top_n:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Minimum threshold
                results.append({
                    "similarity": round(float(similarities[idx]), 3),
                    "id": self.articles[idx]['id'],
                    "headline": self.articles[idx]['headline'],
                    "paper": self.articles[idx]['paper_name'],
                    "url": self.articles[idx]['url']
                })
        
        return results
    
    def cluster_duplicates(self, duplicates: List[Dict]) -> List[List[int]]:
        """Cluster duplicates into groups."""
        # Build graph of connected articles
        graph = defaultdict(set)
        
        for dup in duplicates:
            id1 = dup['article1']['id']
            id2 = dup['article2']['id']
            graph[id1].add(id2)
            graph[id2].add(id1)
        
        # Find connected components
        visited = set()
        clusters = []
        
        def dfs(node, cluster):
            if node in visited:
                return
            visited.add(node)
            cluster.append(node)
            for neighbor in graph[node]:
                dfs(neighbor, cluster)
        
        for node in graph:
            if node not in visited:
                cluster = []
                dfs(node, cluster)
                if len(cluster) > 1:
                    clusters.append(sorted(cluster))
        
        return sorted(clusters, key=len, reverse=True)
    
    def generate_report(self, days: int = 7) -> str:
        """Generate duplicate analysis report."""
        self.load_articles(days=days)
        duplicates = self.find_duplicates()
        clusters = self.cluster_duplicates(duplicates)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(self.articles),
            "duplicate_pairs": len(duplicates),
            "duplicate_clusters": len(clusters),
            "top_duplicates": duplicates[:20],
            "clusters": clusters[:10]
        }
        
        path = Path(__file__).parent / "reports" / f"duplicates_{datetime.now().strftime('%Y%m%d')}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        
        print(f"✅ Report saved: {path}")
        print(f"   {len(duplicates)} duplicate pairs in {len(clusters)} clusters")
        
        return str(path)
    
    def estimate_read_time(self, word_count: int, wpm: int = 200) -> int:
        """Estimate reading time in minutes."""
        return max(1, round(word_count / wpm))


def main():
    parser = argparse.ArgumentParser(description="Content similarity analysis")
    parser.add_argument("--duplicates", action="store_true", help="Find duplicates")
    parser.add_argument("--similar", help="Find similar articles")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold")
    
    args = parser.parse_args()
    
    analyzer = ContentSimilarity(threshold=args.threshold)
    
    if args.duplicates:
        analyzer.load_articles(days=args.days)
        duplicates = analyzer.find_duplicates()
        
        print(f"\n🔍 Found {len(duplicates)} duplicate pairs:\n")
        
        for dup in duplicates[:15]:
            print(f"  [{dup['similarity']:.0%}] Similar headlines:")
            print(f"    📰 {dup['article1']['paper']}: {dup['article1']['headline'][:60]}...")
            print(f"    📰 {dup['article2']['paper']}: {dup['article2']['headline'][:60]}...")
            print()
    
    elif args.similar:
        analyzer.load_articles(days=args.days)
        results = analyzer.find_similar(args.similar)
        
        print(f"\n🔍 Articles similar to: '{args.similar}'\n")
        
        for r in results:
            print(f"  [{r['similarity']:.0%}] {r['headline'][:70]}...")
            print(f"       {r['paper']}")
            print()
    
    elif args.report:
        analyzer.generate_report(days=args.days)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
