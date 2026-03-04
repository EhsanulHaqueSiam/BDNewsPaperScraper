#!/usr/bin/env python3
"""
Webhook & Alert System
======================
Send alerts for breaking news keywords and new articles.

Features:
    - Webhook notifications (Discord, Slack, custom)
    - Keyword-based alerts
    - Breaking news detection
    - Rate limiting to prevent spam

Usage:
    python alerts.py --setup                    # Interactive setup
    python alerts.py --monitor                  # Start monitoring
    python alerts.py --keywords "politics,cricket"  # Set keywords
    python alerts.py --test                     # Send test alert
"""

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
CONFIG_PATH = Path(__file__).parent / "alerts_config.json"


def load_config() -> dict:
    """Load alert configuration."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "webhooks": [],
        "keywords": [],
        "enabled": False,
        "check_interval": 300,
        "last_check": None
    }


def save_config(config: dict):
    """Save alert configuration."""
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def send_discord_webhook(url: str, message: str, title: str = "BD News Alert") -> bool:
    """Send message to Discord webhook."""
    data = json.dumps({
        "embeds": [{
            "title": f"🗞️ {title}",
            "description": message[:2000],
            "color": 0x00ff00,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }).encode("utf-8")
    
    try:
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as response:
            return response.status == 204
    except URLError as e:
        print(f"❌ Discord webhook error: {e}")
        return False


def send_slack_webhook(url: str, message: str, title: str = "BD News Alert") -> bool:
    """Send message to Slack webhook."""
    data = json.dumps({
        "text": f"*{title}*\n{message[:2000]}"
    }).encode("utf-8")
    
    try:
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as response:
            return response.status == 200
    except URLError as e:
        print(f"❌ Slack webhook error: {e}")
        return False


def send_generic_webhook(url: str, message: str, title: str = "BD News Alert") -> bool:
    """Send message to generic webhook."""
    data = json.dumps({
        "title": title,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }).encode("utf-8")
    
    try:
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as response:
            return response.status in [200, 201, 204]
    except URLError as e:
        print(f"❌ Webhook error: {e}")
        return False


def send_alert(message: str, title: str = "BD News Alert"):
    """Send alert to all configured webhooks."""
    config = load_config()
    
    for webhook in config.get("webhooks", []):
        url = webhook.get("url")
        webhook_type = webhook.get("type", "generic")
        
        if not url:
            continue
        
        if webhook_type == "discord":
            send_discord_webhook(url, message, title)
        elif webhook_type == "slack":
            send_slack_webhook(url, message, title)
        else:
            send_generic_webhook(url, message, title)
    
    print(f"✅ Alert sent: {title}")


def check_for_alerts() -> List[dict]:
    """Check database for articles matching keywords."""
    config = load_config()
    keywords = config.get("keywords", [])
    last_check = config.get("last_check")
    
    if not keywords:
        return []
    
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get articles since last check
    if last_check:
        query = "SELECT * FROM articles WHERE scraped_at > ? ORDER BY scraped_at DESC"
        cursor = conn.execute(query, (last_check,))
    else:
        # First run - get last hour
        cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
        query = "SELECT * FROM articles WHERE scraped_at > ? ORDER BY scraped_at DESC"
        cursor = conn.execute(query, (cutoff,))
    
    articles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Update last check time
    config["last_check"] = datetime.now().isoformat()
    save_config(config)
    
    # Filter by keywords
    matching = []
    for article in articles:
        headline = article.get("headline", "").lower()
        body = (article.get("article_body") or "").lower()
        
        for keyword in keywords:
            if keyword.lower() in headline or keyword.lower() in body:
                article["matched_keyword"] = keyword
                matching.append(article)
                break
    
    return matching


def monitor_loop():
    """Run continuous monitoring."""
    config = load_config()
    interval = config.get("check_interval", 300)
    
    print(f"🔍 Starting alert monitor (checking every {interval}s)")
    print(f"   Keywords: {config.get('keywords', [])}")
    print("   Press Ctrl+C to stop")
    
    while True:
        try:
            matching = check_for_alerts()
            
            if matching:
                print(f"⚡ Found {len(matching)} matching articles!")
                
                for article in matching[:5]:
                    message = f"**{article.get('headline', 'No title')}**\n\n"
                    message += f"🔑 Keyword: `{article.get('matched_keyword')}`\n"
                    message += f"📰 Source: {article.get('paper_name')}\n"
                    message += f"🔗 {article.get('url')}"
                    
                    send_alert(message, title="Breaking News Alert")
                    time.sleep(1)  # Rate limiting
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\n👋 Stopping monitor")
            break


def setup_wizard():
    """Interactive setup for alerts."""
    config = load_config()
    
    print("\n🔧 Alert System Setup\n")
    
    # Keywords
    print("Current keywords:", config.get("keywords", []))
    keywords_input = input("Enter keywords (comma-separated, or press Enter to keep): ").strip()
    if keywords_input:
        config["keywords"] = [k.strip() for k in keywords_input.split(",")]
    
    # Webhook
    print("\nWebhook types: discord, slack, generic")
    webhook_type = input("Enter webhook type (or press Enter to skip): ").strip().lower()
    
    if webhook_type:
        webhook_url = input(f"Enter {webhook_type} webhook URL: ").strip()
        if webhook_url:
            config["webhooks"].append({
                "type": webhook_type,
                "url": webhook_url
            })
    
    # Interval
    interval = input("\nCheck interval in seconds (default 300): ").strip()
    if interval.isdigit():
        config["check_interval"] = int(interval)
    
    config["enabled"] = True
    save_config(config)
    
    print("\n✅ Configuration saved!")
    print(f"   Keywords: {config['keywords']}")
    print(f"   Webhooks: {len(config['webhooks'])}")


def main():
    parser = argparse.ArgumentParser(description="Webhook alert system for news")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring")
    parser.add_argument("--keywords", help="Comma-separated keywords to watch")
    parser.add_argument("--test", action="store_true", help="Send test alert")
    parser.add_argument("--status", action="store_true", help="Show current config")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_wizard()
    elif args.monitor:
        monitor_loop()
    elif args.keywords:
        config = load_config()
        config["keywords"] = [k.strip() for k in args.keywords.split(",")]
        save_config(config)
        print(f"✅ Keywords set: {config['keywords']}")
    elif args.test:
        send_alert("This is a test alert from BD Newspaper Scraper!", "Test Alert")
    elif args.status:
        config = load_config()
        print(f"Keywords: {config.get('keywords', [])}")
        print(f"Webhooks: {len(config.get('webhooks', []))}")
        print(f"Enabled: {config.get('enabled', False)}")
        print(f"Interval: {config.get('check_interval', 300)}s")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
