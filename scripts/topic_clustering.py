#!/usr/bin/env python3
"""
Topic Clustering with Machine Learning
=======================================
Cluster similar news articles using NLP and ML techniques.

Features:
    - TF-IDF vectorization
    - K-Means clustering
    - Topic extraction with keywords
    - Visualization of clusters

Usage:
    python topic_clustering.py --cluster           # Run clustering
    python topic_clustering.py --visualize         # Generate visualization
    python topic_clustering.py --similar "headline" # Find similar articles
"""

import argparse
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import re

DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"

# Try to import ML libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.decomposition import PCA, LatentDirichletAllocation
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ Install scikit-learn: pip install scikit-learn numpy")


class TopicClusterer:
    """ML-based topic clustering for news articles."""
    
    def __init__(self, n_clusters: int = 10, n_topics: int = 5):
        self.n_clusters = n_clusters
        self.n_topics = n_topics
        self.vectorizer = None
        self.model = None
        self.articles = []
        self.vectors = None
    
    def load_articles(self, days: int = 7, limit: int = 5000) -> List[Dict]:
        """Load articles from database."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute("""
            SELECT id, headline, article_body, paper_name, category, url
            FROM articles 
            WHERE scraped_at >= ?
            ORDER BY scraped_at DESC
            LIMIT ?
        """, (cutoff, limit))
        
        self.articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return self.articles
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for clustering."""
        if not text:
            return ""
        
        # Lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def fit(self) -> Dict:
        """Fit the clustering model on articles."""
        if not ML_AVAILABLE:
            return {"error": "scikit-learn not installed"}
        
        if not self.articles:
            self.load_articles()
        
        if len(self.articles) < self.n_clusters:
            return {"error": f"Not enough articles ({len(self.articles)}) for {self.n_clusters} clusters"}
        
        print(f"📊 Clustering {len(self.articles)} articles into {self.n_clusters} clusters...")
        
        # Combine headline and body for better clustering
        texts = [
            self.preprocess_text(f"{a.get('headline', '')} {a.get('article_body', '')[:500]}")
            for a in self.articles
        ]
        
        # TF-IDF Vectorization
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )
        
        self.vectors = self.vectorizer.fit_transform(texts)
        
        # K-Means clustering
        self.model = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        labels = self.model.fit_predict(self.vectors)
        
        # Assign clusters to articles
        for i, article in enumerate(self.articles):
            article['cluster'] = int(labels[i])
        
        # Extract cluster topics
        clusters = self._extract_cluster_topics()
        
        return {
            "n_articles": len(self.articles),
            "n_clusters": self.n_clusters,
            "clusters": clusters
        }
    
    def _extract_cluster_topics(self) -> List[Dict]:
        """Extract top keywords for each cluster."""
        if self.vectorizer is None or self.model is None:
            return []
        
        feature_names = self.vectorizer.get_feature_names_out()
        clusters = []
        
        for i in range(self.n_clusters):
            # Get articles in this cluster
            cluster_articles = [a for a in self.articles if a.get('cluster') == i]
            
            if not cluster_articles:
                continue
            
            # Get center of cluster
            center = self.model.cluster_centers_[i]
            
            # Get top keywords
            top_indices = center.argsort()[-10:][::-1]
            keywords = [feature_names[idx] for idx in top_indices]
            
            # Get sample headlines
            sample_headlines = [a['headline'][:80] for a in cluster_articles[:5]]
            
            clusters.append({
                "id": i,
                "size": len(cluster_articles),
                "keywords": keywords,
                "sample_headlines": sample_headlines,
                "papers": list(set(a['paper_name'] for a in cluster_articles))[:5]
            })
        
        # Sort by size
        clusters.sort(key=lambda x: x['size'], reverse=True)
        
        return clusters
    
    def find_similar(self, query: str, top_n: int = 10) -> List[Dict]:
        """Find articles similar to a query."""
        if not ML_AVAILABLE or self.vectorizer is None:
            return []
        
        # Vectorize query
        query_vec = self.vectorizer.transform([self.preprocess_text(query)])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vec, self.vectors)[0]
        
        # Get top matches
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        results = []
        for idx in top_indices:
            article = self.articles[idx].copy()
            article['similarity'] = float(similarities[idx])
            results.append(article)
        
        return results
    
    def get_trending_topics(self, hours: int = 24) -> List[Dict]:
        """Get trending topics from recent articles."""
        recent = [a for a in self.articles if a.get('cluster') is not None]
        
        if not recent:
            return []
        
        # Count cluster occurrences
        cluster_counts = Counter(a['cluster'] for a in recent)
        
        # Get cluster details
        trending = []
        for cluster_id, count in cluster_counts.most_common(5):
            cluster_articles = [a for a in recent if a['cluster'] == cluster_id]
            
            # Extract common words from headlines
            all_words = []
            for a in cluster_articles:
                words = self.preprocess_text(a.get('headline', '')).split()
                all_words.extend([w for w in words if len(w) > 3])
            
            common_words = [w for w, _ in Counter(all_words).most_common(5)]
            
            trending.append({
                "topic": " ".join(common_words[:3]).title(),
                "article_count": count,
                "keywords": common_words,
                "sample": cluster_articles[0]['headline'][:80] if cluster_articles else ""
            })
        
        return trending
    
    def save_clusters(self, output_path: str = "clusters.json"):
        """Save cluster results to JSON."""
        results = {
            "generated_at": datetime.now().isoformat(),
            "n_articles": len(self.articles),
            "n_clusters": self.n_clusters,
            "clusters": self._extract_cluster_topics(),
            "trending": self.get_trending_topics()
        }
        
        Path(output_path).write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"✅ Saved clusters to {output_path}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Topic clustering for news articles")
    parser.add_argument("--cluster", action="store_true", help="Run clustering")
    parser.add_argument("--n-clusters", type=int, default=10, help="Number of clusters")
    parser.add_argument("--days", type=int, default=7, help="Days of articles")
    parser.add_argument("--similar", help="Find similar articles to query")
    parser.add_argument("--trending", action="store_true", help="Show trending topics")
    parser.add_argument("--output", default="clusters.json", help="Output file")
    
    args = parser.parse_args()
    
    if not ML_AVAILABLE:
        print("❌ Install dependencies: pip install scikit-learn numpy")
        return
    
    clusterer = TopicClusterer(n_clusters=args.n_clusters)
    clusterer.load_articles(days=args.days)
    
    if args.cluster:
        results = clusterer.fit()
        
        if "error" in results:
            print(f"❌ {results['error']}")
            return
        
        print(f"\n📊 Clustered {results['n_articles']} articles into {results['n_clusters']} topics:\n")
        
        for cluster in results['clusters'][:10]:
            print(f"🏷️ Topic {cluster['id']} ({cluster['size']} articles)")
            print(f"   Keywords: {', '.join(cluster['keywords'][:5])}")
            print(f"   Sample: {cluster['sample_headlines'][0][:60]}...")
            print()
        
        clusterer.save_clusters(args.output)
    
    elif args.similar:
        clusterer.fit()
        results = clusterer.find_similar(args.similar)
        
        print(f"\n🔍 Articles similar to: '{args.similar}'\n")
        for r in results:
            print(f"  [{r['similarity']:.2f}] {r['headline'][:70]}...")
            print(f"         {r['paper_name']}")
            print()
    
    elif args.trending:
        clusterer.fit()
        trending = clusterer.get_trending_topics()
        
        print("\n🔥 Trending Topics:\n")
        for t in trending:
            print(f"  📰 {t['topic']} ({t['article_count']} articles)")
            print(f"     {t['sample'][:60]}...")
            print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
