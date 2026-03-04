#!/usr/bin/env python3
"""
Spider Diagnostic Script
========================
Identifies why spiders return 0 items by checking:
1. Start URL accessibility
2. Link discovery (CSS selectors)
3. Content extraction (article parsing)
"""

import sys
import subprocess
import json
from urllib.parse import urlparse
from typing import Dict, List, Tuple
import requests

# 26 NO_ITEMS spiders from test results
NO_ITEMS_SPIDERS = [
    "autonews",  # Needs URL argument
    "amadershomoy",
    "banglavision",
    "bonikbarta",
    "bssbangla",
    "comillarkagoj",
    "dailyinqilab",
    "ctgtimes",
    "dailysun",
    "dbcnews",
    "dhakacourier",
    "deshrupantor",
    "dwbangla",
    "ekattor",
    "generic_playwright",  # Needs URL argument
    "gramerkagoj",
    "narayanganjtimes",
    "manabzamin",
    "news24bd",
    "rtvonline",
    "somoyertv",
    "thedhakatimes",
    "unb",
    "unbbangla",
    "theindependent",
    "voabangla",
]


def check_url_accessible(url: str, timeout: int = 10) -> Tuple[bool, int, str]:
    """Check if a URL is accessible."""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            },
            allow_redirects=True
        )
        return True, response.status_code, f"Size: {len(response.content)} bytes"
    except requests.RequestException as e:
        return False, 0, str(e)


def get_spider_start_url(spider_name: str) -> str:
    """Get start URL for a spider by parsing its source."""
    import os
    spider_file = f"BDNewsPaper/spiders/{spider_name}.py"
    
    if not os.path.exists(spider_file):
        return ""
    
    with open(spider_file) as f:
        content = f.read()
    
    # Try to find allowed_domains
    import re
    domain_match = re.search(r"allowed_domains\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if domain_match:
        domains = re.findall(r"['\"]([^'\"]+)['\"]", domain_match.group(1))
        if domains:
            return f"https://www.{domains[0]}/"
    
    return ""


def run_spider_quick_test(spider_name: str, timeout: int = 30) -> Dict:
    """Run a quick spider test."""
    cmd = [
        "uv", "run", "scrapy", "crawl", spider_name,
        "-s", f"CLOSESPIDER_TIMEOUT={timeout}",
        "-s", "CLOSESPIDER_ITEMCOUNT=3",
        "-s", "LOG_LEVEL=WARNING",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,
            cwd="."
        )
        
        # Count items scraped from output
        output = result.stdout + result.stderr
        items = 0
        if "Scraped" in output:
            import re
            match = re.search(r"'item_scraped_count': (\d+)", output)
            if match:
                items = int(match.group(1))
        
        return {
            "success": result.returncode == 0,
            "items": items,
            "error": result.stderr[-500:] if result.returncode != 0 else ""
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "items": 0, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "items": 0, "error": str(e)}


def diagnose_spider(spider_name: str) -> Dict:
    """Diagnose a single spider."""
    result = {
        "spider": spider_name,
        "url_accessible": False,
        "start_url": "",
        "status_code": 0,
        "items_scraped": 0,
        "diagnosis": "Unknown"
    }
    
    # Get start URL
    url = get_spider_start_url(spider_name)
    result["start_url"] = url
    
    if not url:
        result["diagnosis"] = "No start URL found"
        return result
    
    # Check URL accessibility
    accessible, status, msg = check_url_accessible(url)
    result["url_accessible"] = accessible
    result["status_code"] = status
    
    if not accessible:
        result["diagnosis"] = f"URL not accessible: {msg}"
        return result
    
    if status >= 400:
        result["diagnosis"] = f"HTTP error: {status}"
        return result
    
    # Quick spider test
    test_result = run_spider_quick_test(spider_name, timeout=45)
    result["items_scraped"] = test_result["items"]
    
    if test_result["items"] > 0:
        result["diagnosis"] = "WORKING"
    elif "Timeout" in test_result.get("error", ""):
        result["diagnosis"] = "Timeout - site too slow"
    else:
        result["diagnosis"] = "Selectors need update - no items extracted"
    
    return result


def main():
    """Run diagnostics on all NO_ITEMS spiders."""
    print("=" * 60)
    print("Spider Diagnostic Report")
    print("=" * 60)
    
    results = []
    
    # Skip spiders that need arguments
    skip_spiders = ["autonews", "generic_playwright"]
    
    for spider in NO_ITEMS_SPIDERS:
        if spider in skip_spiders:
            print(f"\n[SKIP] {spider} - requires URL argument")
            continue
        
        print(f"\n[{NO_ITEMS_SPIDERS.index(spider)+1}/{len(NO_ITEMS_SPIDERS)}] Diagnosing: {spider}")
        
        try:
            result = diagnose_spider(spider)
            results.append(result)
            
            status = "✅" if result["diagnosis"] == "WORKING" else "❌"
            print(f"  {status} {result['diagnosis']}")
            print(f"     URL: {result['start_url']}")
            print(f"     Status: {result['status_code']}, Items: {result['items_scraped']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    working = [r for r in results if r["diagnosis"] == "WORKING"]
    timeout = [r for r in results if "Timeout" in r["diagnosis"]]
    selector_issues = [r for r in results if "Selectors" in r["diagnosis"]]
    url_issues = [r for r in results if "URL" in r["diagnosis"] or "HTTP" in r["diagnosis"]]
    
    print(f"✅ Working: {len(working)}")
    print(f"⏰ Timeout: {len(timeout)}")
    print(f"🔧 Selector Issues: {len(selector_issues)}")
    print(f"🌐 URL Issues: {len(url_issues)}")
    
    # Save results
    with open("spider_diagnostic_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to spider_diagnostic_results.json")


if __name__ == "__main__":
    main()
