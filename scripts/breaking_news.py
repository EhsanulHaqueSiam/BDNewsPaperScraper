#!/usr/bin/env python3
"""
Breaking News Detector
=======================
Detect sudden topic spikes and breaking news patterns.

Features:
    - Real-time spike detection
    - Keyword velocity tracking
    - Multi-source correlation
    - Alert notifications

Usage:
    python breaking_news.py --monitor       # Start monitoring
    python breaking_news.py --check         # One-time check
    python breaking_news.py --trending      # Show trending now
"""

import argparse
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple
import re
import json


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"


class BreakingNewsDetector:
    """Detect breaking news through spike analysis."""
    
    def __init__(self):
        self.baseline_window = 24  # hours for baseline
        self.spike_window = 1       # hours for current
        self.spike_threshold = 3.0  # times above baseline
        self.min_articles = 3       # minimum for spike
        self.last_alerts = {}       # prevent duplicate alerts
    
    def get_keyword_counts(self, hours: int) -> Counter:
        """Get keyword counts for time window."""
        if not DB_PATH.exists():
            return Counter()
        
        conn = sqlite3.connect(DB_PATH)
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor = conn.execute("""
            SELECT headline FROM articles WHERE scraped_at >= ?
        """, (cutoff,))
        
        keywords = Counter()
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 
                      'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
                      'said', 'says', 'will', 'would', 'could', 'should', 'may', 'might'}
        
        for (headline,) in cursor.fetchall():
            words = re.findall(r'\b[a-z]{4,}\b', headline.lower())
            for word in words:
                if word not in stop_words:
                    keywords[word] += 1
        
        conn.close()
        return keywords
    
    def detect_spikes(self) -> List[Dict]:
        """Detect keyword spikes above baseline."""
        baseline = self.get_keyword_counts(self.baseline_window)
        current = self.get_keyword_counts(self.spike_window)
        
        if not current:
            return []
        
        spikes = []
        
        for keyword, count in current.most_common(50):
            if count < self.min_articles:
                continue
            
            # Normalize baseline to current window
            baseline_count = baseline.get(keyword, 0)
            baseline_rate = baseline_count / self.baseline_window
            expected = baseline_rate * self.spike_window
            
            if expected == 0:
                # New keyword appearing
                if count >= self.min_articles:
                    spikes.append({
                        "keyword": keyword,
                        "count": count,
                        "spike_ratio": float('inf'),
                        "type": "new_topic"
                    })
            else:
                spike_ratio = count / expected
                
                if spike_ratio >= self.spike_threshold:
                    spikes.append({
                        "keyword": keyword,
                        "count": count,
                        "expected": round(expected, 1),
                        "spike_ratio": round(spike_ratio, 1),
                        "type": "spike"
                    })
        
        return sorted(spikes, key=lambda x: x.get('spike_ratio', 0), reverse=True)
    
    def get_related_articles(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Get articles related to spike keyword."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(hours=self.spike_window)).isoformat()
        
        cursor = conn.execute("""
            SELECT headline, paper_name, url, scraped_at
            FROM articles
            WHERE scraped_at >= ? AND LOWER(headline) LIKE ?
            ORDER BY scraped_at DESC
            LIMIT ?
        """, (cutoff, f"%{keyword}%", limit))
        
        articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return articles
    
    def check_multi_source(self, keyword: str) -> Dict:
        """Check if keyword appears across multiple sources."""
        if not DB_PATH.exists():
            return {}
        
        conn = sqlite3.connect(DB_PATH)
        cutoff = (datetime.now() - timedelta(hours=self.spike_window)).isoformat()
        
        cursor = conn.execute("""
            SELECT paper_name, COUNT(*) as count
            FROM articles
            WHERE scraped_at >= ? AND LOWER(headline) LIKE ?
            GROUP BY paper_name
        """, (cutoff, f"%{keyword}%"))
        
        sources = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        return {
            "keyword": keyword,
            "sources": len(sources),
            "by_paper": sources,
            "is_breaking": len(sources) >= 3  # 3+ sources = likely breaking
        }
    
    def get_breaking_news(self) -> List[Dict]:
        """Get confirmed breaking news stories."""
        spikes = self.detect_spikes()
        breaking = []
        
        for spike in spikes[:10]:
            keyword = spike["keyword"]
            
            # Skip if recently alerted
            last_alert = self.last_alerts.get(keyword)
            if last_alert and (datetime.now() - last_alert).seconds < 3600:
                continue
            
            multi = self.check_multi_source(keyword)
            
            if multi.get("is_breaking") or spike.get("type") == "new_topic":
                articles = self.get_related_articles(keyword)
                
                breaking.append({
                    "keyword": keyword,
                    "spike": spike,
                    "sources": multi,
                    "articles": articles,
                    "detected_at": datetime.now().isoformat()
                })
                
                self.last_alerts[keyword] = datetime.now()
        
        return breaking
    
    def get_trending(self) -> List[Dict]:
        """Get currently trending topics."""
        current = self.get_keyword_counts(6)  # Last 6 hours
        
        trending = []
        for keyword, count in current.most_common(20):
            multi = self.check_multi_source(keyword)
            trending.append({
                "keyword": keyword,
                "mentions": count,
                "sources": multi.get("sources", 0)
            })
        
        return trending
    
    def monitor(self, interval_seconds: int = 300):
        """Continuous monitoring for breaking news."""
        print(f"🔍 Monitoring for breaking news (checking every {interval_seconds}s)")
        print("   Press Ctrl+C to stop\n")
        
        while True:
            try:
                breaking = self.get_breaking_news()
                
                if breaking:
                    print(f"\n🚨 BREAKING NEWS DETECTED at {datetime.now().strftime('%H:%M:%S')}")
                    for story in breaking:
                        print(f"\n   📰 Topic: {story['keyword'].upper()}")
                        print(f"   📊 {story['spike']['count']} articles from {story['sources']['sources']} sources")
                        
                        if story['articles']:
                            print(f"   📌 {story['articles'][0]['headline'][:70]}...")
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - No breaking news detected")
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\n👋 Stopping monitor")
                break
    
    def save_report(self) -> str:
        """Generate and save breaking news report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "breaking": self.get_breaking_news(),
            "trending": self.get_trending(),
            "spikes": self.detect_spikes()[:20]
        }
        
        path = Path(__file__).parent / "reports" / f"breaking_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        
        print(f"✅ Report saved: {path}")
        return str(path)


def main():
    parser = argparse.ArgumentParser(description="Breaking news detector")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring")
    parser.add_argument("--check", action="store_true", help="One-time check")
    parser.add_argument("--trending", action="store_true", help="Show trending")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--interval", type=int, default=300, help="Check interval (seconds)")
    
    args = parser.parse_args()
    
    detector = BreakingNewsDetector()
    
    if args.monitor:
        detector.monitor(args.interval)
    elif args.check:
        breaking = detector.get_breaking_news()
        if breaking:
            print("🚨 Breaking News Found:\n")
            for story in breaking:
                print(f"  📰 {story['keyword'].upper()}")
                print(f"     {story['spike']['count']} articles from {story['sources']['sources']} sources\n")
        else:
            print("ℹ️ No breaking news detected")
    elif args.trending:
        trending = detector.get_trending()
        print("🔥 Trending Now:\n")
        for t in trending:
            print(f"  • {t['keyword']}: {t['mentions']} mentions ({t['sources']} sources)")
    elif args.report:
        detector.save_report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
