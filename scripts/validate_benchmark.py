#!/usr/bin/env python3
"""
Validate and compare benchmark outputs between Python and Rust versions.

This script:
1. Compares file counts between Python and Rust outputs
2. Checks structural similarity of generated markdown
3. Reports any significant differences
"""

import argparse
import difflib
import os
from pathlib import Path


def count_md_files(directory: Path) -> int:
    """Count markdown files in references or docs directory."""
    references_dir = directory / "references"
    docs_dir = directory / "docs"
    
    if references_dir.exists():
        return len(list(references_dir.glob("*.md")))
    elif docs_dir.exists():
        return len(list(docs_dir.glob("*.md")))
    else:
        return 0


def get_md_files(directory: Path) -> list[Path]:
    """Get list of markdown files."""
    references_dir = directory / "references"
    docs_dir = directory / "docs"
    
    if references_dir.exists():
        return sorted(references_dir.glob("*.md"))
    elif docs_dir.exists():
        return sorted(docs_dir.glob("*.md"))
    else:
        return []


def read_file_head(filepath: Path, lines: int = 20) -> list[str]:
    """Read first N lines of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [next(f) for _ in range(lines)]
    except (StopIteration, FileNotFoundError):
        return []


def normalize_content(lines: list[str]) -> str:
    """Normalize content for comparison (remove timestamps, paths, etc.)."""
    normalized = []
    for line in lines:
        # Remove or normalize variable content
        # Keep structure but ignore minor differences
        normalized.append(line)
    return ''.join(normalized)


def compare_files(file1: Path, file2: Path, name1: str, name2: str) -> dict:
    """Compare two markdown files."""
    lines1 = read_file_head(file1)
    lines2 = read_file_head(file2)
    
    content1 = normalize_content(lines1)
    content2 = normalize_content(lines2)
    
    # Calculate similarity
    similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
    
    # Generate diff if significantly different
    diff = []
    if similarity < 0.9:
        diff = list(difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f"{name1}/{file1.name}",
            tofile=f"{name2}/{file2.name}",
            n=5
        ))
    
    return {
        'file1': str(file1),
        'file2': str(file2),
        'similarity': similarity,
        'diff': diff,
    }


def validate_benchmark(
    python_dir: Path,
    rust_dir: Path,
    size: int,
    verbose: bool = False,
) -> dict:
    """Validate benchmark outputs."""
    
    result = {
        'size': size,
        'python_files': 0,
        'rust_files': 0,
        'file_match': False,
        'comparisons': [],
        'avg_similarity': 0.0,
    }
    
    # Count files
    result['python_files'] = count_md_files(python_dir)
    result['rust_files'] = count_md_files(rust_dir)
    result['file_match'] = result['python_files'] == result['rust_files']
    
    # Get file lists
    py_files = get_md_files(python_dir)
    rs_files = get_md_files(rust_dir)
    
    if not py_files or not rs_files:
        return result
    
    # Compare files (match by filename when possible)
    py_by_name = {f.name: f for f in py_files}
    rs_by_name = {f.name: f for f in rs_files}
    
    common_names = set(py_by_name.keys()) & set(rs_by_name.keys())
    
    if not common_names:
        # No common filenames, compare by position
        min_len = min(len(py_files), len(rs_files))
        comparisons = min(5, min_len)  # Compare up to 5 files
        
        for i in range(comparisons):
            comparison = compare_files(
                py_files[i], rs_files[i],
                "Python", "Rust"
            )
            result['comparisons'].append(comparison)
    else:
        # Compare files with matching names
        comparisons = min(5, len(common_names))
        for name in list(common_names)[:comparisons]:
            comparison = compare_files(
                py_by_name[name], rs_by_name[name],
                "Python", "Rust"
            )
            result['comparisons'].append(comparison)
    
    # Calculate average similarity
    if result['comparisons']:
        result['avg_similarity'] = sum(
            c['similarity'] for c in result['comparisons']
        ) / len(result['comparisons'])
    
    return result


def print_report(results: list[dict], verbose: bool = False) -> None:
    """Print validation report."""
    
    print("\n" + "="*60)
    print("Benchmark Output Validation Report")
    print("="*60)
    
    for result in results:
        print(f"\n### {result['size']} pages")
        print(f"  Python files: {result['python_files']}")
        print(f"  Rust files:   {result['rust_files']}")
        print(f"  File count match: {'✓' if result['file_match'] else '✗'}")
        
        if result['comparisons']:
            print(f"  Average similarity: {result['avg_similarity']*100:.1f}%")
            
            if verbose:
                for comp in result['comparisons']:
                    print(f"\n  File: {comp['file1']}")
                    print(f"  Similarity: {comp['similarity']*100:.1f}%")
                    
                    if comp['diff']:
                        print("  Differences:")
                        for line in comp['diff'][:10]:
                            print(f"    {line.rstrip()}")
                        if len(comp['diff']) > 10:
                            print(f"    ... and {len(comp['diff']) - 10} more lines")
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_match = all(r['file_match'] for r in results)
    avg_sim = sum(r['avg_similarity'] for r in results if r['comparisons'])
    avg_sim /= len([r for r in results if r['comparisons']]) if any(r['comparisons'] for r in results) else 0
    
    print(f"All file counts match: {'✓' if all_match else '✗'}")
    print(f"Average content similarity: {avg_sim*100:.1f}%")
    
    if avg_sim > 0.8:
        print("\n✓ Outputs are structurally similar")
    else:
        print("\n⚠ Outputs show significant differences (expected due to different converters)")


def main():
    parser = argparse.ArgumentParser(
        description="Validate benchmark outputs between Python and Rust versions"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="bench-results",
        help="Directory containing benchmark results (default: bench-results)"
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[10, 100, 500],
        help="Page sizes to validate (default: 10 100 500)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed diff output"
    )
    
    args = parser.parse_args()
    
    results_dir = Path(args.results_dir)
    results = []
    
    for size in args.sizes:
        python_dir = results_dir / f"bench-py-{size}" / "test-skill"
        rust_dir = results_dir / f"bench-rs-{size}" / "test-skill"
        
        if not python_dir.exists() and not rust_dir.exists():
            print(f"Skipping {size} pages: No benchmark data found")
            continue
        
        result = validate_benchmark(python_dir, rust_dir, size, args.verbose)
        results.append(result)
    
    print_report(results, args.verbose)
    
    # Save report
    report_path = results_dir / "validation_report.txt"
    with open(report_path, 'w') as f:
        for result in results:
            f.write(f"Size: {result['size']} pages\n")
            f.write(f"  Python files: {result['python_files']}\n")
            f.write(f"  Rust files: {result['rust_files']}\n")
            f.write(f"  Match: {result['file_match']}\n")
            f.write(f"  Similarity: {result['avg_similarity']*100:.1f}%\n\n")
    
    print(f"\nValidation report saved to: {report_path}")


if __name__ == "__main__":
    main()
