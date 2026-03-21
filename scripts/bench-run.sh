#!/usr/bin/env bash
#
# Quick benchmark runner for site2skill
# Usage: ./scripts/bench-run.sh [python|rust|both] [size]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/bench-results"
SITE_BASE="$PROJECT_ROOT/bench-site"

# Default values
RUN_MODE="${1:-both}"
SIZE="${2:-100}"
PORT="${PORT:-8888}"

echo "========================================"
echo "site2skill Benchmark Runner"
echo "========================================"
echo "Mode: $RUN_MODE"
echo "Size: $SIZE pages"
echo "Port: $PORT"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Generate test site if needed
generate_site() {
    local size=$1
    local site_path="$SITE_BASE-$size"
    
    if [ ! -d "$site_path" ]; then
        echo "Generating $size-page test site..."
        python3 "$SCRIPT_DIR/generate_bench_site.py" --pages "$size" --output "$site_path"
    fi
}

# Start HTTP server
start_server() {
    local site_path=$1
    echo "Starting HTTP server on port $PORT..."
    python3 -m http.server "$PORT" --directory "$site_path" &
    SERVER_PID=$!
    sleep 1
    
    # Check if server started
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Failed to start server"
        exit 1
    fi
    echo "Server started (PID: $SERVER_PID)"
}

# Stop HTTP server
stop_server() {
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
        echo "Server stopped"
    fi
}

trap stop_server EXIT

# Run Python benchmark
run_python() {
    local size=$1
    local site_path="$SITE_BASE-$size"
    local output_dir="$RESULTS_DIR/bench-py-$size"
    local temp_dir="/tmp/bench-py-$size"
    local time_file="$RESULTS_DIR/python-$size.time.txt"
    
    echo ""
    echo "=== Python: $size pages ==="
    
    generate_site $size
    start_server "$site_path"
    
    # Clean output
    rm -rf "$output_dir" "$temp_dir"
    mkdir -p "$output_dir"
    
    # Run with timing
    if command -v /usr/bin/time &> /dev/null; then
        /usr/bin/time -l site2skill "http://localhost:$PORT/" "$output_dir/test-skill" \
            --temp-dir "$temp_dir" --clean \
            2> "$time_file"
    else
        time site2skill "http://localhost:$PORT/" "$output_dir/test-skill" \
            --temp-dir "$temp_dir" --clean \
            2>&1 | tee "$time_file"
    fi
    
    # Count results
    local ref_dir="$output_dir/test-skill/references"
    if [ -d "$ref_dir" ]; then
        local file_count=$(find "$ref_dir" -name '*.md' | wc -l | tr -d ' ')
        local total_size=$(du -sh "$ref_dir" | cut -f1)
        echo "Output: $file_count files, $total_size"
    fi
    
    stop_server
}

# Run Rust benchmark
run_rust() {
    local size=$1
    local site_path="$SITE_BASE-$size"
    local output_dir="$RESULTS_DIR/bench-rs-$size"
    local temp_dir="/tmp/bench-rs-$size"
    local time_file="$RESULTS_DIR/rust-$size.time.txt"
    
    echo ""
    echo "=== Rust: $size pages ==="
    
    # Build if needed
    if [ ! -f "$PROJECT_ROOT/target/release/site2skill" ]; then
        echo "Building Rust binary..."
        cargo build --release
    fi
    
    generate_site $size
    start_server "$site_path"
    
    # Clean output
    rm -rf "$output_dir" "$temp_dir"
    mkdir -p "$output_dir"
    
    # Run with timing
    if command -v /usr/bin/time &> /dev/null; then
        /usr/bin/time -l "$PROJECT_ROOT/target/release/site2skill" "http://localhost:$PORT/" "$output_dir/test-skill" \
            --temp-dir "$temp_dir" --clean \
            2> "$time_file"
    else
        time "$PROJECT_ROOT/target/release/site2skill" "http://localhost:$PORT/" "$output_dir/test-skill" \
            --temp-dir "$temp_dir" --clean \
            2>&1 | tee "$time_file"
    fi
    
    # Count results
    local ref_dir="$output_dir/test-skill/references"
    if [ -d "$ref_dir" ]; then
        local file_count=$(find "$ref_dir" -name '*.md' | wc -l | tr -d ' ')
        local total_size=$(du -sh "$ref_dir" | cut -f1)
        echo "Output: $file_count files, $total_size"
    fi
    
    stop_server
}

# Compare results
compare_results() {
    local size=$1
    
    echo ""
    echo "=== Comparison: $size pages ==="
    
    local py_time_file="$RESULTS_DIR/python-$size.time.txt"
    local rs_time_file="$RESULTS_DIR/rust-$size.time.txt"
    
    if [ -f "$py_time_file" ] && [ -f "$rs_time_file" ]; then
        echo "Python time file: $py_time_file"
        echo "Rust time file: $rs_time_file"
        
        # Extract max RSS if available (macOS format)
        local py_rss=$(grep "maximum resident set size" "$py_time_file" | awk '{print $NF}' || echo "N/A")
        local rs_rss=$(grep "maximum resident set size" "$rs_time_file" | awk '{print $NF}' || echo "N/A")
        
        echo "Python Max RSS: $py_rss"
        echo "Rust Max RSS: $rs_rss"
    fi
}

# Main execution
case "$RUN_MODE" in
    python)
        run_python "$SIZE"
        ;;
    rust)
        run_rust "$SIZE"
        ;;
    both)
        run_python "$SIZE"
        run_rust "$SIZE"
        compare_results "$SIZE"
        ;;
    *)
        echo "Unknown mode: $RUN_MODE"
        echo "Usage: $0 [python|rust|both] [size]"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "Benchmark complete!"
echo "Results saved to: $RESULTS_DIR"
echo "========================================"
