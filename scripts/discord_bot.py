#!/usr/bin/env python3
"""
Discord Bot for News Notifications
====================================
Send news summaries and alerts to Discord channels.

Setup:
    1. Create Discord Application: https://discord.com/developers/applications
    2. Create Bot and get token
    3. Add to server with Send Messages permission
    4. Set DISCORD_WEBHOOK_URL or DISCORD_BOT_TOKEN

Usage:
    python discord_bot.py --send           # Send summary
    python discord_bot.py --alert          # Send breaking alert
    python discord_bot.py --schedule       # Run scheduled
"""

import argparse
import os
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from urllib.request import Request, urlopen
from urllib.error import URLError


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"

# Discord configuration
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")


class DiscordBot:
    """Discord bot for news notifications."""
    
    def __init__(self):
        self.webhook_url = DISCORD_WEBHOOK_URL
        self.bot_token = DISCORD_BOT_TOKEN
        self.channel_id = DISCORD_CHANNEL_ID
    
    def send_webhook(self, content: str = None, embeds: List[Dict] = None) -> bool:
        """Send message via webhook."""
        if not self.webhook_url:
            print("❌ DISCORD_WEBHOOK_URL not set")
            return False
        
        payload = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"})
            
            with urlopen(req, timeout=10) as response:
                if response.status in [200, 204]:
                    print("✅ Message sent to Discord")
                    return True
                return False
        except URLError as e:
            print(f"❌ Discord error: {e}")
            return False
    
    def build_summary_embed(self, summary: Dict) -> Dict:
        """Build Discord embed for news summary."""
        
        # Top papers field
        papers_text = "\n".join([
            f"• **{paper}**: {count}"
            for paper, count in list(summary.get('by_paper', {}).items())[:5]
        ])
        
        # Headlines field
        headlines_text = "\n".join([
            f"[{h['headline'][:60]}...]({h['url']})"
            for h in summary.get('headlines', [])[:5]
        ])
        
        embed = {
            "title": "🗞️ BD News Daily Summary",
            "description": f"📅 {datetime.now().strftime('%B %d, %Y')}",
            "color": 0x667eea,  # Purple
            "fields": [
                {
                    "name": "📊 Statistics",
                    "value": f"**{summary.get('total', 0):,}** articles from **{len(summary.get('by_paper', {}))}** newspapers",
                    "inline": False
                },
                {
                    "name": "📰 Top Newspapers",
                    "value": papers_text or "No data",
                    "inline": True
                },
                {
                    "name": "📌 Top Headlines",
                    "value": headlines_text or "No headlines",
                    "inline": False
                }
            ],
            "footer": {
                "text": "BD Newspaper Scraper"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return embed
    
    def build_alert_embed(self, headline: str, url: str, paper: str) -> Dict:
        """Build embed for breaking news alert."""
        return {
            "title": "🚨 Breaking News",
            "description": f"**{headline}**",
            "url": url,
            "color": 0xff0000,  # Red
            "fields": [
                {"name": "Source", "value": paper, "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_summary(self, days: int = 1) -> Dict:
        """Get news summary from database."""
        if not DB_PATH.exists():
            return {}
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        total = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE scraped_at >= ?", (cutoff,)
        ).fetchone()[0]
        
        by_paper = {
            row["paper_name"]: row["count"]
            for row in conn.execute("""
                SELECT paper_name, COUNT(*) as count FROM articles
                WHERE scraped_at >= ? GROUP BY paper_name ORDER BY count DESC
            """, (cutoff,)).fetchall()
        }
        
        headlines = [
            dict(row) for row in conn.execute("""
                SELECT headline, paper_name, url FROM articles
                WHERE scraped_at >= ? ORDER BY scraped_at DESC LIMIT 10
            """, (cutoff,)).fetchall()
        ]
        
        conn.close()
        
        return {"total": total, "by_paper": by_paper, "headlines": headlines}
    
    def send_daily_summary(self) -> bool:
        """Send daily news summary."""
        summary = self.get_summary()
        
        if not summary.get("total"):
            print("ℹ️ No articles to report")
            return False
        
        embed = self.build_summary_embed(summary)
        return self.send_webhook(embeds=[embed])
    
    def send_breaking_alert(self, headline: str, url: str, paper: str) -> bool:
        """Send breaking news alert."""
        embed = self.build_alert_embed(headline, url, paper)
        return self.send_webhook(content="@everyone 🚨 Breaking News!", embeds=[embed])
    
    def run_scheduled(self, interval_hours: int = 24):
        """Run as scheduled service."""
        print(f"📅 Running Discord bot every {interval_hours} hours")
        
        while True:
            try:
                self.send_daily_summary()
                time.sleep(interval_hours * 3600)
            except KeyboardInterrupt:
                print("\n👋 Stopping")
                break


def main():
    parser = argparse.ArgumentParser(description="Discord news bot")
    parser.add_argument("--send", action="store_true", help="Send summary")
    parser.add_argument("--test", action="store_true", help="Send test")
    parser.add_argument("--schedule", action="store_true", help="Run scheduled")
    parser.add_argument("--interval", type=int, default=24, help="Hours")
    
    args = parser.parse_args()
    
    bot = DiscordBot()
    
    if args.send:
        bot.send_daily_summary()
    elif args.test:
        bot.send_webhook(content="👋 Hello from BD News Scraper!")
    elif args.schedule:
        bot.run_scheduled(args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
