#!/bin/bash

# Enhanced spider runner with performance monitoring
# Usage: ./run_spiders_optimized.sh [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

# Create logs directory if it doesn't exist
mkdir -p logs

# Array of available spiders
spiders=(
    "prothomalo"
    "BDpratidin" 
    "dailysun"
    "ittefaq"
    "bangladesh_today"
    "thedailystar"
)

# Function to monitor long-running operations
monitor_long_operation() {
    local spider_name=$1
    local log_file=$2
    local start_time=$3
    
    # Background monitoring for long operations
    (
        local last_check=$(date +%s)
        local last_size=0
        local stall_count=0
        
        while [ -f "$log_file" ] && ps -p $! > /dev/null 2>&1; do
            sleep 30  # Check every 30 seconds
            
            current_time=$(date +%s)
            current_size=$(wc -c < "$log_file" 2>/dev/null || echo "0")
            elapsed=$((current_time - start_time))
            
            # Check if log file is growing (activity)
            if [ "$current_size" -le "$last_size" ]; then
                ((stall_count++))
                if [ $stall_count -ge 10 ]; then  # 5 minutes of no activity
                    echo "⚠️  WARNING: $spider_name appears stalled (no activity for 5 minutes)"
                    echo "   Log file: $log_file"
                    echo "   Elapsed time: ${elapsed}s ($(($elapsed / 60))m)"
                    stall_count=0
                fi
            else
                stall_count=0
                # Show progress every 5 minutes for long operations
                if [ $((elapsed % 300)) -eq 0 ] && [ $elapsed -gt 300 ]; then
                    echo "📊 $spider_name progress update:"
                    echo "   Elapsed: ${elapsed}s ($(($elapsed / 60))m)"
                    echo "   Log size: $((current_size / 1024))KB"
                    if [ -f "$log_file" ]; then
                        echo "   Recent activity: $(tail -n 1 "$log_file" 2>/dev/null | cut -c1-100)..."
                    fi
                fi
            fi
            
            last_size=$current_size
            last_check=$current_time
        done
    ) &
    
    local monitor_pid=$!
    echo "📊 Long-operation monitor started (PID: $monitor_pid)"
    return $monitor_pid
}

# Function to get article count from database
get_articles_count() {
    local spider_name=$1
    local paper_name=""
    
    # Map spider names to their database paper_name values
    case "$spider_name" in
        "prothomalo")
            paper_name="Prothom Alo"
            ;;
        "BDpratidin")
            paper_name="BD Pratidin"
            ;;
        "dailysun")
            paper_name="Daily Sun"
            ;;
        "ittefaq")
            paper_name="The Daily Ittefaq"
            ;;
        "bangladesh_today")
            paper_name="The Bangladesh Today"
            ;;
        "thedailystar")
            paper_name="The Daily Star"
            ;;
        *)
            paper_name="$spider_name"
            ;;
    esac
    
    if [ -f "news_articles.db" ]; then
        sqlite3 news_articles.db "SELECT COUNT(*) FROM articles WHERE paper_name='$paper_name';" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Enhanced function to run a single spider with better monitoring
