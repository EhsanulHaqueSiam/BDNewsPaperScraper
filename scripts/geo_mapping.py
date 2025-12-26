#!/usr/bin/env python3
"""
Geographical News Mapping
==========================
Plot news articles on Bangladesh map by location mentions.

Features:
    - Extract location mentions from articles
    - Geocode locations to coordinates
    - Generate interactive maps
    - Heatmap of news concentration

Usage:
    python geo_mapping.py --generate          # Generate map
    python geo_mapping.py --heatmap           # Heatmap view
    python geo_mapping.py --serve             # Serve map
"""

import argparse
import sqlite3
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
OUTPUT_DIR = Path(__file__).parent / "maps"

# Bangladesh locations with coordinates
BANGLADESH_LOCATIONS = {
    # Divisions
    "dhaka": (23.8103, 90.4125),
    "chittagong": (22.3569, 91.7832),
    "chattogram": (22.3569, 91.7832),
    "rajshahi": (24.3745, 88.6042),
    "khulna": (22.8456, 89.5403),
    "sylhet": (24.8949, 91.8687),
    "barisal": (22.7010, 90.3535),
    "barishal": (22.7010, 90.3535),
    "rangpur": (25.7439, 89.2752),
    "mymensingh": (24.7471, 90.4203),
    
    # Major cities
    "comilla": (23.4607, 91.1809),
    "cumilla": (23.4607, 91.1809),
    "gazipur": (23.9999, 90.4203),
    "narayanganj": (23.6238, 90.5000),
    "bogra": (24.8510, 89.3697),
    "bogura": (24.8510, 89.3697),
    "jessore": (23.1634, 89.2182),
    "jashore": (23.1634, 89.2182),
    "dinajpur": (25.6217, 88.6354),
    "tangail": (24.2513, 89.9167),
    "brahmanbaria": (23.9608, 91.1115),
    "cox's bazar": (21.4272, 92.0058),
    "coxs bazar": (21.4272, 92.0058),
    "coxsbazar": (21.4272, 92.0058),
    "narsingdi": (23.9322, 90.7151),
    "faridpur": (23.6070, 89.8429),
    "savar": (23.8583, 90.2667),
    "tongi": (23.8783, 90.4058),
    "manikganj": (23.8644, 90.0047),
    "munshiganj": (23.5422, 90.5305),
    "chandpur": (23.2333, 90.6500),
    "habiganj": (24.3750, 91.4167),
    "moulvibazar": (24.4833, 91.7667),
    "sunamganj": (25.0667, 91.4000),
    "netrokona": (24.8833, 90.7333),
    "jamalpur": (24.9300, 89.9500),
    "sherpur": (25.0167, 90.0167),
    "feni": (23.0167, 91.4000),
    "noakhali": (22.8333, 91.1000),
    "lakshmipur": (22.9500, 90.8167),
    "patuakhali": (22.3500, 90.3500),
    "bhola": (22.6833, 90.6500),
    "jhalokati": (22.6500, 90.2000),
    "barguna": (22.1500, 90.1167),
    "pirojpur": (22.5833, 89.9667),
    "satkhira": (22.7167, 89.0667),
    "narail": (23.1667, 89.5000),
    "magura": (23.4833, 89.4333),
    "meherpur": (23.7667, 88.6333),
    "chuadanga": (23.6500, 88.8500),
    "kushtia": (23.9000, 89.1200),
    "jhenaidah": (23.5500, 89.1667),
    "natore": (24.4167, 89.0000),
    "chapainawabganj": (24.6000, 88.2667),
    "naogaon": (24.8000, 88.9500),
    "joypurhat": (25.0833, 89.0167),
    "gaibandha": (25.3333, 89.5333),
    "kurigram": (25.8000, 89.6333),
    "nilphamari": (25.9333, 88.8500),
    "lalmonirhat": (25.9167, 89.4333),
    "thakurgaon": (26.0333, 88.4667),
    "panchagarh": (26.3333, 88.5500),
    "bandarban": (22.1953, 92.2184),
    "rangamati": (22.6333, 92.2000),
    "khagrachhari": (23.1167, 91.9500),
    
    # General terms
    "bangladesh": (23.6850, 90.3563),
    "capital": (23.8103, 90.4125),
}


