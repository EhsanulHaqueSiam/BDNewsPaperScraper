#!/usr/bin/env python3
"""
Performance monitoring script for BDNewsPaper scrapers.
Provides real-time stats and performance metrics.
"""

import sqlite3
import time
import os
from datetime import datetime, timedelta
import json


class PerformanceMonitor:
    """Monitor scraping performance and generate reports."""
    
    def __init__(self, db_path="news_articles.db"):
        self.db_path = db_path
        self.start_time = time.time()
    
    def get_scraping_stats(self, hours_back=24):
        """Get scraping statistics for the last N hours."""
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get articles added in the last N hours
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Total articles in period
            cursor.execute(
                "SELECT COUNT(*) FROM articles WHERE created_at > ?", 
                (cutoff_str,)
            )
            recent_articles = cursor.fetchone()[0]
            
            # Articles by paper
            cursor.execute(
                """
                SELECT paper_name, COUNT(*) as count 
                FROM articles 
                WHERE created_at > ? 
                GROUP BY paper_name 
                ORDER BY count DESC
                """, 
                (cutoff_str,)
            )
            by_paper = dict(cursor.fetchall())
            
            # Total articles in database
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            # Average article length
            cursor.execute(
                "SELECT AVG(LENGTH(content)) FROM articles WHERE created_at > ?", 
                (cutoff_str,)
            )
            avg_length = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                "recent_articles": recent_articles,
                "total_articles": total_articles,
                "articles_by_paper": by_paper,
                "avg_article_length": round(avg_length, 2),
                "articles_per_hour": round(recent_articles / hours_back, 2),
                "period_hours": hours_back,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}
    
    def generate_report(self):
        """Generate a comprehensive performance report."""
        stats_24h = self.get_scraping_stats(24)
        stats_1h = self.get_scraping_stats(1)
        
        report = {
            "last_24_hours": stats_24h,
            "last_1_hour": stats_1h,
            "report_generated": datetime.now().isoformat()
        }
        
        return report
    
    def save_report(self, filename=None):
        """Save performance report to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"performance_report_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filename


def main():
    """Command line interface for performance monitoring."""
    import sys
    
    monitor = PerformanceMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "report":
            # Generate and save report
            filename = monitor.save_report()
            print(f"Performance report saved to: {filename}")
        elif sys.argv[1] == "stats":
            # Show quick stats
            stats = monitor.get_scraping_stats()
            print(json.dumps(stats, indent=2))
        else:
            print("Usage: python performance_monitor.py [report|stats]")
    else:
        # Show real-time monitoring
        print("BDNewsPaper Performance Monitor")
        print("=" * 40)
        
        try:
            while True:
                stats = monitor.get_scraping_stats(1)  # Last hour
                
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Articles/hour: {stats.get('articles_per_hour', 0):.1f} | "
                      f"Total: {stats.get('total_articles', 0)} | "
                      f"Recent: {stats.get('recent_articles', 0)}", end="")
                
                time.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()