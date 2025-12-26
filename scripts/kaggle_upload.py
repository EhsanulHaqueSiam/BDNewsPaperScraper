#!/usr/bin/env python3
"""
Kaggle Dataset Publisher
=========================
Export and publish news dataset to Kaggle.

Setup:
    1. Create Kaggle account: https://www.kaggle.com
    2. Go to Account → Create API Token
    3. Place kaggle.json in ~/.kaggle/ or set KAGGLE_USERNAME and KAGGLE_KEY

Usage:
    python kaggle_upload.py --export        # Export dataset
    python kaggle_upload.py --upload        # Upload to Kaggle
    python kaggle_upload.py --update        # Update existing dataset
"""

import argparse
import os
import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import subprocess
import zipfile


DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
EXPORT_DIR = Path(__file__).parent / "kaggle_export"

KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME", "")
KAGGLE_KEY = os.getenv("KAGGLE_KEY", "")
DATASET_SLUG = os.getenv("KAGGLE_DATASET_SLUG", "bd-news-articles")


class KagglePublisher:
    """Publish dataset to Kaggle."""
    
    def __init__(self):
        self.export_dir = EXPORT_DIR
        self.export_dir.mkdir(exist_ok=True)
    
    def export_data(self, limit: int = None) -> Dict:
        """Export articles to CSV."""
        if not DB_PATH.exists():
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT 
                id, url, paper_name, headline, article_body,
                category, author, publication_date, 
                source_language, word_count, scraped_at
            FROM articles
            ORDER BY scraped_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = conn.execute(query)
        articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Export to CSV
        csv_path = self.export_dir / "articles.csv"
        
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            if articles:
                writer = csv.DictWriter(f, fieldnames=articles[0].keys())
                writer.writeheader()
                writer.writerows(articles)
        
        print(f"✅ Exported {len(articles)} articles to {csv_path}")
        
        # Create dataset metadata
        self._create_metadata(len(articles))
        
        return {"articles": len(articles), "path": str(csv_path)}
    
    def _create_metadata(self, article_count: int):
        """Create dataset-metadata.json for Kaggle."""
        metadata = {
            "title": "Bangladeshi News Articles Dataset",
            "id": f"{KAGGLE_USERNAME}/{DATASET_SLUG}",
            "licenses": [{"name": "CC0-1.0"}],
            "keywords": [
                "news",
                "bangladesh",
                "nlp",
                "text classification",
                "sentiment analysis"
            ],
            "resources": [
                {
                    "path": "articles.csv",
                    "description": f"News articles from Bangladeshi newspapers ({article_count:,} rows)"
                }
            ]
        }
        
        meta_path = self.export_dir / "dataset-metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2))
        
        # Create README
        readme = f"""# Bangladeshi News Articles Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

## Description

This dataset contains **{article_count:,}** news articles scraped from 75+ Bangladeshi newspapers.

## Content

- `articles.csv` - Main data file with all articles

### Columns

| Column | Description |
|--------|-------------|
| id | Unique article ID |
| url | Original article URL |
| paper_name | Newspaper name |
| headline | Article title |
| article_body | Full article text |
| category | News category |
| author | Article author |
| publication_date | Publication date |
| source_language | Language (en/bn) |
| word_count | Word count |
| scraped_at | Scrape timestamp |

## Use Cases

- Sentiment analysis
- Text classification
- Topic modeling
- Named entity recognition
- Language modeling for Bengali/English

## Source

Data collected using [BDNewsPaperScraper](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)

## License

CC0 1.0 Universal (Public Domain)

## Update Frequency

Weekly updates
"""
        
        (self.export_dir / "README.md").write_text(readme)
        print(f"✅ Created metadata and README")
    
    def upload(self, new: bool = True) -> bool:
        """Upload dataset to Kaggle."""
        try:
            import kaggle
        except ImportError:
            print("❌ Install: pip install kaggle")
            return False
        
        if not KAGGLE_USERNAME:
            print("❌ Set KAGGLE_USERNAME environment variable")
            return False
        
        # Export first
        result = self.export_data()
        if "error" in result:
            print(f"❌ {result['error']}")
            return False
        
        try:
            if new:
                # Create new dataset
                cmd = ["kaggle", "datasets", "create", "-p", str(self.export_dir)]
            else:
                # Update existing
                cmd = ["kaggle", "datasets", "version", "-p", str(self.export_dir), "-m", f"Update {datetime.now().strftime('%Y-%m-%d')}"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Dataset uploaded to Kaggle: https://www.kaggle.com/datasets/{KAGGLE_USERNAME}/{DATASET_SLUG}")
                return True
            else:
                print(f"❌ Upload failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def create_zip_archive(self) -> str:
        """Create zip archive for manual upload."""
        result = self.export_data()
        if "error" in result:
            return ""
        
        zip_path = self.export_dir / "dataset.zip"
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in self.export_dir.glob("*"):
                if file.suffix in [".csv", ".md", ".json"] and file.name != "dataset.zip":
                    zf.write(file, file.name)
        
        print(f"✅ Created zip archive: {zip_path}")
        return str(zip_path)


def main():
    parser = argparse.ArgumentParser(description="Kaggle dataset publisher")
    parser.add_argument("--export", action="store_true", help="Export data")
    parser.add_argument("--upload", action="store_true", help="Upload new dataset")
    parser.add_argument("--update", action="store_true", help="Update existing")
    parser.add_argument("--zip", action="store_true", help="Create zip archive")
    parser.add_argument("--limit", type=int, help="Limit articles")
    
    args = parser.parse_args()
    
    publisher = KagglePublisher()
    
    if args.export:
        publisher.export_data(args.limit)
    elif args.upload:
        publisher.upload(new=True)
    elif args.update:
        publisher.upload(new=False)
    elif args.zip:
        publisher.create_zip_archive()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