run_spider() {
    local spider_name=$1
    local start_date=$2
    local end_date=$3
    local log_file="logs/${spider_name}_$(date +%Y%m%d_%H%M%S).log"
    local start_time=$(date +%s)
    
    echo "Starting spider: $spider_name"
    echo "🕐 Started at: $(date +%H:%M:%S)"
    echo "Log file: $log_file"
    
    # Get articles count before
    local articles_before=$(get_articles_count "$spider_name")
    
    # Estimate if this will be a long operation
    local estimated_duration=300  # Default 5 minutes
    if [[ -n "$start_date" ]] && [[ -n "$end_date" ]]; then
        local diff_days=$(( ($(date -d "$end_date" +%s) - $(date -d "$start_date" +%s)) / 86400 ))
        if [ $diff_days -gt 30 ]; then
            estimated_duration=1800  # 30 minutes for large ranges
            echo "📅 Large date range detected ($diff_days days) - estimated duration: ${estimated_duration}s"
        fi
    fi
    
    # Build spider command with date parameters
    local spider_cmd=""
    if [ -n "$UV_CMD" ]; then
        spider_cmd="$UV_CMD scrapy crawl \"$spider_name\""
    else
        spider_cmd="scrapy crawl \"$spider_name\""
    fi
    
    # Add date range parameters if provided
    if [ -n "$start_date" ]; then
        spider_cmd="$spider_cmd -a start_date=\"$start_date\""
    fi
    if [ -n "$end_date" ]; then
        spider_cmd="$spider_cmd -a end_date=\"$end_date\""
    fi
    
    # Add performance settings
    spider_cmd="$spider_cmd -s CONCURRENT_REQUESTS=64 -s DOWNLOAD_DELAY=0.25 -s AUTOTHROTTLE_TARGET_CONCURRENCY=8.0 -L INFO"
    
    # Start long-operation monitoring if expected to run > 10 minutes
    local monitor_pid=0
    if [ $estimated_duration -gt 600 ]; then
        monitor_long_operation "$spider_name" "$log_file" "$start_time"
        monitor_pid=$?
    fi
    
    # Run spider
    echo "🚀 Executing: $spider_cmd"
    eval "$spider_cmd" 2>&1 | tee "$log_file"
    
    # Get exit code and calculate statistics
    local exit_code=${PIPESTATUS[0]}
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local articles_after=$(get_articles_count "$spider_name")
    local articles_scraped=$((articles_after - articles_before))
    
    # Stop monitoring if it was started
    if [ $monitor_pid -gt 0 ]; then
        kill $monitor_pid 2>/dev/null
    fi
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Spider $spider_name completed successfully"
        echo "   🕐 Duration: ${duration}s ($(($duration / 60))m)"
        echo "   📰 Articles scraped: $articles_scraped"
        echo "   📊 Total articles in database: $articles_after"
        if [ $duration -gt 0 ]; then
            local rate=$((articles_scraped * 1000 / duration))  # articles per second * 1000 for precision
            echo "   ⚡ Rate: $((rate / 1000)).$((rate % 1000)) articles/second"
        fi
    else
        echo "❌ Spider $spider_name failed with exit code $exit_code after ${duration}s"
        echo "   📰 Articles scraped before failure: $articles_scraped"
    fi
    
    return $exit_code
}

# Function to calculate date chunks for large ranges
calculate_date_chunks() {
    local start_date=$1
    local end_date=$2
    local chunk_days=${3:-30}  # Default 30-day chunks
    
    if [[ -z "$start_date" ]] || [[ -z "$end_date" ]]; then
        echo "full_range"
        return
    fi
    
    # Convert dates to epoch seconds for calculation
    local start_epoch=$(date -d "$start_date" +%s 2>/dev/null || echo "0")
    local end_epoch=$(date -d "$end_date" +%s 2>/dev/null || echo "0")
    
    if [[ $start_epoch -eq 0 ]] || [[ $end_epoch -eq 0 ]]; then
        echo "full_range"
        return
    fi
    
    local diff_days=$(( (end_epoch - start_epoch) / 86400 ))
    
    # If range is larger than chunk_days, return chunked, otherwise full_range
    if [[ $diff_days -gt $chunk_days ]]; then
        echo "chunked:$chunk_days"
    else
        echo "full_range"
    fi
}

# Function to generate date chunks
generate_date_chunks() {
    local start_date=$1
    local end_date=$2
    local chunk_days=$3
    
    local current_date="$start_date"
    local chunks=()
    
    while [[ $(date -d "$current_date" +%s) -le $(date -d "$end_date" +%s) ]]; do
        local chunk_end=$(date -d "$current_date + $((chunk_days - 1)) days" +%Y-%m-%d 2>/dev/null)
        
        # Don't exceed end_date
        if [[ $(date -d "$chunk_end" +%s) -gt $(date -d "$end_date" +%s) ]]; then
            chunk_end="$end_date"
        fi
        
        chunks+=("$current_date:$chunk_end")
        
        # Move to next chunk
        current_date=$(date -d "$chunk_end + 1 day" +%Y-%m-%d 2>/dev/null)
        
        # Break if we've reached or passed the end date
        if [[ $(date -d "$current_date" +%s) -gt $(date -d "$end_date" +%s) ]]; then
            break
        fi
    done
    
    printf '%s\n' "${chunks[@]}"
}

# Function to check if spider has already completed a date range
is_range_completed() {
    local spider_name=$1
    local start_date=$2
    local end_date=$3
    local progress_file="logs/.${spider_name}_progress.txt"
    
    if [[ ! -f "$progress_file" ]]; then
        return 1  # Not completed
    fi
    
    # Check if this exact range is marked as completed
    if grep -q "^COMPLETED:${start_date}:${end_date}$" "$progress_file" 2>/dev/null; then
        return 0  # Completed
    fi
    
    return 1  # Not completed
}

