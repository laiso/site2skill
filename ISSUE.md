# Why: Python to Rust Rewrite

## Motivation

Rewrite the Python implementation of site2skill in Rust.

### 1. Performance

The Python version takes over 15 minutes to process large documentation sites (500+ pages). HTTP fetching uses the external `wget` command for sequential downloads, and HTML-to-Markdown conversion processes files one at a time with no parallelism.

Rust's async/await with tokio enables semaphore-controlled concurrent HTTP fetching and native-code conversion for faster processing.

**Measured results (100 pages, conversion pipeline only with `--skip-fetch`):**

| | Python | Rust | Ratio |
|---|--------|------|-------|
| Wall time | 0.77s | 0.15s | **5.1x** |
| Peak memory | 34MB | 11MB | 3.1x |

### 2. Simpler distribution

The Python version requires Python 3.10+ and wget, which needs separate installation on macOS/Windows.

The Rust version ships as a single binary with no runtime dependencies. PyPI distribution uses the [sqlite-scanner pattern](https://simonwillison.net/2026/Feb/4/distributing-go-binaries/) to bundle the binary inside a wheel, so `pip install site2skill` is all that's needed.

### 3. Remove wget dependency

The Python version shells out to `wget` for HTTP crawling, offering limited control over robots.txt handling and crawl scope. The Rust version uses reqwest with a custom crawler that handles robots.txt compliance, depth control, concurrency limits, and URL scope filtering entirely in code.

## Scope

- Delete the Python implementation (`site2skill/` directory, `test_*.py`)
- Reimplement equivalent functionality in Rust (`src/`)
- Add a Python wrapper for PyPI distribution (`python/`)
- Maintain CLI interface compatibility
