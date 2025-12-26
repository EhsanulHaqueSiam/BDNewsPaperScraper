#!/usr/bin/env python3
"""
Hugging Face Dataset Uploader
==============================
Upload scraped news data to Hugging Face Hub for public sharing.

Features:
    - Export to Hugging Face dataset format
    - Automatic dataset card generation
    - Version control with commits
    - Privacy options

Setup:
    pip install datasets huggingface_hub
    huggingface-cli login

Usage:
    python huggingface_upload.py --upload           # Upload dataset
    python huggingface_upload.py --export           # Export only (no upload)
    python huggingface_upload.py --preview          # Preview data
"""

import argparse
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import os

DB_PATH = Path(__file__).resolve().parent.parent / "news_articles.db"
EXPORT_DIR = Path(__file__).parent / "dataset_export"

# Try to import HF libraries
try:
    from datasets import Dataset, DatasetDict
    from huggingface_hub import HfApi, create_repo
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class HuggingFaceUploader:
    """Upload news dataset to Hugging Face Hub."""
    
    def __init__(self, repo_name: str = None):
        self.repo_name = repo_name or os.getenv("HF_REPO_NAME", "bd-news-dataset")
        self.username = os.getenv("HF_USERNAME", "")
        EXPORT_DIR.mkdir(exist_ok=True)
    
    def load_articles(self, limit: int = None) -> List[Dict]:
        """Load all articles from database."""
        if not DB_PATH.exists():
            print("❌ Database not found")
            return []
        
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
        
        articles = [dict(row) for row in conn.execute(query).fetchall()]
        conn.close()
        
        return articles
    
    def export_to_jsonl(self, articles: List[Dict]) -> str:
        """Export articles to JSONL format."""
        output_path = EXPORT_DIR / "data.jsonl"
        
        with open(output_path, "w", encoding="utf-8") as f:
            for article in articles:
                # Clean up for export
                clean_article = {
                    "id": article["id"],
                    "url": article["url"],
                    "newspaper": article["paper_name"],
                    "headline": article["headline"],
                    "content": article.get("article_body") or "",
                    "category": article.get("category") or "",
                    "author": article.get("author") or "",
                    "date": article.get("publication_date") or "",
                    "language": article.get("source_language") or "en",
                    "word_count": article.get("word_count") or 0,
                }
                f.write(json.dumps(clean_article, ensure_ascii=False) + "\n")
        
        print(f"✅ Exported {len(articles)} articles to {output_path}")
        return str(output_path)
    
    def generate_dataset_card(self, articles: List[Dict]) -> str:
        """Generate README for the dataset."""
        # Get stats
        papers = list(set(a["paper_name"] for a in articles))
        categories = list(set(a.get("category") for a in articles if a.get("category")))
        
        date_range = {
            "earliest": min((a.get("publication_date") or "")[:10] for a in articles if a.get("publication_date")),
            "latest": max((a.get("publication_date") or "")[:10] for a in articles if a.get("publication_date"))
        }
        
        card = f"""---
license: mit
language:
  - en
  - bn
task_categories:
  - text-classification
  - summarization
  - text-generation
tags:
  - news
  - bangladesh
  - newspapers
  - nlp
size_categories:
  - {"10K<n<100K" if len(articles) > 10000 else "1K<n<10K" if len(articles) > 1000 else "n<1K"}
---

# 🗞️ BD News Dataset

A comprehensive collection of news articles from major Bangladeshi newspapers.

## Dataset Description

This dataset contains **{len(articles):,}** news articles scraped from **{len(papers)}** Bangladeshi newspapers, covering various categories including politics, business, sports, entertainment, and more.

### Supported Newspapers

{chr(10).join(f"- {p}" for p in sorted(papers)[:20])}
{"..." if len(papers) > 20 else ""}

### Categories

{chr(10).join(f"- {c}" for c in sorted(categories)[:15] if c)}

### Date Range

- **Earliest**: {date_range['earliest']}
- **Latest**: {date_range['latest']}

## Dataset Structure

```python
{{
    "id": int,
    "url": str,
    "newspaper": str,
    "headline": str,
    "content": str,
    "category": str,
    "author": str,
    "date": str,
    "language": str,  # "en" or "bn"
    "word_count": int
}}
```

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("{self.username}/{self.repo_name}")

# Access articles
for article in dataset["train"]:
    print(article["headline"])
```

## License

This dataset is provided under the MIT License. The original content is owned by the respective newspapers.

## Acknowledgements

- Data collected using [BDNewsPaperScraper](https://github.com/EhsanulHaqueSiam/BDNewsPaperScraper)
- Thanks to all the Bangladeshi news outlets for providing valuable content

## Citation

```bibtex
@misc{{bd-news-dataset,
  author = {{BDNewsPaper Team}},
  title = {{BD News Dataset}},
  year = {{2024}},
  publisher = {{Hugging Face}},
  howpublished = {{\\url{{https://huggingface.co/datasets/{self.username}/{self.repo_name}}}}}
}}
```
"""
        
        readme_path = EXPORT_DIR / "README.md"
        readme_path.write_text(card)
        print(f"✅ Generated dataset card: {readme_path}")
        
        return card
    
    def upload_to_hub(self, articles: List[Dict], private: bool = False) -> bool:
        """Upload dataset to Hugging Face Hub."""
        if not HF_AVAILABLE:
            print("❌ Install: pip install datasets huggingface_hub")
            return False
        
        if not self.username:
            print("❌ Set HF_USERNAME environment variable")
            print("   Or run: huggingface-cli login")
            return False
        
        try:
            # Export data
            jsonl_path = self.export_to_jsonl(articles)
            self.generate_dataset_card(articles)
            
            # Create dataset
            dataset = Dataset.from_json(jsonl_path)
            
            # Split into train/test
            split_dataset = dataset.train_test_split(test_size=0.1)
            
            # Upload
            repo_id = f"{self.username}/{self.repo_name}"
            print(f"📤 Uploading to {repo_id}...")
            
            split_dataset.push_to_hub(
                repo_id,
                private=private,
                commit_message=f"Update dataset: {len(articles)} articles"
            )
            
            print(f"✅ Dataset uploaded: https://huggingface.co/datasets/{repo_id}")
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    def preview(self, limit: int = 5):
        """Preview dataset."""
        articles = self.load_articles(limit=limit)
        
        print(f"\n📊 Dataset Preview ({len(articles)} samples)\n")
        
        for a in articles:
            print(f"📰 {a['paper_name']}")
            print(f"   {a['headline'][:80]}...")
            print(f"   Category: {a.get('category', 'N/A')} | Date: {a.get('publication_date', 'N/A')[:10]}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Upload to Hugging Face")
    parser.add_argument("--upload", action="store_true", help="Upload dataset")
    parser.add_argument("--export", action="store_true", help="Export only")
    parser.add_argument("--preview", action="store_true", help="Preview data")
    parser.add_argument("--limit", type=int, help="Limit articles")
    parser.add_argument("--private", action="store_true", help="Make private")
    parser.add_argument("--repo", default="bd-news-dataset", help="Repository name")
    
    args = parser.parse_args()
    
    uploader = HuggingFaceUploader(repo_name=args.repo)
    
    if args.preview:
        uploader.preview(args.limit or 5)
    elif args.export:
        articles = uploader.load_articles(limit=args.limit)
        uploader.export_to_jsonl(articles)
        uploader.generate_dataset_card(articles)
    elif args.upload:
        articles = uploader.load_articles(limit=args.limit)
        uploader.upload_to_hub(articles, private=args.private)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
