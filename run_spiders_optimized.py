#!/usr/bin/env python3
"""
Enhanced spider runner with performance monitoring - Cross-platform Python version
Supports Windows, macOS, and Linux

Usage: python run_spiders_optimized.py [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
"""

import argparse
import os
import subprocess
import sys
import time
import re
from datetime import datetime
from pathlib import Path
import shutil


class SpiderRunner:
    """Cross-platform spider runner with monitoring and optimization features"""
    
    def __init__(self):
        self.spiders = [
            "prothomalo",
            "bdpratidin", 
            "dailysun",
            "ittefaq",
            "thebangladeshtoday",
            "thedailystar"
        ]
        
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Check for UV and Scrapy availability
        self.uv_cmd = self._check_uv()
        self.scrapy_available = self._check_scrapy()
        
    def _check_uv(self):
        """Check if UV is available"""
        if shutil.which("uv"):
            print("🚀 Using UV for optimized performance")
            return ["uv", "run"]
        else:
            print("⚠️  UV not found, using direct commands")
            return []
    
    def _check_scrapy(self):
        """Check if Scrapy is available"""
        if self.uv_cmd:
            # With UV, scrapy should be available through the virtual environment
            return True
        elif shutil.which("scrapy"):
            return True
        else:
            print("❌ Scrapy not found. Please install requirements or use setup.sh")
            return False
    
    def _validate_date(self, date_str):
        """Validate date format YYYY-MM-DD"""
        if not date_str:
            return True
        
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _build_spider_command(self, spider_name, start_date=None, end_date=None):
        """Build the spider command with all parameters"""
        cmd = []
        
        # Add UV command if available
        if self.uv_cmd:
            cmd.extend(self.uv_cmd)
        
        # Add scrapy command
        cmd.extend(["scrapy", "crawl", spider_name])
        
        # Add date parameters
        if start_date:
            cmd.extend(["-a", f"start_date={start_date}"])
        if end_date:
            cmd.extend(["-a", f"end_date={end_date}"])
        
        # Add performance settings
        cmd.extend([
            "-s", "CONCURRENT_REQUESTS=64",
            "-s", "DOWNLOAD_DELAY=0.25", 
            "-s", "AUTOTHROTTLE_TARGET_CONCURRENCY=8.0",
            "-L", "INFO"
        ])
        
        return cmd
    
    def run_spider(self, spider_name, start_date=None, end_date=None):
        """Run a single spider with monitoring"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"{spider_name}_{timestamp}.log"
        
        print(f"Starting spider: {spider_name}")
        print(f"Log file: {log_file}")
        
        # Build command
        cmd = self._build_spider_command(spider_name, start_date, end_date)
        
        # Run spider with logging
        try:
            with open(log_file, 'w', encoding='utf-8') as log_f:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Real-time output and logging
                for line in process.stdout:
                    print(line, end='')
                    log_f.write(line)
                    log_f.flush()
                
                process.wait()
                exit_code = process.returncode
                
        except Exception as e:
            print(f"❌ Error running spider {spider_name}: {e}")
            return False
        
        if exit_code == 0:
            print(f"✅ Spider {spider_name} completed successfully")
            return True
        else:
            print(f"❌ Spider {spider_name} failed with exit code {exit_code}")
            return False
    
    def run_all_spiders(self, start_date=None, end_date=None):
        """Run all spiders sequentially"""
        print("🚀 Starting all spiders with optimized settings...")
        
        if start_date or end_date:
            start_str = start_date or 'beginning'
            end_str = end_date or 'end'
            print(f"Date range: {start_str} to {end_str}")
        
        start_time = time.time()
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        success_count = 0
        total_spiders = len(self.spiders)
        
        for i, spider in enumerate(self.spiders, 1):
            print()
            print(f"📰 Running spider: {spider}")
            print(f"Progress: {i}/{total_spiders}")
            
            if self.run_spider(spider, start_date, end_date):
                success_count += 1
            
            # Short delay between spiders
            if i < total_spiders:
                print("Waiting 5 seconds before next spider...")
                time.sleep(5)
        
        end_time = time.time()
        duration = int(end_time - start_time)
        minutes = duration // 60
        seconds = duration % 60
        
        print()
        print("🏁 All spiders completed!")
        print(f"Success: {success_count}/{total_spiders}")
        print(f"Total time: {duration}s ({minutes}m {seconds}s)")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate performance report if monitoring script exists
        self._generate_performance_report()
        
        return success_count == total_spiders
    
    def _generate_performance_report(self):
        """Generate performance report if monitor script exists"""
        monitor_script = Path("performance_monitor.py")
        if monitor_script.exists():
            print("📊 Generating performance report...")
            try:
                cmd = []
                if self.uv_cmd:
                    cmd.extend(self.uv_cmd)
                cmd.extend(["python", "performance_monitor.py", "report"])
                
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to generate performance report: {e}")
    
    def start_monitoring(self):
        """Start performance monitoring in background"""
        monitor_script = Path("performance_monitor.py")
        if monitor_script.exists():
            print("📊 Starting performance monitor...")
            try:
                cmd = []
                if self.uv_cmd:
                    cmd.extend(self.uv_cmd)
                cmd.extend(["python", "performance_monitor.py"])
                
                process = subprocess.Popen(cmd)
                print(f"Monitor PID: {process.pid}")
                return process
            except Exception as e:
                print(f"⚠️  Failed to start performance monitor: {e}")
                return None
        else:
            print("⚠️  Performance monitor not found")
            return None
    
    def show_usage(self):
        """Show usage information"""
        print("Usage: python run_spiders_optimized.py [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]")
        print()
        print("Available spiders:")
        for spider in self.spiders:
            print(f"  - {spider}")
        print()
        print("Date filtering options:")
        print("  --start-date YYYY-MM-DD  Scrape articles from this date onwards")
        print("  --end-date YYYY-MM-DD    Scrape articles up to this date")
        print()
        print("Examples:")
        print("  python run_spiders_optimized.py                                           # Run all spiders")
        print("  python run_spiders_optimized.py prothomalo                               # Run specific spider")
        print("  python run_spiders_optimized.py --monitor                                # Run all with monitoring")
        print("  python run_spiders_optimized.py prothomalo --monitor                     # Run specific spider with monitoring")
        print("  python run_spiders_optimized.py --start-date 2023-01-01                 # Run all spiders from Jan 1, 2023")
        print("  python run_spiders_optimized.py prothomalo --start-date 2023-01-01      # Run prothomalo from Jan 1, 2023")
        print("  python run_spiders_optimized.py --start-date 2023-01-01 --end-date 2023-12-31  # Run all spiders for 2023")


def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Enhanced spider runner with performance monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'spider', 
        nargs='?', 
        help='Name of the spider to run (if not provided, runs all spiders)'
    )
    parser.add_argument(
        '--monitor', 
        action='store_true', 
        help='Enable performance monitoring'
    )
    parser.add_argument(
        '--start-date', 
        help='Start date for scraping (YYYY-MM-DD format)'
    )
    parser.add_argument(
        '--end-date', 
        help='End date for scraping (YYYY-MM-DD format)'
    )
    
    # Handle help manually to show custom usage
    if '--help' in sys.argv or '-h' in sys.argv:
        runner = SpiderRunner()
        runner.show_usage()
        return
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = SpiderRunner()
    
    # Check if scrapy is available
    if not runner.scrapy_available:
        sys.exit(1)
    
    # Validate spider name
    if args.spider and args.spider not in runner.spiders:
        print(f"❌ Unknown spider: {args.spider}")
        print(f"Available spiders: {', '.join(runner.spiders)}")
        sys.exit(1)
    
    # Validate dates
    if args.start_date and not runner._validate_date(args.start_date):
        print("❌ Invalid start date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    if args.end_date and not runner._validate_date(args.end_date):
        print("❌ Invalid end date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    # Start monitoring if requested
    monitor_process = None
    if args.monitor:
        monitor_process = runner.start_monitoring()
    
    try:
        # Run spider(s)
        if args.spider:
            print(f"🕷️  Running single spider: {args.spider}")
            if args.start_date or args.end_date:
                start_str = args.start_date or 'beginning'
                end_str = args.end_date or 'end'
                print(f"Date range: {start_str} to {end_str}")
            
            success = runner.run_spider(args.spider, args.start_date, args.end_date)
            sys.exit(0 if success else 1)
        else:
            success = runner.run_all_spiders(args.start_date, args.end_date)
            sys.exit(0 if success else 1)
    
    finally:
        # Stop monitoring if it was started
        if monitor_process:
            print(f"Stopping performance monitor (PID: {monitor_process.pid})")
            try:
                monitor_process.terminate()
                monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                monitor_process.kill()
            except Exception as e:
                print(f"Warning: Could not stop monitor process: {e}")


if __name__ == "__main__":
    main()