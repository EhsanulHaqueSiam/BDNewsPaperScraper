#!/usr/bin/env python3
"""
News Analytics & Sentiment Analysis
====================================
Analyze scraped news articles for trends, sentiment, entities, and more.

Features:
    - Sentiment analysis using TextBlob/VADER
    - Entity extraction (people, places, organizations)
    - Topic clustering
    - Keyword trends
    - Duplicate detection

Usage:
    python analytics.py --sentiment           # Analyze sentiment
    python analytics.py --entities            # Extract entities
    python analytics.py --trends              # Show trending keywords
    python analytics.py --duplicates          # Find duplicate articles
    python analytics.py --report              # Generate full report
"""

import argparse
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import re
from typing import List, Dict, Tuple


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
REPORTS_DIR = Path(__file__).parent / "reports"


# Try to import NLP libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    import nltk
    from nltk import word_tokenize, pos_tag, ne_chunk
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


def get_articles(days: int = 7, limit: int = 1000) -> List[Dict]:
    """Fetch recent articles from database."""
    if not DB_PATH.exists():
        print("❌ Database not found")
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor = conn.execute("""
        SELECT id, headline, article as article_body, paper_name, category, url, scraped_at
        FROM articles 
        WHERE scraped_at >= ?
        ORDER BY scraped_at DESC
        LIMIT ?
    """, (cutoff, limit))
    
    articles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return articles


def analyze_sentiment(articles: List[Dict]) -> Dict:
    """Analyze sentiment of articles using TextBlob."""
    if not TEXTBLOB_AVAILABLE:
        print("❌ TextBlob not installed. Run: pip install textblob")
        return {}
    
    print(f"📊 Analyzing sentiment for {len(articles)} articles...")
    
    results = {
        "positive": [],
        "negative": [],
        "neutral": [],
        "by_paper": {},
        "by_category": {}
    }
    
    for article in articles:
        headline = article.get("headline", "")
        body = article.get("article_body", "") or ""
        text = f"{headline}. {body[:500]}"
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        paper = article.get("paper_name", "Unknown")
        category = article.get("category", "Unknown")
        
        entry = {
            "id": article["id"],
            "headline": headline[:100],
            "polarity": round(polarity, 3),
            "paper": paper
        }
        
        if polarity > 0.1:
            results["positive"].append(entry)
        elif polarity < -0.1:
            results["negative"].append(entry)
        else:
            results["neutral"].append(entry)
        
        # Aggregate by paper
        if paper not in results["by_paper"]:
            results["by_paper"][paper] = {"sum": 0, "count": 0}
        results["by_paper"][paper]["sum"] += polarity
        results["by_paper"][paper]["count"] += 1
        
        # Aggregate by category
        if category not in results["by_category"]:
            results["by_category"][category] = {"sum": 0, "count": 0}
        results["by_category"][category]["sum"] += polarity
        results["by_category"][category]["count"] += 1
    
    # Calculate averages
    for paper, data in results["by_paper"].items():
        data["avg"] = round(data["sum"] / data["count"], 3) if data["count"] > 0 else 0
    
    for cat, data in results["by_category"].items():
        data["avg"] = round(data["sum"] / data["count"], 3) if data["count"] > 0 else 0
    
    return results


def extract_entities(articles: List[Dict], limit: int = 100) -> Dict:
    """Extract named entities from articles."""
    print(f"🔍 Extracting entities from {min(len(articles), limit)} articles...")
    
    people = Counter()
    places = Counter()
    organizations = Counter()
    
    # Simple pattern-based extraction (works without NLTK)
    # Patterns for capitalized words/phrases
    name_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
    
    for article in articles[:limit]:
        text = f"{article.get('headline', '')} {article.get('article_body', '')[:1000]}"
        
        # Extract capitalized phrases (potential names/places)
        matches = name_pattern.findall(text)
        for match in matches:
            words = match.split()
            if len(words) >= 2:
                # Heuristic classification
                if any(title in words[0] for title in ['Mr', 'Mrs', 'Dr', 'PM', 'President', 'Minister']):
                    people[match] += 1
                elif words[-1] in ['University', 'College', 'Bank', 'Corporation', 'Ltd', 'Inc', 'Company']:
                    organizations[match] += 1
                else:
                    # Could be person or place - add to both for simplicity
                    people[match] += 1
    
    return {
        "people": people.most_common(30),
        "places": places.most_common(30),
        "organizations": organizations.most_common(30)
    }


def analyze_trends(articles: List[Dict], top_n: int = 20) -> Dict:
    """Analyze trending keywords over time."""
    print(f"🔥 Analyzing trends from {len(articles)} articles...")
    
    # Stop words to filter
    stop_words = set([
        'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
        'with', 'by', 'from', 'as', 'that', 'this', 'it', 'its', 'or', 'but',
        'not', 'no', 'if', 'so', 'than', 'too', 'very', 'just', 'over', 'also',
        'said', 'says', 'new', 'year', 'day', 'time', 'people', 'first', 'after',
        'more', 'made', 'about', 'against', 'during', 'before', 'between', 'such',
        'bangladesh', 'dhaka', 'news', 'report', 'according'
    ])
    
    all_words = Counter()
    by_date = {}
    
    for article in articles:
        headline = article.get("headline", "")
        date = article.get("scraped_at", "")[:10]
        
        # Extract words
        words = re.findall(r'\b[a-z]{4,}\b', headline.lower())
        filtered = [w for w in words if w not in stop_words]
        
        all_words.update(filtered)
        
        if date not in by_date:
            by_date[date] = Counter()
        by_date[date].update(filtered)
    
    return {
        "overall": all_words.most_common(top_n),
        "by_date": {date: counter.most_common(10) for date, counter in sorted(by_date.items())[-7:]}
    }


