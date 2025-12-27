#!/usr/bin/env python3
"""
Parallel Spider Tester
======================
Runs all available spiders in parallel to verify they are working correctly.
Limits execution to 2 items per spider.
"""

import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
import re

# Default Configuration
DEFAULT_MAX_WORKERS = 8
DEFAULT_ITEM_LIMIT = 2
DEFAULT_TIMEOUT_SECONDS = 60
TEST_DB_PATH = "test_results.db"

# Global config (set by argparse)
MAX_WORKERS = DEFAULT_MAX_WORKERS
ITEM_LIMIT = DEFAULT_ITEM_LIMIT
TIMEOUT_SECONDS = DEFAULT_TIMEOUT_SECONDS

def get_spiders() -> List[str]:
    """Get list of available spiders."""
    try:
        # Use direct path to scrapy to avoid uv locking
        scrapy_path = Path(".venv/bin/scrapy").resolve()
        if not scrapy_path.exists():
            # Fallback for when not running in root or venv not found
            cmd = ["scrapy", "list"]
        else:
            cmd = [str(scrapy_path), "list"]
            
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        # Filter out non-spider lines (like logs)
        spiders = [
            line.strip() 
            for line in result.stdout.splitlines() 
            if line.strip() and not line.startswith("Bytecode")
        ]
        return spiders
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to list spiders: {e}")
        return []

def test_spider(spider_name: str) -> Dict:
    """Run a single spider test."""
    start_time = time.time()
    
    # Use direct path to scrapy to avoid uv locking
    scrapy_path = Path(".venv/bin/scrapy").resolve()
    if not scrapy_path.exists():
        cmd = ["scrapy", "crawl", spider_name]
    else:
        cmd = [str(scrapy_path), "crawl", spider_name]
        
    cmd.extend([
        "-s", f"CLOSESPIDER_ITEMCOUNT={ITEM_LIMIT}",
        "-s", "LOG_LEVEL=INFO",
        "-s", "DATABASE_PATH=:memory:",
        "-s", "TELNETCONSOLE_ENABLED=0",
        "-s", "HTTPCACHE_ENABLED=False",
        "-s", "LOG_FILE="
    ])
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS
        )
        duration = time.time() - start_time
        
        # Check output for scraped item count
        item_count = 0
        if "'item_scraped_count':" in process.stderr:
            match = re.search(r"'item_scraped_count': (\d+)", process.stderr)
            if match:
                item_count = int(match.group(1))
        
        # Determine status
        if process.returncode != 0:
            status = "CRASHED"
            details = process.stderr[-200:] if process.stderr else "Unknown error"
        elif item_count > 0:
            status = "PASSED"
            details = f"{item_count} items"
        else:
            status = "NO_ITEMS"
            details = "0 items scraped"
            
        return {
            "name": spider_name,
            "status": status,
            "duration": duration,
            "details": details,
            "item_count": item_count
        }
        
    except subprocess.TimeoutExpired:
        return {
            "name": spider_name,
            "status": "TIMEOUT",
            "duration": TIMEOUT_SECONDS,
            "details": "Exceeded 60s limit",
            "item_count": 0
        }
    except Exception as e:
        return {
            "name": spider_name,
            "status": "ERROR",
            "duration": time.time() - start_time,
            "details": str(e),
            "item_count": 0
        }

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parallel Spider Tester - runs all spiders to verify they work correctly"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout in seconds per spider (default: {DEFAULT_TIMEOUT_SECONDS})"
    )
    parser.add_argument(
        "--max-items", "-m",
        type=int,
        default=DEFAULT_ITEM_LIMIT,
        help=f"Maximum items to scrape per spider (default: {DEFAULT_ITEM_LIMIT})"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_MAX_WORKERS})"
    )
    parser.add_argument(
        "--spider", "-s",
        type=str,
        default=None,
        help="Test only a specific spider by name"
    )
    return parser.parse_args()

def main():
    global MAX_WORKERS, ITEM_LIMIT, TIMEOUT_SECONDS
    
    args = parse_args()
    MAX_WORKERS = args.workers
    ITEM_LIMIT = args.max_items
    TIMEOUT_SECONDS = args.timeout
    
    print(f"🕷️  Starting parallel spider test (Workers: {MAX_WORKERS}, Timeout: {TIMEOUT_SECONDS}s, Max Items: {ITEM_LIMIT})")
    print("=" * 60)
    
    # Clean up previous test DB
    Path(TEST_DB_PATH).unlink(missing_ok=True)
    
    spiders = get_spiders()
    if not spiders:
        print("No spiders found!")
        return
    
    # Filter to specific spider if requested
    if args.spider:
        if args.spider not in spiders:
            print(f"❌ Spider '{args.spider}' not found!")
            print(f"Available spiders: {', '.join(spiders[:10])}...")
            return
        spiders = [args.spider]
    
    print(f"Found {len(spiders)} spider(s). Running tests...")
    
    results = {
        "PASSED": [],
        "NO_ITEMS": [],
        "TIMEOUT": [],
        "CRASHED": [],
        "ERROR": []
    }
    
    completed = 0
    total = len(spiders)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_spider = {
            executor.submit(test_spider, spider): spider 
            for spider in spiders
        }
        
        for future in as_completed(future_to_spider):
            result = future.result()
            completed += 1
            
            # Store result
            results[result["status"]].append(result)
            
            # Print progress
            symbol = {
                "PASSED": "✅",
                "NO_ITEMS": "⚠️ ",
                "TIMEOUT": "⏰",
                "CRASHED": "❌",
                "ERROR": "🔥"
            }.get(result["status"], "❓")
            
            print(f"[{completed:02d}/{total:02d}] {symbol} {result['name']:<20} ({result['duration']:.1f}s) - {result['details']}")
            
    print("\n" + "=" * 60)
    print("🎉 Testing Complete!")
    print(f"✅ PASSED:   {len(results['PASSED'])}")
    print(f"⚠️  NO ITEMS: {len(results['NO_ITEMS'])}")
    print(f"⏰ TIMEOUT:  {len(results['TIMEOUT'])}")
    print(f"❌ CRASHED:  {len(results['CRASHED']) + len(results['ERROR'])}")
    
    if results['NO_ITEMS']:
        print("\n⚠️  Spiders with NO ITEMS:")
        for r in results['NO_ITEMS']:
            print(f"  - {r['name']}")
            
    if results['TIMEOUT']:
        print("\n⏰ Timed out spiders:")
        for r in results['TIMEOUT']:
            print(f"  - {r['name']}")
            
    if results['CRASHED'] or results['ERROR']:
        print("\n❌ Crashed/Error spiders:")
        for r in results['CRASHED'] + results['ERROR']:
            print(f"  - {r['name']}: {r['details'].splitlines()[-1] if r['details'] else 'Unknown'}")

    # Clean up
    Path(TEST_DB_PATH).unlink(missing_ok=True)

if __name__ == "__main__":
    main()
