#!/usr/bin/env python3
"""
News Timeline Generator
========================
Create interactive timelines of news events.

Features:
    - Chronological event visualization
    - Topic-based filtering
    - Interactive HTML output
    - JSON API for frontend

Usage:
    python news_timeline.py --generate      # Generate timeline
    python news_timeline.py --topic "politics"
    python news_timeline.py --serve         # Start server
"""

import argparse
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import http.server
import socketserver


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
OUTPUT_DIR = Path(__file__).parent / "timeline"


class NewsTimeline:
    """Generate news timelines."""
    
    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
    
    def get_events(self, days: int = 30, topic: str = None, limit: int = 500) -> List[Dict]:
        """Get news events for timeline."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        query = """
            SELECT headline, paper_name, category, url, publication_date, scraped_at
            FROM articles
            WHERE scraped_at >= ?
        """
        params = [cutoff]
        
        if topic:
            query += " AND (LOWER(headline) LIKE ? OR LOWER(category) LIKE ?)"
            params.extend([f"%{topic.lower()}%", f"%{topic.lower()}%"])
        
        query += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        
        events = []
        for row in conn.execute(query, params).fetchall():
            date_str = row["publication_date"] or row["scraped_at"]
            if date_str:
                events.append({
                    "title": row["headline"],
                    "date": date_str[:19],
                    "category": row["category"] or "News",
                    "source": row["paper_name"],
                    "url": row["url"]
                })
        
        conn.close()
        return events
    
    def group_by_date(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Group events by date."""
        grouped = defaultdict(list)
        
        for event in events:
            date = event["date"][:10] if event.get("date") else "Unknown"
            grouped[date].append(event)
        
        return dict(sorted(grouped.items(), reverse=True))
    
    def generate_html(self, events: List[Dict], title: str = "News Timeline") -> str:
        """Generate interactive HTML timeline."""
        grouped = self.group_by_date(events)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 2rem; font-size: 2.5rem; }}
        .stats {{ 
            display: flex; justify-content: center; gap: 2rem; 
            margin-bottom: 2rem; flex-wrap: wrap;
        }}
        .stat {{ 
            background: rgba(255,255,255,0.1); padding: 1rem 2rem; 
            border-radius: 12px; text-align: center;
        }}
        .stat-number {{ font-size: 2rem; font-weight: bold; color: #4299e1; }}
        .timeline {{ position: relative; padding-left: 30px; }}
        .timeline::before {{
            content: ''; position: absolute; left: 10px; top: 0;
            height: 100%; width: 3px; background: #4299e1;
        }}
        .date-group {{ margin-bottom: 2rem; }}
        .date-header {{
            font-size: 1.2rem; font-weight: bold; margin-bottom: 1rem;
            color: #4299e1; position: relative;
        }}
        .date-header::before {{
            content: ''; position: absolute; left: -25px; top: 5px;
            width: 12px; height: 12px; border-radius: 50%;
            background: #4299e1; border: 3px solid #1a1a2e;
        }}
        .event {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px; padding: 1rem;
            margin-bottom: 0.5rem; transition: all 0.2s;
            border-left: 3px solid transparent;
        }}
        .event:hover {{
            background: rgba(255,255,255,0.1);
            border-left-color: #4299e1;
            transform: translateX(5px);
        }}
        .event-title {{ font-weight: 500; margin-bottom: 0.5rem; }}
        .event-title a {{ color: #e2e8f0; text-decoration: none; }}
        .event-title a:hover {{ color: #4299e1; }}
        .event-meta {{ font-size: 0.85rem; color: #a0aec0; }}
        .event-meta span {{ margin-right: 1rem; }}
        .category {{ 
            background: #4299e1; color: white; padding: 2px 8px; 
            border-radius: 4px; font-size: 0.75rem;
        }}
        .filter {{ margin-bottom: 2rem; text-align: center; }}
        .filter input {{
            padding: 0.75rem 1.5rem; border-radius: 25px;
            border: none; width: 100%; max-width: 400px;
            background: rgba(255,255,255,0.1); color: white;
        }}
        .filter input::placeholder {{ color: #a0aec0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗞️ {title}</h1>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{len(events)}</div>
                <div>Events</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(grouped)}</div>
                <div>Days</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(set(e['source'] for e in events))}</div>
                <div>Sources</div>
            </div>
        </div>
        
        <div class="filter">
            <input type="text" id="search" placeholder="🔍 Filter events..." onkeyup="filterEvents()">
        </div>
        
        <div class="timeline" id="timeline">
"""
        
        for date, day_events in grouped.items():
            html += f'<div class="date-group" data-date="{date}">\n'
            html += f'<div class="date-header">📅 {date}</div>\n'
            
            for event in day_events[:10]:  # Limit per day
                category = event.get("category", "News")[:20]
                title = event["title"][:100]
                
                html += f'''
                <div class="event" data-text="{title.lower()} {category.lower()} {event['source'].lower()}">
                    <div class="event-title">
                        <a href="{event['url']}" target="_blank">{title}</a>
                    </div>
                    <div class="event-meta">
                        <span class="category">{category}</span>
                        <span>📰 {event['source']}</span>
                        <span>⏰ {event['date'][11:16]}</span>
                    </div>
                </div>
'''
            
            html += '</div>\n'
        
        html += """
        </div>
    </div>
    
    <script>
        function filterEvents() {
            const query = document.getElementById('search').value.toLowerCase();
            const events = document.querySelectorAll('.event');
            
            events.forEach(event => {
                const text = event.dataset.text;
                event.style.display = text.includes(query) ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>
"""
        return html
    
    def generate(self, days: int = 30, topic: str = None) -> str:
        """Generate timeline and save."""
        events = self.get_events(days=days, topic=topic)
        
        if not events:
            print("❌ No events found")
            return ""
        
        title = f"{topic.title()} Timeline" if topic else "News Timeline"
        html = self.generate_html(events, title)
        
        filename = f"timeline_{topic or 'all'}_{datetime.now().strftime('%Y%m%d')}.html"
        path = OUTPUT_DIR / filename
        path.write_text(html)
        
        print(f"✅ Generated timeline: {path}")
        print(f"   {len(events)} events from {len(self.group_by_date(events))} days")
        
        return str(path)
    
    def generate_json_api(self, days: int = 30) -> str:
        """Generate JSON for frontend consumption."""
        events = self.get_events(days=days)
        grouped = self.group_by_date(events)
        
        api_data = {
            "generated_at": datetime.now().isoformat(),
            "total_events": len(events),
            "total_days": len(grouped),
            "timeline": grouped
        }
        
        path = OUTPUT_DIR / "api.json"
        path.write_text(json.dumps(api_data, indent=2, ensure_ascii=False))
        
        return str(path)
    
    def serve(self, port: int = 8080):
        """Serve timeline via HTTP."""
        # Generate first
        self.generate()
        self.generate_json_api()
        
        os.chdir(OUTPUT_DIR)
        
        handler = http.server.SimpleHTTPRequestHandler
        
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌐 Serving timeline at http://localhost:{port}")
            print("   Press Ctrl+C to stop")
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n👋 Stopping server")


def main():
    parser = argparse.ArgumentParser(description="News timeline generator")
    parser.add_argument("--generate", action="store_true", help="Generate timeline")
    parser.add_argument("--topic", help="Filter by topic")
    parser.add_argument("--days", type=int, default=30, help="Days to include")
    parser.add_argument("--serve", action="store_true", help="Start server")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--json", action="store_true", help="Generate JSON API")
    
    args = parser.parse_args()
    
    timeline = NewsTimeline()
    
    if args.generate:
        timeline.generate(days=args.days, topic=args.topic)
    elif args.json:
        timeline.generate_json_api(days=args.days)
    elif args.serve:
        timeline.serve(args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
