#!/usr/bin/env python3
"""
BD News Scraper - Cross-Platform Quick Setup
=============================================
Works on Windows, macOS, and Linux.

Usage:
    python quickstart.py              # Basic setup
    python quickstart.py dashboard    # With dashboard
    python quickstart.py api          # With REST API
    python quickstart.py all          # All features
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    if sys.platform == 'win32':
        # Windows CMD doesn't support ANSI by default
        RED = YELLOW = GREEN = BLUE = CYAN = NC = ''
    else:
        RED = '\033[0;31m'
        YELLOW = '\033[1;33m'
        GREEN = '\033[0;32m'
        BLUE = '\033[0;34m'
        CYAN = '\033[0;36m'
        NC = '\033[0m'


def print_banner():
    """Print welcome banner."""
    print(f"{Colors.BLUE}")
    print(r"""
    ____  ____  _   __                    _____                                 
   / __ )/ __ \/ | / /___ _      _______/ ___/______________ _____  ___  _____
  / __  / / / /  |/ / __ \ | /| / / ___/\__ \/ ___/ ___/ __ `/ __ \/ _ \/ ___/
 / /_/ / /_/ / /|  / /_/ / |/ |/ (__  )___/ / /__/ /  / /_/ / /_/ /  __/ /    
/_____/_____/_/ |_/\____/|__/|__/____//____/\___/_/   \__,_/ .___/\___/_/     
                                                         /_/                  
    """)
    print(f"{Colors.NC}")
    print("Bangladesh News Scraper - Cross-Platform Setup")
    print(f"System: {platform.system()} {platform.release()}")
    print("=" * 50)


def run_command(cmd: list, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command and handle errors."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error running command: {' '.join(cmd)}{Colors.NC}")
        if e.stderr:
            print(e.stderr)
        raise


def check_python():
    """Verify Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"{Colors.RED}Python 3.9+ required. Found: {version.major}.{version.minor}{Colors.NC}")
        sys.exit(1)
    print(f"{Colors.GREEN}✓ Python {version.major}.{version.minor}.{version.micro}{Colors.NC}")


def check_uv():
    """Check if UV is installed, install if not."""
    if shutil.which('uv'):
        result = run_command(['uv', '--version'], capture=True)
        print(f"{Colors.GREEN}✓ UV installed: {result.stdout.strip()}{Colors.NC}")
        return True
    
    print(f"{Colors.YELLOW}UV not found. Installing...{Colors.NC}")
    
    system = platform.system()
    try:
        if system == 'Windows':
            # Windows: Use PowerShell
            run_command([
                'powershell', '-ExecutionPolicy', 'Bypass', '-Command',
                'irm https://astral.sh/uv/install.ps1 | iex'
            ])
        else:
            # Linux/macOS: Use curl
            run_command(['sh', '-c', 'curl -LsSf https://astral.sh/uv/install.sh | sh'])
        
        print(f"{Colors.GREEN}✓ UV installed successfully{Colors.NC}")
        print(f"{Colors.YELLOW}Please restart your terminal and run this script again.{Colors.NC}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}Failed to install UV: {e}{Colors.NC}")
        print("Please install UV manually: https://docs.astral.sh/uv/")
        sys.exit(1)


def sync_dependencies(extras: list = None):
    """Run uv sync with optional extras."""
    print(f"\n{Colors.BLUE}Installing dependencies...{Colors.NC}")
    
    cmd = ['uv', 'sync']
    if extras:
        for extra in extras:
            cmd.extend(['--extra', extra])
    
    run_command(cmd)
    print(f"{Colors.GREEN}✓ Dependencies installed{Colors.NC}")


def install_playwright():
    """Install Playwright browsers."""
    print(f"\n{Colors.BLUE}Installing Playwright Chromium browser...{Colors.NC}")
    
    try:
        run_command(['uv', 'run', 'playwright', 'install', 'chromium'])
        print(f"{Colors.GREEN}✓ Playwright browser installed{Colors.NC}")
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Playwright install failed: {e}{Colors.NC}")
        print("You can install it manually: uv run playwright install chromium")


def print_usage(mode: str):
    """Print usage information."""
    print(f"\n{Colors.GREEN}{'=' * 50}")
    print("Setup Complete!")
    print(f"{'=' * 50}{Colors.NC}")
    print()
    print("Quick Commands:")
    print(f"  {Colors.CYAN}# Run a spider{Colors.NC}")
    print("  uv run scrapy crawl prothomalo")
    print()
    print(f"  {Colors.CYAN}# Run with articles limit{Colors.NC}")
    print("  uv run scrapy crawl dailystar -s CLOSESPIDER_ITEMCOUNT=10")
    print()
    print(f"  {Colors.CYAN}# Test all spiders{Colors.NC}")
    print("  uv run python scripts/test_all_spiders.py --timeout 60")
    print()
    
    if mode in ['dashboard', 'all']:
        print(f"  {Colors.CYAN}# Run dashboard{Colors.NC}")
        print("  uv run streamlit run scripts/dashboard_enhanced.py")
        print()
    
    if mode in ['api', 'all']:
        print(f"  {Colors.CYAN}# Run API{Colors.NC}")
        print("  uv run uvicorn BDNewsPaper.api:app --reload")
        print()
    
    print(f"Available: {Colors.GREEN}82 spiders{Colors.NC} (prothomalo, dailystar, jugantor, etc.)")
    print(f"Docs: README.md")


def main():
    """Main entry point."""
    print_banner()
    
    # Determine mode from arguments
    mode = 'basic'
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    valid_modes = ['basic', 'dashboard', 'api', 'all', 'help']
    if mode == 'help' or mode == '--help' or mode == '-h':
        print("Usage: python quickstart.py [mode]")
        print()
        print("Modes:")
        print("  basic     - Scraper only (default)")
        print("  dashboard - With Streamlit dashboard")
        print("  api       - With REST API")
        print("  all       - All features")
        sys.exit(0)
    
    if mode not in valid_modes:
        print(f"{Colors.RED}Unknown mode: {mode}{Colors.NC}")
        print("Use: python quickstart.py [basic|dashboard|api|all]")
        sys.exit(1)
    
    print(f"Mode: {Colors.CYAN}{mode}{Colors.NC}")
    print()
    
    # Step 1: Check Python
    check_python()
    
    # Step 2: Check/Install UV
    check_uv()
    
    # Step 3: Sync dependencies
    extras = {
        'basic': [],
        'dashboard': ['dashboard'],
        'api': ['api'],
        'all': ['all', 'dev', 'dashboard'],
    }
    sync_dependencies(extras.get(mode, []))
    
    # Step 4: Install Playwright
    install_playwright()
    
    # Step 5: Print usage
    print_usage(mode)


if __name__ == '__main__':
    main()
