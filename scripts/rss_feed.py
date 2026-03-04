#!/usr/bin/env python3
"""
RSS Feed Generator
==================
Generates RSS feeds from scraped news articles.

Usage:
    python rss_feed.py                    # Generate feed for all articles
    python rss_feed.py --paper ProthomAlo # Generate feed for specific paper
    python rss_feed.py --days 7           # Last 7 days only
    python rss_feed.py --serve            # Start HTTP server on port 8080
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import html


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
OUTPUT_DIR = Path(__file__).parent / "feeds"


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)


def generate_rss_feed(
    paper_name: str = None,
    days: int = None,
    limit: int = 100,
    output_path: Path = None
) -> str:
    """Generate RSS feed from database articles."""
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return None
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Build query
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if paper_name:
        query += " AND paper_name = ?"
        params.append(paper_name)
    
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query += " AND scraped_at >= ?"
        params.append(cutoff)
    
    query += " ORDER BY scraped_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    articles = cursor.fetchall()
    
    if not articles:
        print("❌ No articles found")
        return None
    
    # Create RSS structure
    rss = Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    channel = SubElement(rss, "channel")
    
    # Channel metadata
    title = f"BD News - {paper_name}" if paper_name else "BD Newspaper Scraper"
    SubElement(channel, "title").text = title
    SubElement(channel, "link").text = "https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper"
    SubElement(channel, "description").text = f"Latest news from Bangladeshi newspapers ({len(articles)} articles)"
    SubElement(channel, "language").text = "en-bd"
    SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    SubElement(channel, "generator").text = "BDNewsPaperScraper RSS Generator"
    
    # Add articles as items
    for article in articles:
        item = SubElement(channel, "item")
        
        SubElement(item, "title").text = escape_xml(article["headline"])
        SubElement(item, "link").text = article["url"]
        SubElement(item, "guid", isPermaLink="true").text = article["url"]
        
        # Description (truncated body)
        body = dict(article).get("article") or ""
        if len(body) > 500:
            body = body[:500] + "..."
        SubElement(item, "description").text = escape_xml(body)
        
        # Category
        if article["category"]:
            SubElement(item, "category").text = escape_xml(article["category"])
        
        # Source
        SubElement(item, "source", url=article["url"]).text = escape_xml(article["paper_name"])
        
        # Publication date
        pub_date = article["publication_date"] or article["scraped_at"]
        if pub_date and pub_date != "Unknown":
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                SubElement(item, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S +0600")
            except (ValueError, AttributeError):
                pass
    
    conn.close()
    
    # Format XML
    xml_str = minidom.parseString(tostring(rss, encoding="unicode")).toprettyxml(indent="  ")
    # Remove extra blank lines
    xml_str = "\n".join(line for line in xml_str.split("\n") if line.strip())
    
    # Add XML declaration
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str.split("\n", 1)[1]
    
    # Save to file
    if output_path is None:
        OUTPUT_DIR.mkdir(exist_ok=True)
        filename = f"{paper_name.lower().replace(' ', '_')}.xml" if paper_name else "all.xml"
        output_path = OUTPUT_DIR / filename
    
    output_path.write_text(xml_str, encoding="utf-8")
    print(f"✅ Generated RSS feed: {output_path} ({len(articles)} articles)")
    
    return str(output_path)


def generate_all_feeds():
    """Generate separate RSS feeds for each newspaper."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    papers = [row[0] for row in conn.execute("SELECT DISTINCT paper_name FROM articles").fetchall()]
    conn.close()
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Generate main feed
    generate_rss_feed(limit=200)
    
    # Generate per-paper feeds
    for paper in papers:
        generate_rss_feed(paper_name=paper, limit=50)
    
    # Generate index HTML
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>BD News RSS Feeds</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        ul { list-style: none; padding: 0; }
        li { margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .rss-icon { color: #ff6600; margin-right: 10px; }
    </style>
</head>
<body>
    <h1>🗞️ BD Newspaper RSS Feeds</h1>
    <p>Subscribe to news feeds from Bangladeshi newspapers.</p>
    <ul>
        <li><span class="rss-icon">📰</span><a href="all.xml">All Newspapers (Combined)</a></li>
"""
    for paper in sorted(papers):
        filename = f"{paper.lower().replace(' ', '_')}.xml"
        index_html += f'        <li><span class="rss-icon">📄</span><a href="{filename}">{paper}</a></li>\n'
    
    index_html += """    </ul>
    <p style="color: #666; margin-top: 30px;">Generated by <a href="https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper">BDNewsPaperScraper</a></p>
</body>
</html>"""
    
    (OUTPUT_DIR / "index.html").write_text(index_html)
    print(f"✅ Generated index: {OUTPUT_DIR}/index.html")


def serve_feeds(port: int = 8080):
    """Start HTTP server to serve RSS feeds."""
    import os
    os.chdir(OUTPUT_DIR)
    
    print(f"🌐 Serving RSS feeds at http://localhost:{port}/")
    print(f"   Main feed: http://localhost:{port}/all.xml")
    print("   Press Ctrl+C to stop")
    
    httpd = HTTPServer(("", port), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Generate RSS feeds from scraped articles")
    parser.add_argument("--paper", help="Generate feed for specific newspaper")
    parser.add_argument("--days", type=int, help="Limit to last N days")
    parser.add_argument("--limit", type=int, default=100, help="Maximum articles per feed")
    parser.add_argument("--all", action="store_true", help="Generate feeds for all newspapers")
    parser.add_argument("--serve", action="store_true", help="Start HTTP server")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    
    args = parser.parse_args()
    
    if args.all:
        generate_all_feeds()
    elif args.serve:
        if not (OUTPUT_DIR / "all.xml").exists():
            generate_all_feeds()
        serve_feeds(args.port)
    else:
        generate_rss_feed(
            paper_name=args.paper,
            days=args.days,
            limit=args.limit
        )


if __name__ == "__main__":
    main()
