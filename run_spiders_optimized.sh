#!/bin/bash

# Enhanced spider runner with performance monitoring
# Usage: ./run_spiders_optimized.sh [spider_name] [--monitor]

# Create logs directory if it doesn't exist
mkdir -p logs

# Array of available spiders
spiders=(
    "prothomalo"
    "bdpratidin" 
    "dailysun"
    "ittefaq"
    "kalerkantho"
    "bangladesh_today"
    "thedailystar"
    "dhakatribune"
)

# Function to run a single spider with monitoring
run_spider() {
    local spider_name=$1
    local log_file="logs/${spider_name}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Starting spider: $spider_name"
    echo "Log file: $log_file"
    
    # Run spider with uv and optimized settings
    if [ -n "$UV_CMD" ]; then
        $UV_CMD scrapy crawl "$spider_name" \
            -s CONCURRENT_REQUESTS=64 \
            -s DOWNLOAD_DELAY=0.25 \
            -s AUTOTHROTTLE_TARGET_CONCURRENCY=8.0 \
            -L INFO \
            2>&1 | tee "$log_file"
    else
        scrapy crawl "$spider_name" \
            -s CONCURRENT_REQUESTS=64 \
            -s DOWNLOAD_DELAY=0.25 \
            -s AUTOTHROTTLE_TARGET_CONCURRENCY=8.0 \
            -L INFO \
            2>&1 | tee "$log_file"
    fi
    
    # Get exit code
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Spider $spider_name completed successfully"
    else
        echo "❌ Spider $spider_name failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Function to run all spiders
run_all_spiders() {
    echo "🚀 Starting all spiders with optimized settings..."
    echo "Start time: $(date)"
    
    local start_time=$(date +%s)
    local success_count=0
    local total_spiders=${#spiders[@]}
    
    for spider in "${spiders[@]}"; do
        echo ""
        echo "📰 Running spider: $spider"
        echo "Progress: $((success_count + 1))/$total_spiders"
        
        if run_spider "$spider"; then
            ((success_count++))
        fi
        
        # Short delay between spiders to prevent overwhelming
        sleep 5
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    echo "🏁 All spiders completed!"
    echo "Success: $success_count/$total_spiders"
    echo "Total time: ${duration}s ($(($duration / 60))m $(($duration % 60))s)"
    echo "End time: $(date)"
    
    # Generate performance report if monitoring script exists
    if [ -f "performance_monitor.py" ]; then
        echo "📊 Generating performance report..."
        if [ -n "$UV_CMD" ]; then
            $UV_CMD python performance_monitor.py report
        else
            python3 performance_monitor.py report
        fi
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [spider_name] [--monitor]"
    echo ""
    echo "Available spiders:"
    for spider in "${spiders[@]}"; do
        echo "  - $spider"
    done
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all spiders"
    echo "  $0 prothomalo        # Run specific spider"
    echo "  $0 --monitor         # Run all with monitoring"
    echo "  $0 prothomalo --monitor  # Run specific spider with monitoring"
}

# Function to start monitoring
start_monitoring() {
    if [ -f "performance_monitor.py" ]; then
        echo "📊 Starting performance monitor..."
        if [ -n "$UV_CMD" ]; then
            $UV_CMD python performance_monitor.py &
        else
            python3 performance_monitor.py &
        fi
        local monitor_pid=$!
        echo "Monitor PID: $monitor_pid"
        return $monitor_pid
    else
        echo "⚠️  Performance monitor not found"
        return 0
    fi
}

# Main script logic
main() {
    # Check if uv is available, fallback to direct commands if not
    if command -v uv &> /dev/null; then
        echo "🚀 Using UV for optimized performance"
        UV_CMD="uv run"
    else
        echo "⚠️  UV not found, using direct commands"
        UV_CMD=""
        # Check if scrapy is available
        if ! command -v scrapy &> /dev/null; then
            echo "❌ Scrapy not found. Please install requirements or use setup.sh"
            exit 1
        fi
    fi
    
    # Parse arguments
    local spider_name=""
    local monitor=false
    
    for arg in "$@"; do
        case $arg in
            --monitor)
                monitor=true
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                if [[ " ${spiders[@]} " =~ " $arg " ]]; then
                    spider_name="$arg"
                elif [ -n "$arg" ]; then
                    echo "❌ Unknown spider: $arg"
                    show_usage
                    exit 1
                fi
                ;;
        esac
    done
    
    # Start monitoring if requested
    local monitor_pid=0
    if [ "$monitor" = true ]; then
        start_monitoring
        monitor_pid=$?
    fi
    
    # Run spider(s)
    if [ -n "$spider_name" ]; then
        echo "🕷️  Running single spider: $spider_name"
        run_spider "$spider_name"
    else
        run_all_spiders
    fi
    
    # Stop monitoring if it was started
    if [ $monitor_pid -gt 0 ]; then
        echo "Stopping performance monitor (PID: $monitor_pid)"
        kill $monitor_pid 2>/dev/null
    fi
}

# Run main function with all arguments
main "$@"