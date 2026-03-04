#!/usr/bin/env python3
"""
Spider Status Page & Health Monitor
====================================
Monitor the health and status of all spiders.

Features:
    - Test all spiders for connectivity
    - Generate status page
    - Track success/failure rates
    - Export status as JSON/HTML

Usage:
    python status_page.py                 # Generate status page
    python status_page.py --test          # Test all spiders
    python status_page.py --json          # Output as JSON
    python status_page.py --serve         # Serve status page
"""

import argparse
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List
import os


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
STATUS_DIR = Path(__file__).parent / "status"


def get_spider_list() -> List[str]:
    """Get list of all available spiders."""
    try:
        result = subprocess.run(
            ["scrapy", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=30
        )
        return result.stdout.strip().split("\n") if result.stdout else []
    except Exception as e:
        print(f"❌ Failed to get spider list: {e}")
        return []


def test_spider(spider_name: str, timeout: int = 60) -> Dict:
    """Test a single spider."""
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            ["scrapy", "crawl", spider_name, "-s", "CLOSESPIDER_ITEMCOUNT=1", "-s", "LOG_LEVEL=ERROR"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=timeout
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "spider": spider_name,
            "status": "✅ OK" if result.returncode == 0 else "⚠️ Warning",
            "return_code": result.returncode,
            "duration": round(duration, 2),
            "error": result.stderr[:200] if result.returncode != 0 else None,
            "tested_at": datetime.now().isoformat()
        }
        
    except subprocess.TimeoutExpired:
        return {
            "spider": spider_name,
            "status": "⏱️ Timeout",
            "return_code": -1,
            "duration": timeout,
            "error": f"Exceeded {timeout}s timeout",
            "tested_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "spider": spider_name,
            "status": "❌ Error",
            "return_code": -1,
            "duration": 0,
            "error": str(e),
            "tested_at": datetime.now().isoformat()
        }


def get_spider_stats() -> Dict[str, Dict]:
    """Get article counts and last scraped times for each spider."""
    if not DB_PATH.exists():
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get counts and last scraped
    query = """
        SELECT 
            paper_name,
            COUNT(*) as article_count,
            MAX(scraped_at) as last_scraped
        FROM articles 
        GROUP BY paper_name
    """
    
    stats = {}
    for row in conn.execute(query).fetchall():
        stats[row["paper_name"]] = {
            "count": row["article_count"],
            "last_scraped": row["last_scraped"]
        }
    
    conn.close()
    return stats


def generate_status_page(test_results: List[Dict] = None) -> str:
    """Generate HTML status page."""
    STATUS_DIR.mkdir(exist_ok=True)
    
    spiders = get_spider_list()
    stats = get_spider_stats()
    
    # Generate HTML
    html = """<!DOCTYPE html>
<html>
<head>
    <title>BD Newspaper Scraper - Status</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; margin-bottom: 10px; }
        .meta { color: #666; margin-bottom: 30px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #0066cc; }
        .stat-label { color: #666; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #0066cc; color: white; }
        tr:hover { background: #f9f9f9; }
        .ok { color: #28a745; }
        .warning { color: #ffc107; }
        .error { color: #dc3545; }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge-api { background: #28a745; color: white; }
        .badge-html { background: #6c757d; color: white; }
    </style>
</head>
<body>
    <h1>🗞️ BD Newspaper Scraper Status</h1>
    <p class="meta">Last updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">""" + str(len(spiders)) + """</div>
            <div class="stat-label">Spiders</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">""" + str(sum(s.get('count', 0) for s in stats.values())) + """</div>
            <div class="stat-label">Total Articles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">""" + str(len(stats)) + """</div>
            <div class="stat-label">Active Sources</div>
        </div>
    </div>
    
    <h2>📊 Spider Status</h2>
    <table>
        <tr>
            <th>Spider</th>
            <th>Newspaper</th>
            <th>Articles</th>
            <th>Last Scraped</th>
            <th>Status</th>
        </tr>
"""
    
    # API-based spiders
    api_spiders = ['prothomalo', 'thedailystar', 'dailysun', 'tbsnews', 'unb', 'ittefaq', 'jugantor']
    
    for spider in sorted(spiders):
        spider_stats = stats.get(spider, {})
        count = spider_stats.get('count', 0)
        last = spider_stats.get('last_scraped', 'Never')
        
        # Determine status based on last scraped
        if last and last != 'Never':
            try:
                last_dt = datetime.fromisoformat(last)
                days_ago = (datetime.now() - last_dt).days
                if days_ago <= 1:
                    status = '<span class="ok">✅ Active</span>'
                elif days_ago <= 7:
                    status = '<span class="warning">⚠️ ' + str(days_ago) + 'd ago</span>'
                else:
                    status = '<span class="error">❌ ' + str(days_ago) + 'd ago</span>'
            except:
                status = '<span class="warning">⚠️ Unknown</span>'
        else:
            status = '<span class="error">❌ Never</span>'
        
        badge = '<span class="badge badge-api">API</span>' if spider in api_spiders else '<span class="badge badge-html">HTML</span>'
        
        html += f"""        <tr>
            <td><code>{spider}</code> {badge}</td>
            <td>{spider}</td>
            <td>{count:,}</td>
            <td>{last[:19] if last else 'Never'}</td>
            <td>{status}</td>
        </tr>
"""
    
    html += """    </table>
    
    <p style="margin-top: 30px; color: #666; text-align: center;">
        <a href="https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper">GitHub</a> |
        <a href="status.json">JSON API</a>
    </p>
</body>
</html>"""
    
    # Save HTML
    (STATUS_DIR / "index.html").write_text(html)
    print(f"✅ Status page: {STATUS_DIR}/index.html")
    
    # Save JSON
    status_json = {
        "generated_at": datetime.now().isoformat(),
        "total_spiders": len(spiders),
        "total_articles": sum(s.get('count', 0) for s in stats.values()),
        "spiders": [
            {
                "name": spider,
                "articles": stats.get(spider, {}).get('count', 0),
                "last_scraped": stats.get(spider, {}).get('last_scraped'),
                "is_api": spider in api_spiders
            }
            for spider in spiders
        ]
    }
    
    (STATUS_DIR / "status.json").write_text(json.dumps(status_json, indent=2))
    
    return html


def test_all_spiders(limit: int = None) -> List[Dict]:
    """Test all spiders for connectivity."""
    spiders = get_spider_list()
    if limit:
        spiders = spiders[:limit]
    
    print(f"🧪 Testing {len(spiders)} spiders...\n")
    
    results = []
    for i, spider in enumerate(spiders, 1):
        print(f"[{i}/{len(spiders)}] Testing {spider}...", end=" ", flush=True)
        result = test_spider(spider)
        print(result["status"])
        results.append(result)
    
    # Summary
    ok = sum(1 for r in results if "OK" in r["status"])
    print(f"\n📊 Results: {ok}/{len(results)} spiders OK")
    
    return results


def serve_status(port: int = 8081):
    """Serve status page."""
    os.chdir(STATUS_DIR)
    print(f"🌐 Serving status page at http://localhost:{port}/")
    httpd = HTTPServer(("", port), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Spider status page and health monitor")
    parser.add_argument("--test", action="store_true", help="Test all spiders")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--serve", action="store_true", help="Serve status page")
    parser.add_argument("--port", type=int, default=8081, help="Server port")
    parser.add_argument("--limit", type=int, help="Limit spiders to test")
    
    args = parser.parse_args()
    
    if args.test:
        results = test_all_spiders(args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.serve:
        generate_status_page()
        serve_status(args.port)
    elif args.json:
        stats = get_spider_stats()
        print(json.dumps(stats, indent=2))
    else:
        generate_status_page()


if __name__ == "__main__":
    main()
