#!/usr/bin/env python3
"""
Bias Detection
===============
Analyze political bias in news reporting.

Features:
    - Source bias scoring
    - Sentiment polarity analysis
    - Topic framing detection
    - Comparative analysis

Usage:
    python bias_detection.py --analyze           # Analyze all
    python bias_detection.py --compare           # Compare sources
    python bias_detection.py --topic "politics"  # Specific topic
"""

import argparse
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List
import json


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"

# Bias indicators (simplified lexicon-based)
BIAS_LEXICON = {
    "left_leaning": [
        "progressive", "reform", "equality", "rights", "justice",
        "workers", "labor", "union", "protest", "activist",
        "climate", "environment", "green", "social", "welfare",
        "diversity", "inclusion", "marginalized", "oppressed"
    ],
    "right_leaning": [
        "traditional", "conservative", "patriot", "national",
        "security", "law and order", "business", "economy",
        "growth", "investment", "development", "heritage",
        "family values", "religious", "sovereignty"
    ],
    "sensational": [
        "shocking", "explosive", "breaking", "exclusive",
        "outrage", "scandal", "crisis", "disaster",
        "bombshell", "unprecedented", "chaos", "fury",
        "slam", "blast", "attack", "destroy"
    ],
    "neutral": [
        "report", "according to", "stated", "announced",
        "official", "spokesperson", "data shows", "study",
        "research", "analysis", "survey", "statistics"
    ]
}

# Sentiment words
SENTIMENT = {
    "positive": [
        "good", "great", "excellent", "success", "achievement",
        "progress", "growth", "improve", "benefit", "breakthrough",
        "victory", "celebrate", "proud", "hope", "optimistic"
    ],
    "negative": [
        "bad", "terrible", "failure", "crisis", "problem",
        "decline", "loss", "damage", "concern", "threat",
        "defeat", "condemn", "shame", "fear", "pessimistic"
    ]
}


