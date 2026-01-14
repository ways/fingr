#!/bin/sh
set -e

CACHE_DIR="${CACHE_DIR:-/app/data}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-24}"
MIN_FREE_PERCENT="${MIN_FREE_PERCENT:-10}"

echo "Starting cache cleanup for $CACHE_DIR"
echo "Max age: ${MAX_AGE_HOURS}h, Min free space: ${MIN_FREE_PERCENT}%"

# Remove files older than MAX_AGE_HOURS
if [ -d "$CACHE_DIR" ]; then
    echo "Removing files older than ${MAX_AGE_HOURS} hours..."
    # Use -mmin for minutes (hours * 60)
    MAX_AGE_MINUTES=$((MAX_AGE_HOURS * 60))
    find "$CACHE_DIR" -type f -mmin "+$MAX_AGE_MINUTES" -delete 2>/dev/null || true

    # Debug: Show full df output
    echo "=== df output ==="
    df "$CACHE_DIR"
    echo "================="

    # Check disk usage - use df -k for consistent output
    # Output format: Filesystem 1K-blocks Used Available Use% Mounted
    DISK_LINE=$(df -k "$CACHE_DIR" | tail -1)

    # Extract fields - some df outputs have the filesystem on a separate line
    # So we need to handle both cases
    FIELD_COUNT=$(echo "$DISK_LINE" | awk '{print NF}')

    if [ "$FIELD_COUNT" -eq 6 ]; then
        # Normal format: Filesystem 1K-blocks Used Available Use% Mounted
        TOTAL=$(echo "$DISK_LINE" | awk '{print $2}')
        USED=$(echo "$DISK_LINE" | awk '{print $3}')
        AVAIL=$(echo "$DISK_LINE" | awk '{print $4}')
        USE_PCT=$(echo "$DISK_LINE" | awk '{print $5}' | tr -d '%')
    elif [ "$FIELD_COUNT" -eq 5 ]; then
        # Wrapped format: 1K-blocks Used Available Use% Mounted
        TOTAL=$(echo "$DISK_LINE" | awk '{print $1}')
        USED=$(echo "$DISK_LINE" | awk '{print $2}')
        AVAIL=$(echo "$DISK_LINE" | awk '{print $3}')
        USE_PCT=$(echo "$DISK_LINE" | awk '{print $4}' | tr -d '%')
    else
        echo "Unexpected df output format (field count: $FIELD_COUNT)"
        echo "Line: $DISK_LINE"
        exit 1
    fi

    # Validate we got numbers
    TOTAL=$(echo "$TOTAL" | tr -cd '0-9')
    USED=$(echo "$USED" | tr -cd '0-9')
    AVAIL=$(echo "$AVAIL" | tr -cd '0-9')
    USE_PCT=$(echo "$USE_PCT" | tr -cd '0-9')

    if [ -z "$TOTAL" ] || [ "$TOTAL" -eq 0 ]; then
        echo "Error: Invalid disk space values"
        exit 1
    fi

    # Calculate free percentage
    FREE_PERCENT=$((100 - USE_PCT))

    echo "Disk usage: Total=${TOTAL}K, Used=${USED}K, Available=${AVAIL}K"
    echo "Usage: ${USE_PCT}% used, ${FREE_PERCENT}% free"

    # Compare percentages
    if [ "$FREE_PERCENT" -lt "$MIN_FREE_PERCENT" ]; then
        echo "Low disk space detected (${FREE_PERCENT}% < ${MIN_FREE_PERCENT}%)! Removing oldest files..."

        # Count files
        FILE_COUNT=$(find "$CACHE_DIR" -type f | wc -l)

        if [ "$FILE_COUNT" -gt 0 ]; then
            # Calculate 20% of files to remove (add 1 to ensure at least one file)
            REMOVE_COUNT=$((FILE_COUNT * 20 / 100 + 1))
            echo "Found $FILE_COUNT files, removing oldest $REMOVE_COUNT files..."

            # List files with modification time and sort
            # Alpine's find may not have -printf, so use a more portable approach
            find "$CACHE_DIR" -type f -exec stat -c '%Y %n' {} \; 2>/dev/null | \
                sort -n | \
                head -n "$REMOVE_COUNT" | \
                cut -d' ' -f2- | \
                while read -r file; do
                    if [ -f "$file" ]; then
                        rm -f "$file"
                        echo "Removed: $file"
                    fi
                done

            echo "Cleanup complete"
        else
            echo "No files to remove (directory is empty)"
        fi
    else
        echo "Sufficient free space available (${FREE_PERCENT}% >= ${MIN_FREE_PERCENT}%)"
    fi
else
    echo "Cache directory $CACHE_DIR not found"
fi
