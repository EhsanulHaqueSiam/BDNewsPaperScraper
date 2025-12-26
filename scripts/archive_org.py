#!/usr/bin/env python3
"""
Archive.org Integration
========================
Archive news articles to Wayback Machine for permanent preservation.

Features:
    - Submit URLs to Wayback Machine
    - Verify archived versions
    - Batch archiving
    - Archive status tracking

Usage:
    python archive_org.py --archive-recent    # Archive recent articles
    python archive_org.py --archive-url URL   # Archive specific URL
    python archive_org.py --check-status      # Check archive status
"""

import argparse
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
ARCHIVE_LOG = Path(__file__).parent / "archive_log.json"

# Wayback Machine API
SAVE_URL = "https://web.archive.org/save/{}"
CHECK_URL = "https://archive.org/wayback/available?url={}"


class ArchiveOrg:
    """Archive articles to Wayback Machine."""
    
    def __init__(self):
        self.log = self._load_log()
        self.rate_limit = 5  # seconds between requests
    
    def _load_log(self) -> Dict:
        """Load archive log."""
        if ARCHIVE_LOG.exists():
            return json.loads(ARCHIVE_LOG.read_text())
        return {"archived": {}, "failed": [], "last_run": None}
    
    def _save_log(self):
        """Save archive log."""
        ARCHIVE_LOG.write_text(json.dumps(self.log, indent=2))
    
    def check_availability(self, url: str) -> Optional[Dict]:
        """Check if URL is already archived."""
        try:
            check_url = CHECK_URL.format(url)
            req = Request(check_url, headers={"User-Agent": "BDNewsScraper/1.0"})
            
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                if data.get("archived_snapshots", {}).get("closest"):
                    return data["archived_snapshots"]["closest"]
                return None
        except (URLError, HTTPError):
            return None
    
    def archive_url(self, url: str) -> Optional[str]:
        """Submit URL to Wayback Machine."""
        # Check if already archived recently
        if url in self.log["archived"]:
            archived_date = self.log["archived"][url].get("date", "")
            if archived_date[:10] == datetime.now().strftime("%Y-%m-%d"):
                print(f"⏭️ Already archived today: {url[:50]}")
                return self.log["archived"][url].get("archive_url")
        
        try:
            save_url = SAVE_URL.format(url)
            req = Request(save_url, headers={
                "User-Agent": "BDNewsScraper/1.0 (archiving for preservation)"
            })
            
            with urlopen(req, timeout=60) as response:
                # Get archived URL from headers
                archived_url = response.url
                
                self.log["archived"][url] = {
                    "archive_url": archived_url,
                    "date": datetime.now().isoformat(),
                    "status": "success"
                }
                self._save_log()
                
                print(f"✅ Archived: {url[:50]}")
                return archived_url
                
        except HTTPError as e:
            if e.code == 429:
                print(f"⚠️ Rate limited, waiting...")
                time.sleep(30)
            else:
                print(f"❌ Failed ({e.code}): {url[:50]}")
                self.log["failed"].append({
                    "url": url,
                    "error": str(e),
                    "date": datetime.now().isoformat()
                })
            return None
        except URLError as e:
            print(f"❌ Error: {e}")
            return None
    
    def archive_recent(self, days: int = 1, limit: int = 50) -> Dict:
        """Archive recent articles."""
        if not DB_PATH.exists():
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(DB_PATH)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute("""
            SELECT DISTINCT url FROM articles
            WHERE scraped_at >= ?
            ORDER BY scraped_at DESC LIMIT ?
        """, (cutoff, limit))
        
        urls = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"📦 Archiving {len(urls)} articles to Wayback Machine...\n")
        
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        for i, url in enumerate(urls):
            # Skip already archived
            if url in self.log["archived"]:
                results["skipped"] += 1
                continue
            
            result = self.archive_url(url)
            
            if result:
                results["success"] += 1
            else:
                results["failed"] += 1
            
            # Rate limiting
            if i < len(urls) - 1:
                print(f"⏳ Waiting {self.rate_limit}s (rate limit)...")
                time.sleep(self.rate_limit)
        
        self.log["last_run"] = datetime.now().isoformat()
        self._save_log()
        
        print(f"\n✅ Done! {results['success']} archived, {results['failed']} failed, {results['skipped']} skipped")
        return results
    
    def get_stats(self) -> Dict:
        """Get archive statistics."""
        return {
            "total_archived": len(self.log["archived"]),
            "total_failed": len(self.log["failed"]),
            "last_run": self.log["last_run"],
            "recent_archives": list(self.log["archived"].items())[-10:]
        }
    
    def verify_archives(self, limit: int = 10) -> List[Dict]:
        """Verify archived URLs are accessible."""
        results = []
        
        for url, data in list(self.log["archived"].items())[-limit:]:
            available = self.check_availability(url)
            
            results.append({
                "url": url,
                "archived": data.get("date"),
                "verified": bool(available),
                "wayback_url": available.get("url") if available else None
            })
            
            time.sleep(1)  # Be nice to the API
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Archive.org integration")
    parser.add_argument("--archive-recent", action="store_true", help="Archive recent articles")
    parser.add_argument("--archive-url", help="Archive specific URL")
    parser.add_argument("--check", help="Check if URL is archived")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--verify", action="store_true", help="Verify archives")
    parser.add_argument("--days", type=int, default=1, help="Days for recent")
    parser.add_argument("--limit", type=int, default=50, help="Limit articles")
    
    args = parser.parse_args()
    
    archiver = ArchiveOrg()
    
    if args.archive_recent:
        archiver.archive_recent(days=args.days, limit=args.limit)
    
    elif args.archive_url:
        result = archiver.archive_url(args.archive_url)
        if result:
            print(f"✅ Archived: {result}")
    
    elif args.check:
        result = archiver.check_availability(args.check)
        if result:
            print(f"✅ Archived: {result['url']}")
            print(f"   Timestamp: {result['timestamp']}")
        else:
            print("❌ Not archived")
    
    elif args.stats:
        stats = archiver.get_stats()
        print(f"\n📊 Archive Statistics:\n")
        print(f"   Total archived: {stats['total_archived']}")
        print(f"   Total failed: {stats['total_failed']}")
        print(f"   Last run: {stats['last_run']}")
    
    elif args.verify:
        results = archiver.verify_archives(args.limit)
        print(f"\n🔍 Verification Results:\n")
        for r in results:
            status = "✅" if r['verified'] else "❌"
            print(f"   {status} {r['url'][:60]}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
