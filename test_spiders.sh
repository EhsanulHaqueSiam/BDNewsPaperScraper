#!/bin/bash
# test_spiders.sh

echo "🕷️  Starting comprehensive spider test (Limit: 2 items/spider)..."
echo "------------------------------------------------------------"

failed_spiders=()
passed_spiders=()
no_items_spiders=()

# Get list of spiders (ignoring 'Bytecode compiled' lines)
spiders=$(uv run scrapy list 2>/dev/null | grep -v "Bytecode")

count=0
total=$(echo "$spiders" | wc -w)

for spider in $spiders; do
    ((count++))
    echo -n "[$count/$total] Testing $spider... "
    
    # Run spider with 2 item limit and minimal logging, capture output
    # We use a timeout of 60s to prevent hang-ups
    # Use a temporary database to avoid duplicate URL drops from previous runs
    output=$(timeout 60s uv run scrapy crawl "$spider" -s CLOSESPIDER_ITEMCOUNT=2 -s LOG_LEVEL=INFO -s DATABASE_PATH=test_results.db 2>&1)
    exit_code=$?
    
    if [ $exit_code -eq 124 ]; then
        echo "⏰ TIMEOUT"
        failed_spiders+=("$spider (Timeout)")
        continue
    fi

    # Check for item count in stats
    # We look for 'item_scraped_count' in the output (since we are redirecting stderr to stdout, and scrapy stats are printed there)
     item_count=$(echo "$output" | grep "'item_scraped_count':" | awk -F': ' '{print $2}' | tr -d '},')

    
    if [[ "$output" == *"Traceback"* ]]; then
        echo "❌ CRASHED"
        failed_spiders+=("$spider (Crash)")
    elif [ -n "$item_count" ] && [ "$item_count" -gt 0 ]; then
        echo "✅ PASSED ($item_count items)"
        passed_spiders+=("$spider")
    else
        echo "⚠️  NO ITEMS"
        no_items_spiders+=("$spider")
    fi
done

echo "------------------------------------------------------------"
echo "🎉 Testing Complete!"
echo "✅ Passed: ${#passed_spiders[@]}"
echo "⚠️  No Items: ${#no_items_spiders[@]}"
echo "❌ Failed: ${#failed_spiders[@]}"
echo ""

if [ ${#no_items_spiders[@]} -gt 0 ]; then
    echo "⚠️  Spiders with 0 items:"
    printf '%s\n' "${no_items_spiders[@]}"
    echo ""
fi

if [ ${#failed_spiders[@]} -gt 0 ]; then
    echo "❌ Failed Spiders:"
    printf '%s\n' "${failed_spiders[@]}"
fi
