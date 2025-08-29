#!/bin/bash

# BDNewsPaper Scraper Setup Script with UV
# This script sets up the project using UV for fast dependency management

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install uv if not present
install_uv() {
    if command_exists uv; then
        print_success "UV is already installed ($(uv --version))"
        return 0
    fi
    
    print_status "Installing UV package manager..."
    
    if command_exists curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command_exists wget; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        print_error "Neither curl nor wget is available. Please install one of them first."
        exit 1
    fi
    
    # Add uv to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command_exists uv; then
        print_success "UV installed successfully ($(uv --version))"
    else
        print_error "Failed to install UV. Please install manually: https://github.com/astral-sh/uv"
        exit 1
    fi
}

# Function to setup the project
setup_project() {
    print_status "Setting up BDNewsPaper Scraper project..."
    
    # Create virtual environment with uv
    print_status "Creating virtual environment with UV..."
    uv venv --python 3.11
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install dependencies
    print_status "Installing project dependencies..."
    uv sync
    
    # Install optional performance dependencies
    if [ "$1" = "--performance" ] || [ "$1" = "--all" ]; then
        print_status "Installing performance dependencies..."
        uv sync --extra performance
    fi
    
    # Install development dependencies
    if [ "$1" = "--dev" ] || [ "$1" = "--all" ]; then
        print_status "Installing development dependencies..."
        uv sync --extra dev
    fi
    
    # Install monitoring dependencies
    if [ "$1" = "--monitoring" ] || [ "$1" = "--all" ]; then
        print_status "Installing monitoring dependencies..."
        uv sync --extra monitoring
    fi
    
    # Create necessary directories
    print_status "Creating project directories..."
    mkdir -p logs
    mkdir -p data
    mkdir -p reports
    mkdir -p httpcache
    
    # Set up pre-commit hooks if in dev mode
    if [ "$1" = "--dev" ] || [ "$1" = "--all" ]; then
        if [ -f .pre-commit-config.yaml ]; then
            print_status "Installing pre-commit hooks..."
            uv run pre-commit install
        fi
    fi
    
    # Install playwright browsers if needed
    if command_exists playwright; then
        print_status "Installing Playwright browsers..."
        uv run playwright install
    fi
    
    print_success "Project setup completed!"
}

# Function to show usage
show_usage() {
    echo "BDNewsPaper Scraper Setup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev         Install development dependencies"
    echo "  --performance Install performance optimization dependencies"
    echo "  --monitoring  Install monitoring dependencies"
    echo "  --all         Install all optional dependencies"
    echo "  --check       Check installation and requirements"
    echo "  --clean       Clean up virtual environment and reinstall"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Basic installation"
    echo "  $0 --dev            # Development setup"
    echo "  $0 --all            # Full installation with all features"
    echo "  $0 --check          # Check current installation"
}

# Function to check installation
check_installation() {
    print_status "Checking BDNewsPaper Scraper installation..."
    
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        print_error "Virtual environment not found. Run setup first."
        return 1
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Check key dependencies
    local deps=("scrapy" "playwright" "pytz" "sqlite3")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! python -c "import $dep" 2>/dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        print_success "All dependencies are properly installed"
        
        # Show version information
        echo ""
        echo "Installed versions:"
        echo "  Python: $(python --version)"
        echo "  Scrapy: $(python -c 'import scrapy; print(scrapy.__version__)')"
        echo "  UV: $(uv --version)"
        
        # Check if spiders are accessible
        if python -c "from BDNewsPaper.spiders.prothomalo import ProthomaloSpider" 2>/dev/null; then
            print_success "Spiders are accessible"
        else
            print_warning "Spiders may not be properly configured"
        fi
        
    else
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_status "Run setup again to install missing dependencies"
        return 1
    fi
}

# Function to clean installation
clean_installation() {
    print_status "Cleaning up existing installation..."
    
    if [ -d ".venv" ]; then
        rm -rf .venv
        print_success "Removed virtual environment"
    fi
    
    if [ -f "uv.lock" ]; then
        rm -f uv.lock
        print_success "Removed lock file"
    fi
    
    # Clean cache directories
    if [ -d "httpcache" ]; then
        rm -rf httpcache
        print_success "Cleaned HTTP cache"
    fi
    
    if [ -d "__pycache__" ]; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        print_success "Cleaned Python cache"
    fi
    
    print_success "Cleanup completed"
}

# Main script execution
main() {
    echo "🕷️  BDNewsPaper Scraper Setup with UV"
    echo "====================================="
    echo ""
    
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --check)
            check_installation
            exit $?
            ;;
        --clean)
            clean_installation
            echo ""
            print_status "Run setup again to reinstall the project"
            exit 0
            ;;
        --dev|--performance|--monitoring|--all)
            # Valid options, continue
            ;;
        "")
            # Default installation
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    # Install UV if needed
    install_uv
    
    # Setup the project
    setup_project "$1"
    
    echo ""
    print_success "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Activate the virtual environment: source .venv/bin/activate"
    echo "  2. Run a spider: uv run scrapy crawl prothomalo"
    echo "  3. Run all spiders: ./run_spiders_optimized.sh"
    echo "  4. Monitor performance: uv run python performance_monitor.py stats"
    echo ""
    echo "For development:"
    echo "  - Format code: uv run black BDNewsPaper/"
    echo "  - Sort imports: uv run isort BDNewsPaper/"
    echo "  - Run tests: uv run pytest"
    echo ""
}

# Run main function with all arguments
main "$@"