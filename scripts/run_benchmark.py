#!/usr/bin/env python3
"""
Benchmark runner for site2skill - Python vs Rust performance comparison.

This script automates the benchmarking process:
1. Generates test sites of different sizes
2. Runs Python and Rust versions against them
3. Collects timing and memory metrics
4. Compares results and generates a report
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    version: str  # "python" or "rust"
    pages: int
    real_time: float  # seconds
    user_time: float  # seconds
    sys_time: float  # seconds
    max_rss_kb: Optional[int]  # KB, None if not available
    output_files: int
    output_size_bytes: int
    success: bool
    error: Optional[str] = None


def parse_time_output(time_output: str) -> dict:
    """Parse the output of /usr/bin/time -l or time command."""
    result = {}
    
    # macOS /usr/bin/time -l format
    rss_match = re.search(r'maximum resident set size\s*=\s*(\d+)', time_output)
    if rss_match:
        result['max_rss_kb'] = int(rss_match.group(1)) // 1024  # Convert to KB
    else:
        result['max_rss_kb'] = None
    
    # Elapsed time (real)
    elapsed_match = re.search(r'(\d+):(\d+\.\d+) elapsed', time_output)
    if elapsed_match:
        result['real_time'] = int(elapsed_match.group(1)) * 60 + float(elapsed_match.group(2))
    else:
        # Try alternative format
        elapsed_match = re.search(r'(\d+\.\d+) real', time_output)
        if elapsed_match:
            result['real_time'] = float(elapsed_match.group(1))
        else:
            result['real_time'] = 0.0
    
    # CPU time
    user_match = re.search(r'(\d+\.\d+) user', time_output)
    sys_match = re.search(r'(\d+\.\d+) sys', time_output)
    result['user_time'] = float(user_match.group(1)) if user_match else 0.0
    result['sys_time'] = float(sys_match.group(1)) if sys_match else 0.0
    
    return result


def run_benchmark(
    version: str,
    pages: int,
    site_dir: Path,
    output_dir: Path,
    temp_dir: Path,
    executable: str,
    server_port: int = 8888,
    wait: bool = False,
) -> BenchmarkResult:
    """Run a single benchmark."""
    
    print(f"\n{'='*60}")
    print(f"Benchmark: {version.upper()} - {pages} pages")
    print(f"{'='*60}")
    
    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    
    # Clean temp directory
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    
    # Build command
    url = f"http://localhost:{server_port}/"
    cmd = [
        executable,
        url,
        str(output_dir / "test-skill"),
        "--temp-dir", str(temp_dir),
        "--clean",
    ]
    
    if wait:
        # Add delay for fair comparison
        if version == "rust":
            cmd.extend(["--delay-ms", "100"])
    
    print(f"Command: {' '.join(cmd)}")
    
    # Run with timing
    start_time = time.time()
    
    try:
        # Use /usr/bin/time for detailed metrics on macOS
        time_cmd = ["/usr/bin/time", "-l"] + cmd
        result = subprocess.run(
            time_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        
        stderr_output = result.stderr
        stdout_output = result.stdout
        
    except subprocess.TimeoutExpired:
        return BenchmarkResult(
            version=version,
            pages=pages,
            real_time=0,
            user_time=0,
            sys_time=0,
            max_rss_kb=None,
            output_files=0,
            output_size_bytes=0,
            success=False,
            error="Timeout after 10 minutes"
        )
    except Exception as e:
        return BenchmarkResult(
            version=version,
            pages=pages,
            real_time=0,
            user_time=0,
            sys_time=0,
            max_rss_kb=None,
            output_files=0,
            output_size_bytes=0,
            success=False,
            error=str(e)
        )
    
    real_time = time.time() - start_time
    
    # Parse time output
    time_metrics = parse_time_output(stderr_output)
    
    # Count output files
    references_dir = output_dir / "test-skill" / "references"
    if references_dir.exists():
        output_files = len(list(references_dir.glob("*.md")))
    else:
        # Try legacy docs/ directory
        docs_dir = output_dir / "test-skill" / "docs"
        if docs_dir.exists():
            output_files = len(list(docs_dir.glob("*.md")))
        else:
            output_files = 0
    
    # Calculate output size
    output_size = 0
    if references_dir.exists():
        for f in references_dir.glob("*.md"):
            output_size += f.stat().st_size
    elif docs_dir.exists():
        for f in docs_dir.glob("*.md"):
            output_size += f.stat().st_size
    
    success = result.returncode == 0
    
    return BenchmarkResult(
        version=version,
        pages=pages,
        real_time=real_time,
        user_time=time_metrics.get('user_time', 0),
        sys_time=time_metrics.get('sys_time', 0),
        max_rss_kb=time_metrics.get('max_rss_kb'),
        output_files=output_files,
        output_size_bytes=output_size,
        success=success,
        error=None if success else f"Exit code: {result.returncode}"
    )


def start_http_server(site_dir: Path, port: int = 8888) -> subprocess.Popen:
    """Start a local HTTP server for the test site."""
    print(f"Starting HTTP server on port {port}...")
    
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(site_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    
    # Wait for server to start
    time.sleep(1)
    
    # Check if server is running
    if server.poll() is not None:
        raise RuntimeError("Failed to start HTTP server")
    
    return server


def run_benchmarks(
    python_sizes: list[int],
    rust_sizes: list[int],
    site_base: Path,
    results_dir: Path,
    server_port: int = 8888,
    wait: bool = False,
) -> list[BenchmarkResult]:
    """Run all benchmarks."""
    
    all_results = []
    
    # Start HTTP server
    site_dir = site_base / "bench-site"
    server = start_http_server(site_dir, server_port)
    
    try:
        # Run Python benchmarks
        for size in python_sizes:
            # Generate site for this size if needed
            site_path = site_base / f"bench-site-{size}"
            if not site_path.exists():
                print(f"\nGenerating {size}-page test site...")
                subprocess.run(
                    [sys.executable, str(site_base / "generate_bench_site.py"),
                     "--pages", str(size), "--output", str(site_path)],
                    check=True,
                )
            
            result = run_benchmark(
                version="python",
                pages=size,
                site_dir=site_path,
                output_dir=results_dir / f"bench-py-{size}",
                temp_dir=Path(f"/tmp/bench-py-{size}"),
                executable="site2skill",
                server_port=server_port,
                wait=wait,
            )
            all_results.append(result)
            
            # Save individual result
            save_result(result, results_dir / f"python-{size}.txt")
        
        # Run Rust benchmarks
        for size in rust_sizes:
            # Generate site for this size if needed
            site_path = site_base / f"bench-site-{size}"
            if not site_path.exists():
                print(f"\nGenerating {size}-page test site...")
                subprocess.run(
                    [sys.executable, str(site_base / "generate_bench_site.py"),
                     "--pages", str(size), "--output", str(site_path)],
                    check=True,
                )
            
            result = run_benchmark(
                version="rust",
                pages=size,
                site_dir=site_path,
                output_dir=results_dir / f"bench-rs-{size}",
                temp_dir=Path(f"/tmp/bench-rs-{size}"),
                executable="./target/release/site2skill",
                server_port=server_port,
                wait=wait,
            )
            all_results.append(result)
            
            # Save individual result
            save_result(result, results_dir / f"rust-{size}.txt")
    
    finally:
        # Stop HTTP server
        server.terminate()
        server.wait()
        print("\nHTTP server stopped")
    
    return all_results


def save_result(result: BenchmarkResult, filepath: Path) -> None:
    """Save benchmark result to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        f.write(f"Version: {result.version}\n")
        f.write(f"Pages: {result.pages}\n")
        f.write(f"Real Time: {result.real_time:.2f}s\n")
        f.write(f"User Time: {result.user_time:.2f}s\n")
        f.write(f"Sys Time: {result.sys_time:.2f}s\n")
        f.write(f"Max RSS: {result.max_rss_kb} KB\n" if result.max_rss_kb else "Max RSS: N/A\n")
        f.write(f"Output Files: {result.output_files}\n")
        f.write(f"Output Size: {result.output_size_bytes / 1024:.1f} KB\n")
        f.write(f"Success: {result.success}\n")
        if result.error:
            f.write(f"Error: {result.error}\n")


