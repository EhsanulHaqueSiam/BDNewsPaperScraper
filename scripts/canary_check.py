#!/usr/bin/env python3
"""
Canary Health Check Script
==========================
Lightweight health check for all spiders before main scraping runs.

Features:
    - Hit homepage of each newspaper
    - Detect Cloudflare/bot protection challenges
    - Verify content loads (not empty HTML)
    - Output JSON/console report

Usage:
    python scripts/canary_check.py --papers prothomalo,thedailystar
    python scripts/canary_check.py --all --output health_report.json
    python scripts/canary_check.py --all --format json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    import requests
    HTTPX_AVAILABLE = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class HealthCheck:
    """Health check result for a single newspaper."""
    name: str
    url: str
    status: str = "unknown"  # healthy, unhealthy, cloudflare, timeout, error
    status_code: Optional[int] = None
    response_time_ms: float = 0.0
    content_length: int = 0
    has_cloudflare: bool = False
    has_content: bool = False
    error_message: str = ""
    checked_at: str = ""
    
    def is_healthy(self) -> bool:
        return self.status == "healthy"


@dataclass  
class HealthReport:
    """Full health report for all checked papers."""
    timestamp: str = ""
    total_checked: int = 0
    healthy: int = 0
    unhealthy: int = 0
    cloudflare_blocked: int = 0
    timeout: int = 0
    errors: int = 0
    checks: List[HealthCheck] = field(default_factory=list)
    
    def add_check(self, check: HealthCheck):
        self.checks.append(check)
        self.total_checked += 1
        if check.status == "healthy":
            self.healthy += 1
        elif check.status == "cloudflare":
            self.cloudflare_blocked += 1
            self.unhealthy += 1
        elif check.status == "timeout":
            self.timeout += 1
            self.unhealthy += 1
        elif check.status == "error":
            self.errors += 1
            self.unhealthy += 1
        else:
            self.unhealthy += 1
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_checked": self.total_checked,
                "healthy": self.healthy,
                "unhealthy": self.unhealthy,
                "cloudflare_blocked": self.cloudflare_blocked,
                "timeout": self.timeout,
                "errors": self.errors,
            },
            "checks": [asdict(c) for c in self.checks],
        }


# Newspaper URLs to check
NEWSPAPER_URLS = {
    "prothomalo": "https://en.prothomalo.com",
    "thedailystar": "https://www.thedailystar.net",
    "dailysun": "https://www.daily-sun.com",
    "bdnews24": "https://bdnews24.com",
    "dhakatribune": "https://www.dhakatribune.com",
    "newage": "https://www.newagebd.net",
    "financialexpress": "https://thefinancialexpress.com.bd",
    "observerbd": "https://www.observerbd.com",
    "jugantor": "https://www.jugantor.com",
    "ittefaq": "https://www.ittefaq.com.bd",
    "kalerkantho": "https://www.kalerkantho.com",
    "samakal": "https://samakal.com",
    "banglatribune": "https://www.banglatribune.com",
    "jaijaidin": "https://www.jaijaidinbd.com",
    "manabzamin": "https://mzamin.com",
}

# Cloudflare detection patterns
CLOUDFLARE_PATTERNS = [
    "cf_clearance",
    "cloudflare",
    "just a moment",
    "checking your browser",
    "__cf_bm",
    "ray id",
    "challenge-platform",
]


def check_for_cloudflare(html: str, headers: dict) -> bool:
    """Detect Cloudflare protection in response."""
    html_lower = html.lower()
    
    # Check HTML content
    for pattern in CLOUDFLARE_PATTERNS:
        if pattern in html_lower:
            return True
    
    # Check headers
    cf_headers = ["cf-ray", "cf-cache-status", "cf-request-id"]
    for header in cf_headers:
        if header in [h.lower() for h in headers.keys()]:
            # CF headers exist but doesn't mean blocked
            pass
    
    # Check for challenge page (very short HTML with CF markers)
    if len(html) < 5000 and "challenge" in html_lower:
        return True
        
    return False


def check_newspaper(name: str, url: str, timeout: int = 15) -> HealthCheck:
    """Perform health check on a single newspaper."""
    check = HealthCheck(
        name=name,
        url=url,
        checked_at=datetime.now().isoformat(),
    )
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    start_time = time.time()
    
    try:
        if HTTPX_AVAILABLE:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                html = response.text
                resp_headers = dict(response.headers)
                status_code = response.status_code
        else:
            response = requests.get(url, headers=headers, timeout=timeout)
            html = response.text
            resp_headers = dict(response.headers)
            status_code = response.status_code
        
        check.response_time_ms = (time.time() - start_time) * 1000
        check.status_code = status_code
        check.content_length = len(html)
        
        # Check for Cloudflare
        check.has_cloudflare = check_for_cloudflare(html, resp_headers)
        
        # Check if content is meaningful (not just challenge page)
        check.has_content = len(html) > 10000 and not check.has_cloudflare
        
        # Determine status
        if status_code == 200:
            if check.has_cloudflare:
                check.status = "cloudflare"
            elif check.has_content:
                check.status = "healthy"
            else:
                check.status = "unhealthy"
                check.error_message = "Content too short or empty"
        elif status_code in [403, 429]:
            check.status = "blocked"
            check.error_message = f"HTTP {status_code}"
        else:
            check.status = "unhealthy"
            check.error_message = f"HTTP {status_code}"
            
    except Exception as e:
        check.response_time_ms = (time.time() - start_time) * 1000
        error_str = str(e).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            check.status = "timeout"
            check.error_message = "Connection timed out"
        else:
            check.status = "error"
            check.error_message = str(e)[:100]
    
    return check


def run_health_checks(
    papers: Optional[List[str]] = None,
    max_workers: int = 5,
    timeout: int = 15,
) -> HealthReport:
    """Run health checks on specified or all newspapers."""
    report = HealthReport(timestamp=datetime.now().isoformat())
    
    # Select papers to check
    if papers:
        urls_to_check = {k: v for k, v in NEWSPAPER_URLS.items() if k in papers}
    else:
        urls_to_check = NEWSPAPER_URLS
    
    # Run checks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_newspaper, name, url, timeout): name
            for name, url in urls_to_check.items()
        }
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                check = future.result()
                report.add_check(check)
            except Exception as e:
                check = HealthCheck(
                    name=name,
                    url=urls_to_check.get(name, "unknown"),
                    status="error",
                    error_message=str(e)[:100],
                    checked_at=datetime.now().isoformat(),
                )
                report.add_check(check)
    
    return report


def print_report(report: HealthReport, format_type: str = "console"):
    """Print health report in specified format."""
    if format_type == "json":
        print(json.dumps(report.to_dict(), indent=2))
        return
    
    # Console format
    print("\n" + "=" * 60)
    print("📊 CANARY HEALTH CHECK REPORT")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print(f"\nSummary:")
    print(f"  Total Checked: {report.total_checked}")
    print(f"  ✅ Healthy: {report.healthy}")
    print(f"  ❌ Unhealthy: {report.unhealthy}")
    print(f"  🔒 Cloudflare: {report.cloudflare_blocked}")
    print(f"  ⏱️  Timeout: {report.timeout}")
    print(f"  ⚠️  Errors: {report.errors}")
    
    print("\n" + "-" * 60)
    print("Detailed Results:")
    print("-" * 60)
    
    # Sort by status
    sorted_checks = sorted(report.checks, key=lambda x: (x.status != "healthy", x.name))
    
    for check in sorted_checks:
        status_icon = {
            "healthy": "✅",
            "unhealthy": "❌",
            "cloudflare": "🔒",
            "timeout": "⏱️",
            "error": "⚠️",
            "blocked": "🚫",
        }.get(check.status, "❓")
        
        print(f"\n{status_icon} {check.name}")
        print(f"   URL: {check.url}")
        print(f"   Status: {check.status}")
        if check.status_code:
            print(f"   HTTP: {check.status_code}")
        print(f"   Response Time: {check.response_time_ms:.0f}ms")
        if check.error_message:
            print(f"   Error: {check.error_message}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Canary health check for newspaper spiders"
    )
    parser.add_argument(
        "--papers", "-p",
        help="Comma-separated list of papers to check"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Check all newspapers"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path for JSON report"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["console", "json"],
        default="console",
        help="Output format"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=15,
        help="Request timeout in seconds"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=5,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available newspapers"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available newspapers:")
        for name, url in sorted(NEWSPAPER_URLS.items()):
            print(f"  {name}: {url}")
        return
    
    # Determine papers to check
    papers = None
    if args.papers:
        papers = [p.strip() for p in args.papers.split(",")]
    elif not args.all:
        # Default to a few key papers
        papers = ["prothomalo", "thedailystar", "dailysun"]
    
    print(f"🔍 Running health checks...")
    report = run_health_checks(
        papers=papers,
        max_workers=args.workers,
        timeout=args.timeout,
    )
    
    # Output
    print_report(report, args.format)
    
    # Save to file if specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\n📁 Report saved to: {args.output}")
    
    # Exit with error code if any unhealthy
    if report.unhealthy > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