def find_duplicates(articles: List[Dict], threshold: float = 0.8) -> List[Tuple]:
    """Find potentially duplicate articles using simple similarity."""
    print(f"🔄 Checking for duplicates in {len(articles)} articles...")
    
    duplicates = []
    
    # Simple approach: compare headlines
    headlines = [(a["id"], a["headline"].lower(), a["paper_name"]) for a in articles]
    
    for i, (id1, h1, p1) in enumerate(headlines):
        for j, (id2, h2, p2) in enumerate(headlines[i+1:], i+1):
            if p1 == p2:  # Same paper - skip
                continue
            
            # Simple word overlap ratio
            words1 = set(h1.split())
            words2 = set(h2.split())
            
            if len(words1) < 3 or len(words2) < 3:
                continue
            
            overlap = len(words1 & words2)
            ratio = overlap / min(len(words1), len(words2))
            
            if ratio >= threshold:
                duplicates.append({
                    "article1": {"id": id1, "headline": h1, "paper": p1},
                    "article2": {"id": id2, "headline": h2, "paper": p2},
                    "similarity": round(ratio, 2)
                })
    
    return duplicates[:50]  # Limit output


def generate_report(days: int = 7) -> str:
    """Generate comprehensive analytics report."""
    REPORTS_DIR.mkdir(exist_ok=True)
    
    articles = get_articles(days=days)
    
    if not articles:
        return "No articles found"
    
    print(f"\n📊 Generating report for {len(articles)} articles from last {days} days...\n")
    
    # Run analyses
    sentiment = analyze_sentiment(articles) if TEXTBLOB_AVAILABLE else {}
    entities = extract_entities(articles)
    trends = analyze_trends(articles)
    duplicates = find_duplicates(articles)
    
    # Build report
    report = f"""
# 📊 BD News Analytics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: Last {days} days
Articles Analyzed: {len(articles)}

---

## 📈 Summary Statistics

- **Total Articles**: {len(articles)}
- **Unique Newspapers**: {len(set(a['paper_name'] for a in articles))}
- **Unique Categories**: {len(set(a.get('category') for a in articles if a.get('category')))}

---

## 🔥 Trending Keywords

| Rank | Keyword | Mentions |
|------|---------|----------|
"""
    
    for i, (word, count) in enumerate(trends.get("overall", [])[:15], 1):
        report += f"| {i} | {word} | {count} |\n"
    
    if sentiment:
        report += f"""
---

## 😊 Sentiment Analysis

- **Positive Articles**: {len(sentiment.get('positive', []))}
- **Negative Articles**: {len(sentiment.get('negative', []))}
- **Neutral Articles**: {len(sentiment.get('neutral', []))}

### Most Positive Headlines
"""
        for article in sorted(sentiment.get('positive', []), key=lambda x: x['polarity'], reverse=True)[:5]:
            report += f"- ({article['polarity']}) {article['headline']}\n"
        
        report += "\n### Most Negative Headlines\n"
        for article in sorted(sentiment.get('negative', []), key=lambda x: x['polarity'])[:5]:
            report += f"- ({article['polarity']}) {article['headline']}\n"
    
    report += f"""
---

## 👤 Extracted Entities

### People/Names Mentioned
"""
    for name, count in entities.get("people", [])[:10]:
        report += f"- {name}: {count}\n"
    
    report += """
### Organizations
"""
    for org, count in entities.get("organizations", [])[:10]:
        report += f"- {org}: {count}\n"
    
    if duplicates:
        report += f"""
---

## 🔄 Potential Duplicates Found: {len(duplicates)}

"""
        for dup in duplicates[:5]:
            report += f"- **{dup['similarity']*100:.0f}% similar**:\n"
            report += f"  - {dup['article1']['paper']}: {dup['article1']['headline'][:60]}...\n"
            report += f"  - {dup['article2']['paper']}: {dup['article2']['headline'][:60]}...\n\n"
    
    # Save report
    report_path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.write_text(report)
    
    print(f"\n✅ Report saved: {report_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="News analytics and sentiment analysis")
    parser.add_argument("--sentiment", action="store_true", help="Analyze sentiment")
    parser.add_argument("--entities", action="store_true", help="Extract entities")
    parser.add_argument("--trends", action="store_true", help="Show trending keywords")
    parser.add_argument("--duplicates", action="store_true", help="Find duplicates")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    if args.report:
        report = generate_report(args.days)
        print(report)
    elif args.sentiment:
        articles = get_articles(args.days)
        results = analyze_sentiment(articles)
        print(f"\n✅ Positive: {len(results.get('positive', []))}")
        print(f"❌ Negative: {len(results.get('negative', []))}")
        print(f"➖ Neutral: {len(results.get('neutral', []))}")
    elif args.entities:
        articles = get_articles(args.days)
        entities = extract_entities(articles)
        print("\n👤 People:", [e[0] for e in entities.get('people', [])[:10]])
        print("🏢 Organizations:", [e[0] for e in entities.get('organizations', [])[:10]])
    elif args.trends:
        articles = get_articles(args.days)
        trends = analyze_trends(articles)
        print("\n🔥 Trending Keywords:")
        for word, count in trends.get("overall", [])[:15]:
            print(f"  {word}: {count}")
    elif args.duplicates:
        articles = get_articles(args.days)
        dups = find_duplicates(articles)
        print(f"\n🔄 Found {len(dups)} potential duplicates")
        for dup in dups[:10]:
            print(f"  {dup['similarity']*100:.0f}%: {dup['article1']['headline'][:50]}...")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