class GeoMapper:
    """Map news articles geographically."""
    
    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
        self.location_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(loc) for loc in BANGLADESH_LOCATIONS.keys()) + r')\b',
            re.IGNORECASE
        )
    
    def extract_locations(self, text: str) -> List[str]:
        """Extract location mentions from text."""
        if not text:
            return []
        
        matches = self.location_pattern.findall(text.lower())
        return list(set(matches))
    
    def get_articles_with_locations(self, days: int = 30, limit: int = 1000) -> List[Dict]:
        """Get articles and extract locations."""
        if not DB_PATH.exists():
            return []
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = conn.execute("""
            SELECT id, headline, paper_name, category, url, scraped_at
            FROM articles WHERE scraped_at >= ?
            ORDER BY scraped_at DESC LIMIT ?
        """, (cutoff, limit))
        
        articles = []
        for row in cursor.fetchall():
            locations = self.extract_locations(row["headline"])
            if locations:
                articles.append({
                    "id": row["id"],
                    "headline": row["headline"],
                    "paper_name": row["paper_name"],
                    "category": row["category"],
                    "url": row["url"],
                    "locations": locations,
                    "date": row["scraped_at"][:10]
                })
        
        conn.close()
        return articles
    
    def get_location_stats(self, articles: List[Dict]) -> Dict[str, int]:
        """Count articles per location."""
        counter = Counter()
        for article in articles:
            for loc in article["locations"]:
                counter[loc] += 1
        return dict(counter.most_common(50))
    
    def generate_map_html(self, articles: List[Dict]) -> str:
        """Generate interactive map HTML."""
        location_stats = self.get_location_stats(articles)
        
        # Group articles by location
        by_location = defaultdict(list)
        for article in articles:
            for loc in article["locations"]:
                by_location[loc].append(article)
        
        # Generate markers
        markers_js = []
        for loc, count in location_stats.items():
            if loc in BANGLADESH_LOCATIONS:
                lat, lon = BANGLADESH_LOCATIONS[loc]
                loc_articles = by_location[loc][:5]  # Top 5 articles
                
                popup_content = f"<b>{loc.title()}</b><br>{count} articles<br><br>"
                for a in loc_articles:
                    popup_content += f"<a href='{a['url']}' target='_blank'>{a['headline'][:50]}...</a><br>"
                
                # Size based on count
                radius = min(5 + count * 2, 30)
                
                markers_js.append(f"""
                    L.circleMarker([{lat}, {lon}], {{
                        radius: {radius},
                        fillColor: '#667eea',
                        color: '#fff',
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.7
                    }}).addTo(map).bindPopup(`{popup_content}`);
                """)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD News Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 0; font-family: system-ui; }}
        #map {{ height: 100vh; width: 100%; }}
        .info {{
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.8); color: white;
            padding: 15px; border-radius: 8px; z-index: 1000;
        }}
        .legend {{ position: absolute; bottom: 30px; left: 10px; background: white; padding: 10px; border-radius: 8px; z-index: 1000; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="info">
        <h3>🗺️ BD News Map</h3>
        <p>{len(articles)} articles</p>
        <p>{len(location_stats)} locations</p>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([23.8, 90.4], 7);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>'
        }}).addTo(map);
        
        {chr(10).join(markers_js)}
    </script>
</body>
</html>"""
        return html
    
    def generate_heatmap_html(self, articles: List[Dict]) -> str:
        """Generate heatmap visualization."""
        location_stats = self.get_location_stats(articles)
        
        # Build heat data
        heat_data = []
        max_count = max(location_stats.values()) if location_stats else 1
        
        for loc, count in location_stats.items():
            if loc in BANGLADESH_LOCATIONS:
                lat, lon = BANGLADESH_LOCATIONS[loc]
                intensity = count / max_count
                heat_data.append([lat, lon, intensity])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>BD News Heatmap</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <style>
        body {{ margin: 0; }}
        #map {{ height: 100vh; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map('map').setView([23.8, 90.4], 7);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
        
        const heat = L.heatLayer({json.dumps(heat_data)}, {{
            radius: 25,
            blur: 15,
            maxZoom: 10,
            gradient: {{0.4: 'blue', 0.65: 'lime', 1: 'red'}}
        }}).addTo(map);
    </script>
</body>
</html>"""
        return html
    
    def generate(self, days: int = 30, heatmap: bool = False) -> str:
        """Generate map and save."""
        articles = self.get_articles_with_locations(days)
        
        if not articles:
            print("❌ No articles with location data")
            return ""
        
        if heatmap:
            html = self.generate_heatmap_html(articles)
            filename = "heatmap.html"
        else:
            html = self.generate_map_html(articles)
            filename = "map.html"
        
        path = OUTPUT_DIR / filename
        path.write_text(html)
        
        stats = self.get_location_stats(articles)
        print(f"✅ Generated {filename}")
        print(f"   {len(articles)} articles, {len(stats)} locations")
        print(f"   Top: {', '.join(list(stats.keys())[:5])}")
        
        return str(path)
    
    def generate_json_api(self, days: int = 30) -> str:
        """Generate JSON for API consumption."""
        articles = self.get_articles_with_locations(days)
        stats = self.get_location_stats(articles)
        
        api_data = {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(articles),
            "locations": {
                loc: {
                    "count": count,
                    "coordinates": BANGLADESH_LOCATIONS.get(loc)
                }
                for loc, count in stats.items()
            }
        }
        
        path = OUTPUT_DIR / "geo_api.json"
        path.write_text(json.dumps(api_data, indent=2))
        return str(path)


def main():
    parser = argparse.ArgumentParser(description="Geographical news mapping")
    parser.add_argument("--generate", action="store_true", help="Generate map")
    parser.add_argument("--heatmap", action="store_true", help="Generate heatmap")
    parser.add_argument("--days", type=int, default=30, help="Days to include")
    parser.add_argument("--json", action="store_true", help="Generate JSON API")
    
    args = parser.parse_args()
    
    mapper = GeoMapper()
    
    if args.heatmap:
        mapper.generate(days=args.days, heatmap=True)
    elif args.generate:
        mapper.generate(days=args.days)
    elif args.json:
        mapper.generate_json_api(days=args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