def generate_report(results: list[BenchmarkResult], results_dir: Path) -> None:
    """Generate a comparison report."""
    
    report_path = results_dir / "benchmark_report.md"
    
    # Group results by size
    by_size = {}
    for r in results:
        if r.pages not in by_size:
            by_size[r.pages] = {}
        by_size[r.pages][r.version] = r
    
    with open(report_path, 'w') as f:
        f.write("# Benchmark Results: Python vs Rust\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Time comparison table
        f.write("## Execution Time Comparison\n\n")
        f.write("| Pages | Python (s) | Rust (s) | Speedup |\n")
        f.write("|-------|------------|----------|---------|\n")
        
        for size in sorted(by_size.keys()):
            py = by_size[size].get("python")
            rs = by_size[size].get("rust")
            
            if py and rs:
                speedup = py.real_time / rs.real_time if rs.real_time > 0 else 0
                f.write(f"| {size} | {py.real_time:.2f} | {rs.real_time:.2f} | {speedup:.2f}x |\n")
            elif py:
                f.write(f"| {size} | {py.real_time:.2f} | - | - |\n")
            elif rs:
                f.write(f"| {size} | - | {rs.real_time:.2f} | - |\n")
        
        # Memory comparison table
        f.write("\n## Memory Usage Comparison\n\n")
        f.write("| Pages | Python (KB) | Rust (KB) | Ratio |\n")
        f.write("|-------|-------------|-----------|-------|\n")
        
        for size in sorted(by_size.keys()):
            py = by_size[size].get("python")
            rs = by_size[size].get("rust")
            
            if py and rs and py.max_rss_kb and rs.max_rss_kb:
                ratio = py.max_rss_kb / rs.max_rss_kb if rs.max_rss_kb > 0 else 0
                f.write(f"| {size} | {py.max_rss_kb} | {rs.max_rss_kb} | {ratio:.2f}x |\n")
            elif py and py.max_rss_kb:
                f.write(f"| {size} | {py.max_rss_kb} | - | - |\n")
            elif rs and rs.max_rss_kb:
                f.write(f"| {size} | - | {rs.max_rss_kb} | - |\n")
        
        # Output validation
        f.write("\n## Output Validation\n\n")
        f.write("| Pages | Python Files | Rust Files | Python Size | Rust Size |\n")
        f.write("|-------|--------------|------------|-------------|-----------|\n")
        
        for size in sorted(by_size.keys()):
            py = by_size[size].get("python")
            rs = by_size[size].get("rust")
            
            py_size = f"{py.output_size_bytes / 1024:.1f} KB" if py else "-"
            rs_size = f"{rs.output_size_bytes / 1024:.1f} KB" if rs else "-"
            
            f.write(f"| {size} | {py.output_files if py else '-'} | {rs.output_files if rs else '-'} | {py_size} | {rs_size} |\n")
        
        # Summary
        f.write("\n## Summary\n\n")
        
        rust_faster = []
        for size, versions in by_size.items():
            if "python" in versions and "rust" in versions:
                py = versions["python"]
                rs = versions["rust"]
                if py.real_time > 0 and rs.real_time > 0:
                    speedup = py.real_time / rs.real_time
                    rust_faster.append((size, speedup))
        
        if rust_faster:
            avg_speedup = sum(s for _, s in rust_faster) / len(rust_faster)
            f.write(f"Rust is **{avg_speedup:.2f}x** faster on average.\n\n")
            
            for size, speedup in rust_faster:
                f.write(f"- {size} pages: **{speedup:.2f}x** speedup\n")
    
    print(f"\nReport saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark runner for site2skill Python vs Rust"
    )
    parser.add_argument(
        "--python-sizes",
        type=int,
        nargs="+",
        default=[10, 100, 500],
        help="Page counts for Python benchmarks (default: 10 100 500)"
    )
    parser.add_argument(
        "--rust-sizes",
        type=int,
        nargs="+",
        default=[10, 100, 500],
        help="Page counts for Rust benchmarks (default: 10 100 500)"
    )
    parser.add_argument(
        "--site-base",
        type=str,
        default="bench-site",
        help="Base directory for test sites (default: bench-site)"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="bench-results",
        help="Directory for benchmark results (default: bench-results)"
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=8888,
        help="HTTP server port (default: 8888)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Add delay between requests for fair comparison"
    )
    parser.add_argument(
        "--rust-only",
        action="store_true",
        help="Run only Rust benchmarks"
    )
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Run only Python benchmarks"
    )
    
    args = parser.parse_args()
    
    site_base = Path(args.site_base)
    results_dir = Path(args.results_dir)
    
    # Check prerequisites
    if not args.python_only:
        rust_binary = Path("target/release/site2skill")
        if not rust_binary.exists():
            print("Rust binary not found. Building...")
            subprocess.run(["cargo", "build", "--release"], check=True)
    
    # Run benchmarks
    results = []
    
    if not args.rust_only:
        print("\n" + "="*60)
        print("Running Python Benchmarks")
        print("="*60)
        for size in args.python_sizes:
            site_path = site_base / f"bench-site-{size}"
            if not site_path.exists():
                print(f"\nGenerating {size}-page test site...")
                subprocess.run(
                    [sys.executable, "scripts/generate_bench_site.py",
                     "--pages", str(size), "--output", str(site_path)],
                    check=True,
                )
            
            result = run_benchmark(
                version="python",
                pages=size,
                site_dir=site_path,
                output_dir=results_dir / f"bench-py-{size}",
                temp_dir=Path(f"/tmp/bench-py-{size}"),
                executable="site2skill",
                server_port=args.server_port,
                wait=args.wait,
            )
            results.append(result)
            save_result(result, results_dir / f"python-{size}.txt")
    
    if not args.python_only:
        print("\n" + "="*60)
        print("Running Rust Benchmarks")
        print("="*60)
        for size in args.rust_sizes:
            site_path = site_base / f"bench-site-{size}"
            if not site_path.exists():
                print(f"\nGenerating {size}-page test site...")
                subprocess.run(
                    [sys.executable, "scripts/generate_bench_site.py",
                     "--pages", str(size), "--output", str(site_path)],
                    check=True,
                )
            
            result = run_benchmark(
                version="rust",
                pages=size,
                site_dir=site_path,
                output_dir=results_dir / f"bench-rs-{size}",
                temp_dir=Path(f"/tmp/bench-rs-{size}"),
                executable="./target/release/site2skill",
                server_port=args.server_port,
                wait=args.wait,
            )
            results.append(result)
            save_result(result, results_dir / f"rust-{size}.txt")
    
    # Generate report
    generate_report(results, results_dir)
    
    print("\n" + "="*60)
    print("Benchmark Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
