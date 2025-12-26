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
from datetime import datetime, timedelta
from pathlib import Path
import shutil


class SpiderRunner:
    """Cross-platform spider runner with monitoring and optimization features"""
    
    def __init__(self):
        self.spiders = [
            "prothomalo",
            "BDpratidin", 
            "dailysun",
            "ittefaq",
            "bangladesh_today",
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
    
    def calculate_date_chunks(self, start_date, end_date, chunk_days=30):
        """Calculate if date range needs chunking"""
        if not start_date or not end_date:
            return "full_range"
        
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            diff_days = (end_dt - start_dt).days
            
            if diff_days > chunk_days:
                return f"chunked:{chunk_days}"
            else:
                return "full_range"
        except ValueError:
            return "full_range"
    
    def generate_date_chunks(self, start_date, end_date, chunk_days):
        """Generate date chunks for large ranges"""
        chunks = []
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_dt:
            chunk_end = min(current_date + timedelta(days=chunk_days - 1), end_dt)
            chunks.append((
                current_date.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            ))
            current_date = chunk_end + timedelta(days=1)
            
            if current_date > end_dt:
                break
        
        return chunks
    
    def is_range_completed(self, spider_name, start_date, end_date):
        """Check if date range was already completed"""
        progress_file = self.logs_dir / f".{spider_name}_progress.txt"
        if not progress_file.exists():
            return False
        
        try:
            with open(progress_file, 'r') as f:
                for line in f:
                    if line.strip() == f"COMPLETED:{start_date}:{end_date}":
                        return True
        except Exception:
            pass
        
        return False
    
    def mark_range_completed(self, spider_name, start_date, end_date):
        """Mark date range as completed"""
        progress_file = self.logs_dir / f".{spider_name}_progress.txt"
        try:
            with open(progress_file, 'a') as f:
                f.write(f"COMPLETED:{start_date}:{end_date}\n")
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
    
    def _get_articles_count(self, spider_name):
        """Get current count of articles for a spider from database"""
        import sqlite3
        
        # Map spider names to their database paper_name values
        spider_to_paper_name = {
            "prothomalo": "Prothom Alo",
            "BDpratidin": "BD Pratidin", 
            "dailysun": "Daily Sun",
            "ittefaq": "The Daily Ittefaq",
            "bangladesh_today": "The Bangladesh Today",
            "thedailystar": "The Daily Star"
        }
        
        paper_name = spider_to_paper_name.get(spider_name, spider_name)
        
        try:
            conn = sqlite3.connect("news_articles.db", timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles WHERE paper_name = ?", (paper_name,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
    
    def run_spider_chunked(self, spider_name, start_date, end_date, chunk_days=30):
        """Run spider with chunking for large date ranges"""
        print(f"🔄 Running {spider_name} with {chunk_days}-day chunks from {start_date} to {end_date}")
        
        chunks = self.generate_date_chunks(start_date, end_date, chunk_days)
        total_chunks = len(chunks)
        completed_chunks = 0
        failed_chunks = 0
        
        # Timing and progress tracking
        operation_start = time.time()
        chunk_times = []
        articles_per_chunk = []
        
        print(f"📊 Total chunks to process: {total_chunks}")
        print(f"🕐 Operation started at: {datetime.now().strftime('%H:%M:%S')}")
        
        for i, (chunk_start, chunk_end) in enumerate(chunks):
            chunk_start_time = time.time()
            
            print(f"\n📅 Processing chunk {i + 1}/{total_chunks}: {chunk_start} to {chunk_end}")
            
            # Check if chunk already completed
            if self.is_range_completed(spider_name, chunk_start, chunk_end):
                print("✅ Chunk already completed, skipping...")
                completed_chunks += 1
                continue
            
            # Get articles count before this chunk
            articles_before = self._get_articles_count(spider_name)
            
            # Run chunk
            if self.run_spider_chunk(spider_name, chunk_start, chunk_end, i + 1, total_chunks):
                chunk_end_time = time.time()
                chunk_duration = chunk_end_time - chunk_start_time
                chunk_times.append(chunk_duration)
                
                # Get articles count after this chunk
                articles_after = self._get_articles_count(spider_name)
                articles_this_chunk = articles_after - articles_before
                articles_per_chunk.append(articles_this_chunk)
                
                self.mark_range_completed(spider_name, chunk_start, chunk_end)
                completed_chunks += 1
                
                # Calculate progress statistics
                avg_time = sum(chunk_times) / len(chunk_times) if chunk_times else 0
                remaining_chunks = total_chunks - (i + 1)
                eta_seconds = remaining_chunks * avg_time
                eta_time = datetime.now() + timedelta(seconds=eta_seconds)
                
                # Progress summary
                print(f"✅ Chunk {i + 1}/{total_chunks} completed in {chunk_duration:.1f}s")
                print(f"   📰 Articles found: {articles_this_chunk}")
                print(f"   📊 Total articles so far: {articles_after}")
                if remaining_chunks > 0:
                    print(f"   ⏱️  Average time per chunk: {avg_time:.1f}s")
                    print(f"   🎯 ETA for completion: {eta_time.strftime('%H:%M:%S')} ({eta_seconds/60:.1f}m remaining)")
                
            else:
                failed_chunks += 1
                print(f"❌ Chunk {i + 1}/{total_chunks} failed")
            
            # Brief pause between chunks
            time.sleep(1)
        
        # Final summary with comprehensive statistics
        operation_end = time.time()
        total_duration = operation_end - operation_start
        total_articles = sum(articles_per_chunk) if articles_per_chunk else 0
        
        print(f"\n📈 Chunked spider summary for {spider_name}:")
        print(f"   ✅ Completed chunks: {completed_chunks}/{total_chunks}")
        print(f"   ❌ Failed chunks: {failed_chunks}/{total_chunks}")
        print(f"   🕐 Total operation time: {total_duration:.1f}s ({total_duration/60:.1f}m)")
        print(f"   📰 Total articles scraped: {total_articles}")
        
        if chunk_times:
            avg_chunk_time = sum(chunk_times) / len(chunk_times)
            fastest_chunk = min(chunk_times)
            slowest_chunk = max(chunk_times)
            print(f"   ⚡ Average chunk time: {avg_chunk_time:.1f}s")
            print(f"   🏃 Fastest chunk: {fastest_chunk:.1f}s")
            print(f"   🐌 Slowest chunk: {slowest_chunk:.1f}s")
        
        if articles_per_chunk:
            avg_articles = sum(articles_per_chunk) / len(articles_per_chunk)
            max_articles = max(articles_per_chunk)
            print(f"   📊 Average articles per chunk: {avg_articles:.1f}")
            print(f"   🏆 Best chunk yield: {max_articles} articles")
        
        # Return success if more than 80% of chunks completed
        success_rate = (completed_chunks * 100) // total_chunks if total_chunks > 0 else 0
        if success_rate >= 80:
            print(f"✅ Spider {spider_name} chunked operation completed ({success_rate}% success rate)")
            return True
        else:
            print(f"❌ Spider {spider_name} chunked operation had low success rate ({success_rate}%)")
            return False
    
    def run_spider_chunk(self, spider_name, start_date, end_date, chunk_num, total_chunks):
        """Run spider for a specific date chunk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"{spider_name}_chunk_{start_date}_to_{end_date}_{timestamp}.log"
        
        print(f"Log file: {log_file}")
        
        # Build optimized command for chunks
        cmd = []
        if self.uv_cmd:
            cmd.extend(self.uv_cmd)
        
        cmd.extend(["scrapy", "crawl", spider_name])
        cmd.extend(["-a", f"start_date={start_date}"])
        cmd.extend(["-a", f"end_date={end_date}"])
        
        # Optimized settings for chunked operations
        cmd.extend([
            "-s", "CONCURRENT_REQUESTS=32",
            "-s", "DOWNLOAD_DELAY=0.1", 
            "-s", "AUTOTHROTTLE_TARGET_CONCURRENCY=4.0",
            "-s", "MEMUSAGE_LIMIT_MB=4096",
            "-L", "INFO"
        ])
        
        try:
            with open(log_file, 'w', encoding='utf-8') as log_f:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                if process.stdout:
                    for line in process.stdout:
                        print(line, end='')
                        log_f.write(line)
                        log_f.flush()
                
                process.wait()
                exit_code = process.returncode
                
        except Exception as e:
            print(f"❌ Error running chunk {chunk_num}/{total_chunks}: {e}")
            return False
        
        if exit_code == 0:
            print(f"✅ Chunk {chunk_num}/{total_chunks} completed successfully")
            return True
        else:
            print(f"❌ Chunk {chunk_num}/{total_chunks} failed with exit code {exit_code}")
            return False
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
        print(f"🕐 Started at: {datetime.now().strftime('%H:%M:%S')}")
        print(f"Log file: {log_file}")
        
        # Get articles count before
        articles_before = self._get_articles_count(spider_name)
        start_time = time.time()
        
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
                if process.stdout:
                    for line in process.stdout:
                        print(line, end='')
                        log_f.write(line)
                        log_f.flush()
                
                process.wait()
                exit_code = process.returncode
                
        except Exception as e:
            print(f"❌ Error running spider {spider_name}: {e}")
            return False
        
        # Calculate completion statistics
        end_time = time.time()
        duration = end_time - start_time
        articles_after = self._get_articles_count(spider_name)
        articles_scraped = articles_after - articles_before
        
        if exit_code == 0:
            print(f"✅ Spider {spider_name} completed successfully")
            print(f"   🕐 Duration: {duration:.1f}s ({duration/60:.1f}m)")
            print(f"   📰 Articles scraped: {articles_scraped}")
            print(f"   📊 Total articles in database: {articles_after}")
            if duration > 0:
                print(f"   ⚡ Rate: {articles_scraped/duration:.1f} articles/second")
            return True
        else:
            print(f"❌ Spider {spider_name} failed with exit code {exit_code}")
            print(f"   🕐 Duration: {duration:.1f}s ({duration/60:.1f}m)")
            print(f"   📰 Articles scraped before failure: {articles_scraped}")
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
    
    def run_all_spiders(self, start_date=None, end_date=None):
        """Run all spiders sequentially with chunking support"""
        print("🚀 Starting all spiders with optimized settings...")
        
        if start_date or end_date:
            start_str = start_date or 'beginning'
            end_str = end_date or 'end'
            print(f"Date range: {start_str} to {end_str}")
        
        # Determine if chunking is needed
        chunk_strategy = self.calculate_date_chunks(start_date, end_date, 30)
        use_chunking = chunk_strategy.startswith("chunked:")
        chunk_days = 30
        
        if use_chunking:
            chunk_days = int(chunk_strategy.split(":")[1])
            print(f"📅 Large date range detected. Using {chunk_days}-day chunks for better performance.")
        
        start_time = time.time()
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        success_count = 0
        total_spiders = len(self.spiders)
        
        for i, spider in enumerate(self.spiders, 1):
            print()
            print(f"📰 Running spider: {spider}")
            print(f"Progress: {i}/{total_spiders}")
            
            if use_chunking and start_date and end_date:
                # Run spider with chunking
                if self.run_spider_chunked(spider, start_date, end_date, chunk_days):
                    success_count += 1
            else:
                # Run spider normally
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
                
                # Redirect output to avoid interference with main script
                with open("logs/monitor.log", "w") as log_file:
                    process = subprocess.Popen(
                        cmd, 
                        stdout=log_file, 
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL
                    )
                print(f"Monitor PID: {process.pid}")
                print("📊 Monitor output logged to logs/monitor.log")
                
                # Give monitor a moment to start
                time.sleep(2)
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
            
            # Check if chunking is needed for single spider
            chunk_strategy = runner.calculate_date_chunks(args.start_date, args.end_date, 30)
            if chunk_strategy.startswith("chunked:") and args.start_date and args.end_date:
                chunk_days = int(chunk_strategy.split(":")[1])
                print(f"📅 Large date range detected. Using {chunk_days}-day chunks.")
                success = runner.run_spider_chunked(args.spider, args.start_date, args.end_date, chunk_days)
            else:
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