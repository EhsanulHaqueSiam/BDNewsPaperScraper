#!/usr/bin/env python3
"""
Enhanced SQLite to Excel converter for BDNewsPaper scrapers.
Works with the shared database containing essential fields only.
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional


def get_database_info(db_file: str = "news_articles.db") -> Dict:
    """Get information about the shared database."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get total article count
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_count = cursor.fetchone()[0]
        
        # Get count by paper
        cursor.execute("SELECT paper_name, COUNT(*) FROM articles GROUP BY paper_name ORDER BY COUNT(*) DESC")
        papers = dict(cursor.fetchall())
        
        # Get date range
        cursor.execute("SELECT MIN(publication_date), MAX(publication_date) FROM articles WHERE publication_date IS NOT NULL")
        date_range = cursor.fetchone()
        
        conn.close()
        return {
            'total_articles': total_count,
            'papers': papers,
            'date_range': date_range,
            'database_file': db_file
        }
        
    except sqlite3.Error as e:
        return {'error': str(e)}


def export_to_excel(db_file: str = "news_articles.db", output_file: str = "news_articles.xlsx", 
                   paper_filter: str = None, limit: int = None) -> bool:
    """Export articles to Excel file."""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas and openpyxl are required for Excel export.")
        print("Install with: uv add pandas openpyxl")
        return False
    
    try:
        conn = sqlite3.connect(db_file)
        
        # Build query based on filters
        query = "SELECT url, paper_name, headline, article, publication_date, scraped_at FROM articles"
        params = []
        
        if paper_filter:
            query += " WHERE paper_name = ?"
            params.append(paper_filter)
        
        query += " ORDER BY scraped_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            print("No articles found matching the criteria")
            return False
        
        # Rename columns for better readability
        df.columns = ['URL', 'Paper Name', 'Headline', 'Article Content', 'Publication Date', 'Scraped At']
        
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        print(f"✓ Exported {len(df)} articles to {output_file}")
        if paper_filter:
            print(f"  Filter: {paper_filter} articles only")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Export error: {e}")
        return False


def export_to_csv(db_file: str = "news_articles.db", output_file: str = "news_articles.csv",
                 paper_filter: str = None, limit: int = None) -> bool:
    """Export articles to CSV file."""
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas is required for CSV export.")
        print("Install with: uv add pandas")
        return False
    
    try:
        conn = sqlite3.connect(db_file)
        
        # Build query based on filters
        query = "SELECT url, paper_name, headline, article, publication_date, scraped_at FROM articles"
        params = []
        
        if paper_filter:
            query += " WHERE paper_name = ?"
            params.append(paper_filter)
        
        query += " ORDER BY scraped_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            print("No articles found matching the criteria")
            return False
        
        # Rename columns for better readability
        df.columns = ['URL', 'Paper Name', 'Headline', 'Article Content', 'Publication Date', 'Scraped At']
        
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"✓ Exported {len(df)} articles to {output_file}")
        if paper_filter:
            print(f"  Filter: {paper_filter} articles only")
        return True
        
    except Exception as e:
        print(f"Export error: {e}")
        return False


def list_database():
    """List database information and available papers."""
    db_file = "news_articles.db"
    
    if not Path(db_file).exists():
        print(f"Database file '{db_file}' not found.")
        print("Run spiders first to create the database.")
        return
    
    print("Shared News Articles Database")
    print("=" * 40)
    
    info = get_database_info(db_file)
    if 'error' in info:
        print(f"Error: {info['error']}")
        return
    
    print(f"Database file: {info['database_file']}")
    print(f"Total articles: {info['total_articles']:,}")
    
    if info['date_range'][0] and info['date_range'][1]:
        print(f"Date range: {info['date_range'][0]} to {info['date_range'][1]}")
    
    print(f"\nArticles by newspaper:")
    print("-" * 30)
    for paper, count in info['papers'].items():
        print(f"  {paper}: {count:,} articles")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Export BDNewsPaper data from shared database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                                    # Show database info
  %(prog)s --output all_articles.xlsx               # Export all articles to Excel
  %(prog)s --paper prothomalo --format csv          # Export only ProthomAlo articles to CSV
  %(prog)s --paper dailysun --limit 100             # Export latest 100 Daily Sun articles
  %(prog)s --output recent.xlsx --limit 500         # Export latest 500 articles from all papers
        """
    )
    
    parser.add_argument('--list', action='store_true',
                       help='Show database information and article counts')
    
    parser.add_argument('--paper', 
                       help='Filter by specific newspaper (e.g., prothomalo, dailysun, ittefaq)')
    
    parser.add_argument('--output', default='news_articles.xlsx',
                       help='Output file path (default: news_articles.xlsx)')
    
    parser.add_argument('--format', choices=['excel', 'csv'], default='excel',
                       help='Output format (default: excel)')
    
    parser.add_argument('--limit', type=int,
                       help='Limit number of articles to export (most recent first)')
    
    args = parser.parse_args()
    
    # Show database information
    if args.list:
        list_database()
        return
    
    # Check if database exists
    db_file = "news_articles.db"
    if not Path(db_file).exists():
        print(f"Error: Database file '{db_file}' not found.")
        print("Run spiders first to create the database:")
        print("  uv run scrapy crawl prothomalo")
        print("  uv run scrapy crawl dailysun")
        print("  # etc...")
        sys.exit(1)
    
    # Validate paper filter
    if args.paper:
        info = get_database_info(db_file)
        available_papers = list(info.get('papers', {}).keys())
        if args.paper not in available_papers:
            print(f"Error: Paper '{args.paper}' not found in database.")
            if available_papers:
                print(f"Available papers: {', '.join(available_papers)}")
            else:
                print("No articles found in database.")
            sys.exit(1)
    
    # Determine output file extension
    if args.format == 'csv' and not args.output.endswith('.csv'):
        if args.output == 'news_articles.xlsx':  # Default was used
            args.output = 'news_articles.csv'
    
    # Perform export
    print(f"Exporting from {db_file} to {args.output}...")
    
    if args.format == 'csv':
        success = export_to_csv(db_file, args.output, args.paper, args.limit)
    else:
        success = export_to_excel(db_file, args.output, args.paper, args.limit)
    
    if success:
        print("✓ Export completed successfully!")
    else:
        print("✗ Export failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
