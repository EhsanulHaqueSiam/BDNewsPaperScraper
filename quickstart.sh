#!/bin/bash
# =============================================================================
# BD News Scraper - Quick Setup Script
# =============================================================================
# Usage: ./quickstart.sh [component]
#
# Components:
#   (no args) - Basic setup (scraper only)
#   dashboard - Setup with Streamlit dashboard
#   api       - Setup with REST API
#   all       - Setup with all features
#   docker    - Run with Docker Compose
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ____  ____  _   __                    _____                                 
   / __ )/ __ \/ | / /___ _      _______/ ___/______________ _____  ___  _____
  / __  / / / /  |/ / __ \ | /| / / ___/\__ \/ ___/ ___/ __ `/ __ \/ _ \/ ___/
 / /_/ / /_/ / /|  / /_/ / |/ |/ (__  )___/ / /__/ /  / /_/ / /_/ /  __/ /    
/_____/_____/_/ |_/\____/|__/|__/____//____/\___/_/   \__,_/ .___/\___/_/     
                                                         /_/                  
EOF
    echo -e "${NC}"
    echo "Bangladesh News Scraper - Quick Setup"
    echo "======================================"
    echo ""
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}UV not found. Installing...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    echo -e "${GREEN}✓ UV installed: $(uv --version)${NC}"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3.9+ required. Please install Python first.${NC}"
        exit 1
    fi
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"
}

setup_basic() {
    echo -e "\n${BLUE}Step 1: Syncing dependencies...${NC}"
    uv sync
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

setup_dashboard() {
    echo -e "\n${BLUE}Installing dashboard dependencies...${NC}"
    uv sync --extra dashboard
    echo -e "${GREEN}✓ Dashboard dependencies installed${NC}"
}

setup_api() {
    echo -e "\n${BLUE}Installing API dependencies...${NC}"
    uv sync --extra api
    echo -e "${GREEN}✓ API dependencies installed${NC}"
}

setup_all() {
    echo -e "\n${BLUE}Installing all dependencies...${NC}"
    uv sync --extra all --extra dev --extra dashboard
    echo -e "${GREEN}✓ All dependencies installed${NC}"
}

install_playwright() {
    echo -e "\n${BLUE}Step 2: Installing Playwright browsers...${NC}"
    uv run playwright install chromium
    echo -e "${GREEN}✓ Playwright browsers installed${NC}"
}

print_usage() {
    echo -e "\n${GREEN}=== Setup Complete! ===${NC}"
    echo ""
    echo "Quick Commands:"
    echo "  # Run a spider"
    echo "  uv run scrapy crawl prothomalo"
    echo ""
    echo "  # Run with articles limit"
    echo "  uv run scrapy crawl dailystar -s CLOSESPIDER_ITEMCOUNT=10"
    echo ""
    echo "  # Test all spiders"
    echo "  uv run python scripts/test_all_spiders.py --timeout 60 --max-items 2"
    echo ""
    if [[ "$1" == "dashboard" ]] || [[ "$1" == "all" ]]; then
        echo "  # Run dashboard"
        echo "  uv run streamlit run scripts/dashboard_enhanced.py"
        echo ""
    fi
    if [[ "$1" == "api" ]] || [[ "$1" == "all" ]]; then
        echo "  # Run API"
        echo "  uv run uvicorn BDNewsPaper.api:app --reload"
        echo ""
    fi
    echo "Available Spiders: 82 newspapers including prothomalo, dailystar, jugantor, etc."
    echo ""
    echo "Documentation: README.md"
}

run_docker() {
    echo -e "\n${BLUE}Starting Docker Compose...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker not found. Please install Docker first.${NC}"
        exit 1
    fi
    
    echo "Starting services..."
    docker-compose up -d api dashboard redis
    
    echo -e "${GREEN}✓ Services started!${NC}"
    echo ""
    echo "Access:"
    echo "  - Dashboard: http://localhost:8501"
    echo "  - API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
}

# Main
print_banner
check_python
check_uv

COMPONENT=${1:-basic}

case $COMPONENT in
    basic|"")
        setup_basic
        install_playwright
        print_usage "basic"
        ;;
    dashboard)
        setup_dashboard
        install_playwright
        print_usage "dashboard"
        ;;
    api)
        setup_api
        install_playwright
        print_usage "api"
        ;;
    all)
        setup_all
        install_playwright
        print_usage "all"
        ;;
    docker)
        run_docker
        ;;
    *)
        echo -e "${RED}Unknown component: $COMPONENT${NC}"
        echo "Usage: ./quickstart.sh [basic|dashboard|api|all|docker]"
        exit 1
        ;;
esac
