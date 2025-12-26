"""
BDNewsPaper CLI Module
======================
Command-line interface for running newspaper scrapers.
"""

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from BDNewsPaper.config import (
    SPIDER_CONFIGS,
    DEFAULT_START_DATE,
    get_default_end_date,
    list_available_spiders,
)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog='bdnews',
        description='Scrape Bangladeshi newspapers for news articles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all newspapers with default settings
  bdnews scrape

  # Scrape specific newspapers
  bdnews scrape --newspapers prothomalo dailysun

  # Scrape with date range
  bdnews scrape --from 2024-12-01 --to 2024-12-25

  # Scrape with category filter
  bdnews scrape --newspapers prothomalo --categories Bangladesh Sports

  # Search for specific keywords (API search for supported spiders)
  bdnews scrape --newspapers prothomalo --search "Sheikh Hasina"

  # Search with multiple keywords (OR logic)
  bdnews scrape --newspapers prothomalo --search "BNP,election"

  # List available spiders and their capabilities
  bdnews list
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Run newspaper scrapers')
    scrape_parser.add_argument(
        '--newspapers', '-n',
        nargs='+',
        choices=list_available_spiders(),
        default=None,
        help='Newspapers to scrape (default: all)'
    )
    scrape_parser.add_argument(
        '--from', '-f',
        dest='start_date',
        default=DEFAULT_START_DATE,
        help=f'Start date (YYYY-MM-DD, default: {DEFAULT_START_DATE})'
    )
    scrape_parser.add_argument(
        '--to', '-t',
        dest='end_date',
        default='today',
        help='End date (YYYY-MM-DD or "today", default: today)'
    )
    scrape_parser.add_argument(
        '--categories', '-c',
        nargs='+',
        default=None,
        help='Categories to filter (spider-specific)'
    )
    scrape_parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Maximum pages to scrape per category (default: 50)'
    )
    scrape_parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output file (JSON/CSV based on extension)'
    )
    scrape_parser.add_argument(
        '--db-path',
        default='news_articles.db',
        help='SQLite database path (default: news_articles.db)'
    )
    scrape_parser.add_argument(
        '--search', '-s',
        default=None,
        help='Search query/keywords to filter articles (comma-separated for OR logic)'
    )

    # List command
    list_parser = subparsers.add_parser('list', help='List available spiders')
    list_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed spider information'
    )

    return parser


def list_spiders(verbose: bool = False) -> None:
    """List available spiders and their capabilities."""
    print("\nAvailable Newspaper Spiders:")
    print("=" * 60)
    
    for name, config in SPIDER_CONFIGS.items():
        api_status = "✅ API" if config.uses_api else "❌ HTML"
        date_filter = "✅" if config.supports_api_date_filter else "⚠️"
        cat_filter = "✅" if config.supports_api_category_filter else "⚠️"
        
        print(f"\n{config.paper_name} ({name})")
        print(f"  Scraping: {api_status}")
        print(f"  Date Filter: {date_filter}")
        print(f"  Category Filter: {cat_filter}")
        
        if verbose:
            print(f"  Language: {config.language}")
            print(f"  Domains: {', '.join(config.allowed_domains)}")
            print(f"  Categories: {', '.join(config.default_categories[:5])}...")
            if hasattr(config, 'supports_keyword_search') and config.supports_keyword_search:
                print(f"  Search: ✅ API-level search supported")


def run_scrapers(
    newspapers: Optional[List[str]] = None,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = 'today',
    categories: Optional[List[str]] = None,
    max_pages: int = 50,
    output: Optional[str] = None,
    db_path: str = 'news_articles.db',
    search_query: Optional[str] = None
) -> None:
    """Run newspaper scrapers with given parameters."""
    
    if end_date.lower() == 'today':
        end_date = get_default_end_date()
    
    if newspapers is None:
        newspapers = list_available_spiders()
    
    print(f"\nRunning scrapers:")
    print(f"  Newspapers: {', '.join(newspapers)}")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Max pages: {max_pages}")
    if categories:
        print(f"  Categories: {', '.join(categories)}")
    if search_query:
        print(f"  Search query: {search_query}")
    print()
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Configure output if specified
    if output:
        if output.endswith('.json'):
            settings['FEEDS'] = {output: {'format': 'json'}}
        elif output.endswith('.csv'):
            settings['FEEDS'] = {output: {'format': 'csv'}}
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add spiders
    for spider_name in newspapers:
        spider_kwargs = {
            'start_date': start_date,
            'end_date': end_date,
            'max_pages': max_pages,
            'db_path': db_path,
        }
        
        if categories:
            spider_kwargs['categories'] = ','.join(categories)
        
        if search_query:
            spider_kwargs['search_query'] = search_query
        
        # Import spider dynamically
        try:
            process.crawl(spider_name, **spider_kwargs)
            print(f"  Added spider: {spider_name}")
        except Exception as e:
            print(f"  Error adding spider {spider_name}: {e}")
    
    print("\nStarting scrape...\n")
    process.start()
    print("\nScraping complete!")


def main() -> int:
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == 'list':
        list_spiders(verbose=args.verbose)
        return 0
    
    if args.command == 'scrape':
        run_scrapers(
            newspapers=args.newspapers,
            start_date=args.start_date,
            end_date=args.end_date,
            categories=args.categories,
            max_pages=args.max_pages,
            output=args.output,
            db_path=args.db_path,
            search_query=args.search,
        )
        return 0
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