class BiasDetector:
    """Detect bias in news articles."""
    
    def __init__(self):
        self.bias_patterns = {
            category: re.compile(r'\b(' + '|'.join(words) + r')\b', re.IGNORECASE)
            for category, words in BIAS_LEXICON.items()
        }
        self.sentiment_patterns = {
            sentiment: re.compile(r'\b(' + '|'.join(words) + r')\b', re.IGNORECASE)
            for sentiment, words in SENTIMENT.items()
        }
    
    def analyze_text(self, text: str) -> Dict:
        """Analyze bias and sentiment in text."""
        if not text:
            return {}
        
        text = text.lower()
        word_count = len(text.split())
        
        # Count bias indicators
        bias_counts = {}
        for category, pattern in self.bias_patterns.items():
            matches = pattern.findall(text)
            bias_counts[category] = len(matches)
        
        # Count sentiment
        sentiment_counts = {}
        for sentiment, pattern in self.sentiment_patterns.items():
            matches = pattern.findall(text)
            sentiment_counts[sentiment] = len(matches)
        
        # Calculate scores (normalized by word count)
        total_bias = sum(bias_counts.values())
        
        bias_scores = {
            k: round(v / max(total_bias, 1) * 100, 1)
            for k, v in bias_counts.items()
        }
        
        # Determine lean
        left = bias_counts.get("left_leaning", 0)
        right = bias_counts.get("right_leaning", 0)
        
        if left > right * 1.5:
            lean = "left"
        elif right > left * 1.5:
            lean = "right"
        else:
            lean = "center"
        
        # Sentiment score
        pos = sentiment_counts.get("positive", 0)
        neg = sentiment_counts.get("negative", 0)
        
        if pos > neg * 1.5:
            sentiment = "positive"
        elif neg > pos * 1.5:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "bias_counts": bias_counts,
            "bias_scores": bias_scores,
            "sentiment_counts": sentiment_counts,
            "political_lean": lean,
            "sentiment": sentiment,
            "sensational_score": round(bias_counts.get("sensational", 0) / max(word_count, 1) * 100, 2)
        }
    
    def analyze_source(self, paper_name: str, days: int = 30) -> Dict:
        """Analyze bias for a specific news source."""
        if not DB_PATH.exists():
            return {}
        
        conn = sqlite3.connect(DB_PATH)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute("""
            SELECT headline, article as article_body FROM articles
            WHERE paper_name = ? AND scraped_at >= ?
            ORDER BY scraped_at DESC LIMIT 500
        """, (paper_name, cutoff))
        
        aggregated = defaultdict(int)
        sentiment_agg = defaultdict(int)
        article_count = 0
        
        for headline, body in cursor.fetchall():
            text = f"{headline} {body or ''}"
            analysis = self.analyze_text(text)
            
            if analysis:
                article_count += 1
                for cat, count in analysis.get("bias_counts", {}).items():
                    aggregated[cat] += count
                for sent, count in analysis.get("sentiment_counts", {}).items():
                    sentiment_agg[sent] += count
        
        conn.close()
        
        if article_count == 0:
            return {}
        
        # Calculate overall lean
        left = aggregated.get("left_leaning", 0)
        right = aggregated.get("right_leaning", 0)
        
        lean_score = (right - left) / max(right + left, 1)  # -1 to 1 scale
        
        return {
            "paper_name": paper_name,
            "articles_analyzed": article_count,
            "bias_totals": dict(aggregated),
            "sentiment_totals": dict(sentiment_agg),
            "lean_score": round(lean_score, 2),
            "lean_label": "left" if lean_score < -0.2 else "right" if lean_score > 0.2 else "center",
            "sensationalism": round(aggregated.get("sensational", 0) / article_count, 1)
        }
    
    def compare_sources(self, days: int = 30) -> List[Dict]:
        """Compare bias across all sources."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("""
            SELECT DISTINCT paper_name FROM articles
            WHERE scraped_at >= ?
        """, ((datetime.now() - timedelta(days=days)).isoformat(),))
        
        papers = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        results = []
        for paper in papers:
            analysis = self.analyze_source(paper, days)
            if analysis:
                results.append(analysis)
        
        # Sort by lean score
        results.sort(key=lambda x: x.get("lean_score", 0))
        
        return results
    
    def analyze_topic(self, topic: str, days: int = 30) -> Dict:
        """Analyze how different sources cover a topic."""
        if not DB_PATH.exists():
            return {}
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute("""
            SELECT paper_name, headline, article as article_body
            FROM articles
            WHERE scraped_at >= ? AND (
                LOWER(headline) LIKE ? OR LOWER(article) LIKE ?
            )
        """, (cutoff, f"%{topic.lower()}%", f"%{topic.lower()}%"))
        
        by_source = defaultdict(list)
        
        for row in cursor.fetchall():
            text = f"{row['headline']} {row['article_body'] or ''}"
            analysis = self.analyze_text(text)
            by_source[row['paper_name']].append(analysis)
        
        conn.close()
        
        # Aggregate per source
        source_summary = {}
        for paper, analyses in by_source.items():
            if analyses:
                avg_sentiment = sum(
                    1 if a.get("sentiment") == "positive" else -1 if a.get("sentiment") == "negative" else 0
                    for a in analyses
                ) / len(analyses)
                
                source_summary[paper] = {
                    "articles": len(analyses),
                    "avg_sentiment": round(avg_sentiment, 2),
                    "dominant_lean": Counter(a.get("political_lean") for a in analyses).most_common(1)[0][0]
                }
        
        return {
            "topic": topic,
            "total_articles": sum(len(v) for v in by_source.values()),
            "sources_count": len(by_source),
            "by_source": source_summary
        }
    
    def generate_report(self, days: int = 30) -> str:
        """Generate bias analysis report."""
        comparisons = self.compare_sources(days)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "sources_analyzed": len(comparisons),
            "spectrum": {
                "left": [s for s in comparisons if s.get("lean_label") == "left"],
                "center": [s for s in comparisons if s.get("lean_label") == "center"],
                "right": [s for s in comparisons if s.get("lean_label") == "right"]
            },
            "most_sensational": sorted(comparisons, key=lambda x: x.get("sensationalism", 0), reverse=True)[:5],
            "full_comparison": comparisons
        }
        
        path = Path(__file__).parent / "reports" / f"bias_{datetime.now().strftime('%Y%m%d')}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        
        print(f"✅ Report saved: {path}")
        return str(path)


def main():
    parser = argparse.ArgumentParser(description="Bias detection")
    parser.add_argument("--analyze", action="store_true", help="Analyze sources")
    parser.add_argument("--compare", action="store_true", help="Compare all")
    parser.add_argument("--topic", help="Analyze specific topic")
    parser.add_argument("--source", help="Analyze specific source")
    parser.add_argument("--days", type=int, default=30, help="Days")
    parser.add_argument("--report", action="store_true", help="Generate report")
    
    args = parser.parse_args()
    
    detector = BiasDetector()
    
    if args.compare or args.analyze:
        results = detector.compare_sources(args.days)
        
        print("\n📊 Bias Comparison:\n")
        print(f"{'Source':<25} {'Lean':<8} {'Score':>8} {'Sensational':>12}")
        print("-" * 55)
        
        for r in results:
            print(f"{r['paper_name'][:24]:<25} {r['lean_label']:<8} {r['lean_score']:>8} {r['sensationalism']:>12.1f}")
    
    elif args.topic:
        result = detector.analyze_topic(args.topic, args.days)
        print(f"\n📰 Topic Analysis: {args.topic}\n")
        print(f"   {result['total_articles']} articles from {result['sources_count']} sources\n")
        
        for source, data in result.get("by_source", {}).items():
            print(f"   {source}: {data['articles']} articles, sentiment={data['avg_sentiment']:.1f}")
    
    elif args.source:
        result = detector.analyze_source(args.source, args.days)
        print(f"\n📰 Source Analysis: {args.source}\n")
        print(json.dumps(result, indent=2))
    
    elif args.report:
        detector.generate_report(args.days)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
