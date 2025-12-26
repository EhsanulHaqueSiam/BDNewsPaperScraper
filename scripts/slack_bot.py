#!/usr/bin/env python3
"""
Slack Bot for News Notifications
==================================
Send news summaries and alerts to Slack channels.

Setup:
    1. Create Slack App: https://api.slack.com/apps
    2. Add Bot Token Scopes: chat:write, channels:read
    3. Install to workspace
    4. Set SLACK_BOT_TOKEN and SLACK_CHANNEL

Usage:
    python slack_bot.py --send              # Send daily summary
    python slack_bot.py --alert "keyword"   # Alert on keyword
    python slack_bot.py --schedule          # Run scheduled
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

# Slack configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#news-alerts")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


class SlackBot:
    """Slack bot for news notifications."""
    
    def __init__(self):
        self.token = SLACK_BOT_TOKEN
        self.channel = SLACK_CHANNEL
        self.webhook_url = SLACK_WEBHOOK_URL
    
    def send_message(self, text: str, blocks: List[Dict] = None) -> bool:
        """Send message to Slack channel."""
        
        # Try webhook first (simpler)
        if self.webhook_url:
            return self._send_webhook(text, blocks)
        
        # Use Bot API
        if not self.token:
            print("❌ SLACK_BOT_TOKEN or SLACK_WEBHOOK_URL not set")
            return False
        
        url = "https://slack.com/api/chat.postMessage"
        
        payload = {
            "channel": self.channel,
            "text": text,
        }
        
        if blocks:
            payload["blocks"] = blocks
        
        return self._api_call(url, payload)
    
    def _send_webhook(self, text: str, blocks: List[Dict] = None) -> bool:
        """Send via incoming webhook."""
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"})
            
            with urlopen(req, timeout=10) as response:
                return response.status == 200
        except URLError as e:
            print(f"❌ Webhook error: {e}")
            return False
    
    def _api_call(self, url: str, payload: Dict) -> bool:
        """Make Slack API call."""
        try:
            data = json.dumps(payload).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            req = Request(url, data=data, headers=headers)
            
            with urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                if result.get("ok"):
                    print("✅ Message sent to Slack")
                    return True
                else:
                    print(f"❌ Slack error: {result.get('error')}")
                    return False
        except URLError as e:
            print(f"❌ API error: {e}")
            return False
    
    def build_summary_blocks(self, summary: Dict) -> List[Dict]:
        """Build Slack blocks for news summary."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🗞️ BD News Daily Summary"}
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {datetime.now().strftime('%B %d, %Y')}"}
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Articles*\n{summary.get('total', 0):,}"},
                    {"type": "mrkdwn", "text": f"*Newspapers*\n{len(summary.get('by_paper', {}))}"},
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*📰 Top Newspapers*"}
            }
        ]
        
        # Top papers
        papers_text = "\n".join([
            f"• {paper}: {count}"
            for paper, count in list(summary.get('by_paper', {}).items())[:5]
        ])
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": papers_text}
        })
        
        # Headlines
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📌 Top Headlines*"}
        })
        
        for h in summary.get('headlines', [])[:5]:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{h['url']}|{h['headline'][:80]}...>\n_{h['paper_name']}_"
                }
            })
        
        return blocks
    
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
        
        blocks = self.build_summary_blocks(summary)
        text = f"🗞️ BD News: {summary['total']} articles from {len(summary['by_paper'])} newspapers"
        
        return self.send_message(text, blocks)
    
    def send_alert(self, headline: str, url: str, paper: str) -> bool:
        """Send breaking news alert."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Breaking News Alert"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{headline}*\n\n📰 {paper}"}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Read Article"},
                        "url": url,
                        "style": "primary"
                    }
                ]
            }
        ]
        
        return self.send_message(f"🚨 {headline[:100]}", blocks)
    
    def run_scheduled(self, interval_hours: int = 24):
        """Run as scheduled service."""
        print(f"📅 Running Slack bot every {interval_hours} hours")
        
        while True:
            try:
                self.send_daily_summary()
                time.sleep(interval_hours * 3600)
            except KeyboardInterrupt:
                print("\n👋 Stopping")
                break


def main():
    parser = argparse.ArgumentParser(description="Slack news bot")
    parser.add_argument("--send", action="store_true", help="Send summary")
    parser.add_argument("--test", action="store_true", help="Send test message")
    parser.add_argument("--schedule", action="store_true", help="Run scheduled")
    parser.add_argument("--interval", type=int, default=24, help="Hours between sends")
    
    args = parser.parse_args()
    
    bot = SlackBot()
    
    if args.send:
        bot.send_daily_summary()
    elif args.test:
        bot.send_message("👋 Hello from BD News Scraper!")
    elif args.schedule:
        bot.run_scheduled(args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