# Function to mark date range as completed
mark_range_completed() {
    local spider_name=$1
    local start_date=$2
    local end_date=$3
    local progress_file="logs/.${spider_name}_progress.txt"
    
    echo "COMPLETED:${start_date}:${end_date}" >> "$progress_file"
}

# Function to run all spiders with chunking support
run_all_spiders() {
    local start_date=$1
    local end_date=$2
    
    echo "🚀 Starting all spiders with optimized settings..."
    if [ -n "$start_date" ] || [ -n "$end_date" ]; then
        echo "Date range: ${start_date:-'beginning'} to ${end_date:-'end'}"
    fi
    echo "Start time: $(date)"
    
    # Determine if we need chunking
    local chunk_strategy=$(calculate_date_chunks "$start_date" "$end_date" 30)
    local use_chunking=false
    local chunk_days=30
    
    if [[ "$chunk_strategy" == chunked:* ]]; then
        use_chunking=true
        chunk_days=${chunk_strategy#chunked:}
        echo "📅 Large date range detected. Using $chunk_days-day chunks for better performance."
    fi
    
    local start_time=$(date +%s)
    local success_count=0
    local total_spiders=${#spiders[@]}
    
    for spider in "${spiders[@]}"; do
        echo ""
        echo "📰 Running spider: $spider"
        echo "Progress: $((success_count + 1))/$total_spiders"
        
        if [[ "$use_chunking" == true ]] && [[ -n "$start_date" ]] && [[ -n "$end_date" ]]; then
            # Run spider with chunking
            if run_spider_chunked "$spider" "$start_date" "$end_date" "$chunk_days"; then
                ((success_count++))
            fi
        else
            # Run spider normally
            if run_spider "$spider" "$start_date" "$end_date"; then
                ((success_count++))
            fi
        fi
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

# Function to run spider with chunking for large date ranges
run_spider_chunked() {
    local spider_name=$1
    local start_date=$2
    local end_date=$3
    local chunk_days=$4
    
    echo "🔄 Running $spider_name with $chunk_days-day chunks from $start_date to $end_date"
    
    # Generate chunks
    local chunks=($(generate_date_chunks "$start_date" "$end_date" "$chunk_days"))
    local total_chunks=${#chunks[@]}
    local completed_chunks=0
    local failed_chunks=0
    
    # Timing and progress tracking
    local operation_start=$(date +%s)
    local chunk_times=()
    local articles_per_chunk=()
    
    echo "📊 Total chunks to process: $total_chunks"
    echo "🕐 Operation started at: $(date +%H:%M:%S)"
    
    for i in "${!chunks[@]}"; do
        local chunk="${chunks[$i]}"
        local chunk_start="${chunk%:*}"
        local chunk_end="${chunk#*:}"
        local chunk_start_time=$(date +%s)
        
        echo ""
        echo "📅 Processing chunk $((i + 1))/$total_chunks: $chunk_start to $chunk_end"
        
        # Check if this chunk was already completed
        if is_range_completed "$spider_name" "$chunk_start" "$chunk_end"; then
            echo "✅ Chunk already completed, skipping..."
            ((completed_chunks++))
            continue
        fi
        
        # Get articles count before this chunk
        local articles_before=$(get_articles_count "$spider_name")
        
        # Run spider for this chunk
        local chunk_log_file="logs/${spider_name}_chunk_${chunk_start}_to_${chunk_end}_$(date +%Y%m%d_%H%M%S).log"
        echo "Log file: $chunk_log_file"
        
        # Build spider command for chunk
        local spider_cmd=""
        if [ -n "$UV_CMD" ]; then
            spider_cmd="$UV_CMD scrapy crawl \"$spider_name\""
        else
            spider_cmd="scrapy crawl \"$spider_name\""
        fi
        
        # Add chunk date parameters
        spider_cmd="$spider_cmd -a start_date=\"$chunk_start\" -a end_date=\"$chunk_end\""
        
        # Add optimized performance settings for chunked operations
        spider_cmd="$spider_cmd -s CONCURRENT_REQUESTS=32 -s DOWNLOAD_DELAY=0.1 -s AUTOTHROTTLE_TARGET_CONCURRENCY=4.0 -s MEMUSAGE_LIMIT_MB=4096 -L INFO"
        
        # Run chunk
        echo "🚀 Executing: $spider_cmd"
        if eval "$spider_cmd" 2>&1 | tee "$chunk_log_file"; then
            local exit_code=${PIPESTATUS[0]}
            local chunk_end_time=$(date +%s)
            local chunk_duration=$((chunk_end_time - chunk_start_time))
            
            if [ $exit_code -eq 0 ]; then
                # Calculate statistics
                local articles_after=$(get_articles_count "$spider_name")
                local articles_this_chunk=$((articles_after - articles_before))
                
                chunk_times+=($chunk_duration)
                articles_per_chunk+=($articles_this_chunk)
                
                echo "✅ Chunk $((i + 1))/$total_chunks completed in ${chunk_duration}s"
                echo "   📰 Articles found: $articles_this_chunk"
                echo "   📊 Total articles so far: $articles_after"
                
                # Calculate ETA for remaining chunks
                local remaining_chunks=$((total_chunks - (i + 1)))
                if [ $remaining_chunks -gt 0 ] && [ ${#chunk_times[@]} -gt 0 ]; then
                    local total_time=0
                    for time in "${chunk_times[@]}"; do
                        total_time=$((total_time + time))
                    done
                    local avg_time=$((total_time / ${#chunk_times[@]}))
                    local eta_seconds=$((remaining_chunks * avg_time))
                    local eta_minutes=$((eta_seconds / 60))
                    local eta_time=$(date -d "+${eta_seconds} seconds" +%H:%M:%S)
                    
                    echo "   ⏱️  Average time per chunk: ${avg_time}s"
                    echo "   🎯 ETA for completion: $eta_time (${eta_minutes}m remaining)"
                fi
                
                mark_range_completed "$spider_name" "$chunk_start" "$chunk_end"
                ((completed_chunks++))
            else
                echo "❌ Chunk $((i + 1))/$total_chunks failed with exit code $exit_code"
                ((failed_chunks++))
            fi
        else
            echo "❌ Chunk $((i + 1))/$total_chunks failed"
            ((failed_chunks++))
        fi
        
        # Brief pause between chunks to prevent overwhelming
        sleep 1
    done
    
    # Final comprehensive summary
    local operation_end=$(date +%s)
    local total_duration=$((operation_end - operation_start))
    local total_articles=0
    for articles in "${articles_per_chunk[@]}"; do
        total_articles=$((total_articles + articles))
    done
    
    echo ""
    echo "📈 Chunked spider summary for $spider_name:"
    echo "   ✅ Completed chunks: $completed_chunks/$total_chunks"
    echo "   ❌ Failed chunks: $failed_chunks/$total_chunks"
    echo "   🕐 Total operation time: ${total_duration}s ($((total_duration / 60))m)"
    echo "   📰 Total articles scraped: $total_articles"
    
    if [ ${#chunk_times[@]} -gt 0 ]; then
        local total_time=0
        local fastest=999999
        local slowest=0
        for time in "${chunk_times[@]}"; do
            total_time=$((total_time + time))
            if [ $time -lt $fastest ]; then fastest=$time; fi
            if [ $time -gt $slowest ]; then slowest=$time; fi
        done
        local avg_chunk_time=$((total_time / ${#chunk_times[@]}))
        echo "   ⚡ Average chunk time: ${avg_chunk_time}s"
        echo "   🏃 Fastest chunk: ${fastest}s"
        echo "   🐌 Slowest chunk: ${slowest}s"
    fi
    
    if [ ${#articles_per_chunk[@]} -gt 0 ] && [ $total_articles -gt 0 ]; then
        local avg_articles=$((total_articles / ${#articles_per_chunk[@]}))
        local max_articles=0
        for articles in "${articles_per_chunk[@]}"; do
            if [ $articles -gt $max_articles ]; then max_articles=$articles; fi
        done
        echo "   📊 Average articles per chunk: $avg_articles"
        echo "   🏆 Best chunk yield: $max_articles articles"
    fi
    
    # Return success if more than 80% of chunks completed
    local success_rate=$((completed_chunks * 100 / total_chunks))
    if [ $success_rate -ge 80 ]; then
        echo "✅ Spider $spider_name chunked operation completed (${success_rate}% success rate)"
        return 0
    else
        echo "❌ Spider $spider_name chunked operation had low success rate (${success_rate}%)"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [spider_name] [--monitor] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]"
    echo ""
    echo "Available spiders:"
    for spider in "${spiders[@]}"; do
        echo "  - $spider"
    done
    echo ""
    echo "Date filtering options:"
    echo "  --start-date YYYY-MM-DD  Scrape articles from this date onwards"
    echo "  --end-date YYYY-MM-DD    Scrape articles up to this date"
    echo ""
    echo "Examples:"
    echo "  $0                                           # Run all spiders"
    echo "  $0 prothomalo                               # Run specific spider"
    echo "  $0 --monitor                                # Run all with monitoring"
    echo "  $0 prothomalo --monitor                     # Run specific spider with monitoring"
    echo "  $0 --start-date 2023-01-01                 # Run all spiders from Jan 1, 2023"
    echo "  $0 prothomalo --start-date 2023-01-01      # Run prothomalo from Jan 1, 2023"
    echo "  $0 --start-date 2023-01-01 --end-date 2023-12-31  # Run all spiders for 2023"
    echo "  $0 --start-date 2022-01-01 --end-date 2024-12-31  # Long-range: 3 years (auto-chunked)"
    echo ""
    echo "Long-Range Features:"
    echo "  • Automatic chunking for date ranges > 30 days"
    echo "  • Resume capability for interrupted scraping"
    echo "  • Progress tracking per spider and date chunk"
    echo "  • Optimized memory settings for sustained operation"
}

# Function to start monitoring
start_monitoring() {
    if [ -f "performance_monitor.py" ]; then
        echo "📊 Starting performance monitor..."
        
        # Start monitor with output redirected to log file
        if [ -n "$UV_CMD" ]; then
            nohup $UV_CMD python performance_monitor.py > logs/monitor.log 2>&1 &
        else
            nohup python3 performance_monitor.py > logs/monitor.log 2>&1 &
        fi
        
        local monitor_pid=$!
        echo "Monitor PID: $monitor_pid"
        echo "📊 Monitor output logged to logs/monitor.log"
        
        # Give monitor a moment to start
        sleep 2
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
    local start_date=""
    local end_date=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --monitor)
                monitor=true
                shift
                ;;
            --start-date)
                start_date="$2"
                shift 2
                ;;
            --end-date)
                end_date="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                if [[ " ${spiders[@]} " =~ " $1 " ]]; then
                    spider_name="$1"
                elif [ -n "$1" ]; then
                    echo "❌ Unknown option or spider: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate date format if provided
    if [ -n "$start_date" ] && ! [[ "$start_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "❌ Invalid start date format. Use YYYY-MM-DD"
        exit 1
    fi
    
    if [ -n "$end_date" ] && ! [[ "$end_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "❌ Invalid end date format. Use YYYY-MM-DD"
        exit 1
    fi
    
    # Validate date ranges - warn about future dates
    if [ -n "$start_date" ]; then
        local start_epoch=$(date -d "$start_date" +%s 2>/dev/null || echo "0")
        local today_epoch=$(date +%s)
        if [ $start_epoch -gt $today_epoch ]; then
            echo "⚠️  WARNING: Start date is in the future. No articles may be found."
        fi
    fi
    
    # Start monitoring if requested
    local monitor_pid=0
    if [ "$monitor" = true ]; then
        start_monitoring
        monitor_pid=$?
    fi
    
    # Run spider(s)
    if [ -n "$spider_name" ]; then
        echo "🕷️  Running single spider: $spider_name"
        if [ -n "$start_date" ] || [ -n "$end_date" ]; then
            echo "Date range: ${start_date:-'beginning'} to ${end_date:-'end'}"
        fi
        
        # Check if chunking is needed for single spider
        local chunk_strategy=$(calculate_date_chunks "$start_date" "$end_date" 30)
        if [[ "$chunk_strategy" == chunked:* ]] && [[ -n "$start_date" ]] && [[ -n "$end_date" ]]; then
            local chunk_days=${chunk_strategy#chunked:}
            echo "📅 Large date range detected. Using $chunk_days-day chunks."
            run_spider_chunked "$spider_name" "$start_date" "$end_date" "$chunk_days"
        else
            run_spider "$spider_name" "$start_date" "$end_date"
        fi
    else
        run_all_spiders "$start_date" "$end_date"
    fi
    
    # Stop monitoring if it was started
    if [ $monitor_pid -gt 0 ]; then
        echo "Stopping performance monitor (PID: $monitor_pid)"
        kill $monitor_pid 2>/dev/null
    fi
}

# Run main function with all arguments
main "$@"