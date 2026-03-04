#!/usr/bin/env python3
"""
Webhooks for New Articles
==========================
Push notifications when new articles are scraped.

Features:
    - Webhook triggers on new articles
    - Supports Discord, Slack, custom endpoints
    - Keyword filtering
    - Batch notifications

Usage:
    python webhooks.py --monitor              # Watch for new articles
    python webhooks.py --test                 # Test webhook
    python webhooks.py --config               # Configure webhooks
"""

import argparse
import os
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
CONFIG_PATH = Path(__file__).parent / "webhook_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "webhooks": [],
    "keywords": [],
    "min_interval_seconds": 60,
    "batch_size": 10,
    "last_check": None
}


class WebhookManager:
    """Manage article webhooks."""
    
    def __init__(self):
        self.config = self._load_config()
        self.last_id = self._get_last_id()
    
    def _load_config(self) -> Dict:
        """Load webhook configuration."""
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
        return DEFAULT_CONFIG.copy()
    
    def _save_config(self):
        """Save configuration."""
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2))
    
    def _get_last_id(self) -> int:
        """Get last processed article ID."""
        if not DB_PATH.exists():
            return 0
        
        conn = sqlite3.connect(DB_PATH)
        result = conn.execute("SELECT MAX(id) FROM articles").fetchone()[0]
        conn.close()
        return result or 0
    
    def add_webhook(self, url: str, name: str = None, type: str = "generic") -> bool:
        """Add a webhook endpoint."""
        webhook = {
            "url": url,
            "name": name or f"Webhook {len(self.config['webhooks']) + 1}",
            "type": type,  # discord, slack, generic
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        
        self.config["webhooks"].append(webhook)
        self._save_config()
        
        print(f"✅ Added webhook: {webhook['name']}")
        return True
    
    def add_keyword(self, keyword: str):
        """Add keyword filter."""
        if keyword not in self.config["keywords"]:
            self.config["keywords"].append(keyword.lower())
            self._save_config()
            print(f"✅ Added keyword: {keyword}")
    
    def get_new_articles(self, limit: int = 50) -> List[Dict]:
        """Get articles newer than last check."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT id, headline, paper_name, category, url, scraped_at
            FROM articles WHERE id > ?
            ORDER BY id ASC LIMIT ?
        """, (self.last_id, limit))
        
        articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Filter by keywords if any
        if self.config["keywords"]:
            filtered = []
            for a in articles:
                headline_lower = a["headline"].lower()
                if any(kw in headline_lower for kw in self.config["keywords"]):
                    filtered.append(a)
            return filtered
        
        return articles
    
    def format_for_discord(self, articles: List[Dict]) -> Dict:
        """Format articles for Discord webhook."""
        embeds = []
        
        for a in articles[:10]:  # Discord limit
            embeds.append({
                "title": a["headline"][:256],
                "url": a["url"],
                "color": 0x667eea,
                "fields": [
                    {"name": "Source", "value": a["paper_name"], "inline": True},
                    {"name": "Category", "value": a.get("category") or "N/A", "inline": True}
                ],
                "timestamp": datetime.now().isoformat()
            })
        
        return {"embeds": embeds}
    
    def format_for_slack(self, articles: List[Dict]) -> Dict:
        """Format articles for Slack webhook."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🗞️ {len(articles)} New Articles"}
            }
        ]
        
        for a in articles[:10]:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{a['url']}|{a['headline'][:100]}>*\n_{a['paper_name']}_"
                }
            })
        
        return {"blocks": blocks}
    
    def format_generic(self, articles: List[Dict]) -> Dict:
        """Format for generic webhook."""
        return {
            "event": "new_articles",
            "timestamp": datetime.now().isoformat(),
            "count": len(articles),
            "articles": articles
        }
    
    def send_webhook(self, webhook: Dict, articles: List[Dict]) -> bool:
        """Send webhook notification."""
        if not webhook.get("enabled"):
            return False
        
        webhook_type = webhook.get("type", "generic")
        
        if webhook_type == "discord":
            payload = self.format_for_discord(articles)
        elif webhook_type == "slack":
            payload = self.format_for_slack(articles)
        else:
            payload = self.format_generic(articles)
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(webhook["url"], data=data, headers={"Content-Type": "application/json"})
            
            with urlopen(req, timeout=10) as response:
                if response.status in [200, 204]:
                    print(f"✅ Webhook sent: {webhook['name']}")
                    return True
                return False
        except URLError as e:
            print(f"❌ Webhook failed: {webhook['name']} - {e}")
            return False
    
    def notify_all(self, articles: List[Dict]):
        """Send to all enabled webhooks."""
        if not articles:
            return
        
        for webhook in self.config["webhooks"]:
            if webhook.get("enabled"):
                self.send_webhook(webhook, articles)
    
    def monitor(self, interval: int = 60):
        """Monitor for new articles and send webhooks."""
        print(f"🔍 Monitoring for new articles (checking every {interval}s)")
        print(f"   Keywords: {self.config['keywords'] or 'All articles'}")
        print(f"   Webhooks: {len([w for w in self.config['webhooks'] if w.get('enabled')])}")
        print("   Press Ctrl+C to stop\n")
        
        while True:
            try:
                articles = self.get_new_articles()
                
                if articles:
                    print(f"📰 {len(articles)} new articles found")
                    self.notify_all(articles)
                    
                    # Update last ID
                    self.last_id = max(a["id"] for a in articles)
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - No new articles")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n👋 Stopping monitor")
                break
    
    def test_webhook(self, index: int = 0):
        """Test a webhook with sample data."""
        if not self.config["webhooks"]:
            print("❌ No webhooks configured")
            return
        
        webhook = self.config["webhooks"][index]
        
        sample = [{
            "id": 0,
            "headline": "Test Article - Webhook Integration Check",
            "paper_name": "Test Paper",
            "category": "Technology",
            "url": "https://example.com/test",
            "scraped_at": datetime.now().isoformat()
        }]
        
        self.send_webhook(webhook, sample)


def main():
    parser = argparse.ArgumentParser(description="Webhook notifications")
    parser.add_argument("--monitor", action="store_true", help="Monitor mode")
    parser.add_argument("--test", action="store_true", help="Test webhook")
    parser.add_argument("--add-webhook", help="Add webhook URL")
    parser.add_argument("--add-keyword", help="Add keyword filter")
    parser.add_argument("--type", default="generic", help="Webhook type: discord, slack, generic")
    parser.add_argument("--interval", type=int, default=60, help="Check interval")
    parser.add_argument("--list", action="store_true", help="List webhooks")
    
    args = parser.parse_args()
    
    manager = WebhookManager()
    
    if args.add_webhook:
        manager.add_webhook(args.add_webhook, type=args.type)
    elif args.add_keyword:
        manager.add_keyword(args.add_keyword)
    elif args.test:
        manager.test_webhook()
    elif args.monitor:
        manager.monitor(args.interval)
    elif args.list:
        print("\n📡 Configured Webhooks:\n")
        for i, w in enumerate(manager.config["webhooks"]):
            status = "✅" if w.get("enabled") else "❌"
            print(f"  {i}. {status} {w['name']} ({w['type']})")
        print(f"\n🔑 Keywords: {manager.config['keywords'] or 'None'}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
