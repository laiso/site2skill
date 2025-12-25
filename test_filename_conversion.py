"""
Tests for verifying that HTML to Markdown filename conversion preserves directory structure.

This test validates the fix for the bug where multiple index.html files in different
directories were being overwritten into a single index.md file.
"""
import os
import sys
import tempfile
import shutil

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_html_structure(base_dir):
    """Create a test directory structure with multiple index.html and regular HTML files."""
    # Create test structure:
    # crawl/
    #   example.com/
    #     index.html
    #     page.html
    #     a/
    #       index.html
    #       another.html
    #     b/
    #       c/
    #         index.html
    
    crawl_dir = os.path.join(base_dir, "download", "crawl")
    site_dir = os.path.join(crawl_dir, "example.com")
    
    # Create directories
    os.makedirs(site_dir, exist_ok=True)
    os.makedirs(os.path.join(site_dir, "a"), exist_ok=True)
    os.makedirs(os.path.join(site_dir, "b", "c"), exist_ok=True)
    
    # Create HTML files with simple content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page {}</title></head>
    <body>
        <main>
            <h1>Test Heading {}</h1>
            <p>This is test content for {}.</p>
        </main>
    </body>
    </html>
    """
    
    # Create root index.html
    with open(os.path.join(site_dir, "index.html"), "w") as f:
        f.write(html_content.format("Root", "Root", "root index"))
    
    # Create root page.html
    with open(os.path.join(site_dir, "page.html"), "w") as f:
        f.write(html_content.format("Page", "Page", "page.html"))
    
    # Create a/index.html
    with open(os.path.join(site_dir, "a", "index.html"), "w") as f:
        f.write(html_content.format("A Index", "A Index", "a/index"))
    
    # Create a/another.html
    with open(os.path.join(site_dir, "a", "another.html"), "w") as f:
        f.write(html_content.format("Another", "Another", "a/another.html"))
    
    # Create b/c/index.html
    with open(os.path.join(site_dir, "b", "c", "index.html"), "w") as f:
        f.write(html_content.format("BC Index", "BC Index", "b/c/index"))
    
    return crawl_dir


def test_directory_structure_preserved():
    """Test that directory structure is preserved when converting HTML to MD."""
    print("\n=== Testing Directory Structure Preservation ===")
    
    # Create temporary directory
    temp_base = tempfile.mkdtemp()
    try:
        # Create test HTML structure
        crawl_dir = create_test_html_structure(temp_base)
        print(f"Created test structure in: {temp_base}")
        
        # Run the conversion by simulating the main script flow
        # We'll import and call the relevant parts
        temp_download_dir = os.path.join(temp_base, "download")
        temp_md_dir = os.path.join(temp_base, "markdown")
        os.makedirs(temp_md_dir, exist_ok=True)
        
        import glob
        import datetime
        from site2skill.convert_to_markdown import convert_html_to_md
        from site2skill.utils import sanitize_path, html_to_md_path
        
        # Simulate the conversion logic from main.py
        html_files = glob.glob(os.path.join(crawl_dir, "**/*.html"), recursive=True)
        print(f"Found {len(html_files)} HTML files")
        
        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        for html_file in html_files:
            # Security check
            abs_html_file = os.path.abspath(html_file)
            abs_crawl_dir = os.path.abspath(crawl_dir)
            
            if os.path.commonpath([abs_html_file, abs_crawl_dir]) != abs_crawl_dir:
                continue
            
            # Get relative path
            rel_path = os.path.relpath(html_file, crawl_dir)
            source_url = f"https://{rel_path[:-5] if rel_path.endswith('.html') else rel_path}"
            
            # Apply the fix: preserve directory structure
            md_rel_path = html_to_md_path(rel_path)
            
            # Sanitize path components
            md_rel_path = sanitize_path(md_rel_path)
            md_path = os.path.join(temp_md_dir, md_rel_path)
            
            print(f"Converting: {rel_path} -> {md_rel_path}")
            convert_html_to_md(html_file, md_path, source_url=source_url, fetched_at=fetched_at)
        
        # Verify the output structure
        print("\n=== Verifying Output Structure ===")
        
        # Check that all expected files exist
        expected_files = [
            os.path.join(temp_md_dir, "example.com", "index.md"),
            os.path.join(temp_md_dir, "example.com", "page.md"),
            os.path.join(temp_md_dir, "example.com", "a", "index.md"),
            os.path.join(temp_md_dir, "example.com", "a", "another.md"),
            os.path.join(temp_md_dir, "example.com", "b", "c", "index.md"),
        ]
        
        all_passed = True
        for expected_file in expected_files:
            if os.path.exists(expected_file):
                print(f"✓ PASS: {os.path.relpath(expected_file, temp_md_dir)} exists")
                # Also verify it has content
                with open(expected_file, 'r') as f:
                    content = f.read()
                    if len(content) > 0 and "---" in content:  # Check for frontmatter
                        print(f"  - File has valid content ({len(content)} bytes)")
                    else:
                        print(f"  - WARNING: File may have invalid content")
                        all_passed = False
            else:
                print(f"✗ FAIL: {os.path.relpath(expected_file, temp_md_dir)} does NOT exist")
                all_passed = False
        
        # Count total markdown files
        md_files = glob.glob(os.path.join(temp_md_dir, "**/*.md"), recursive=True)
        print(f"\nTotal markdown files created: {len(md_files)}")
        
        if len(md_files) != len(expected_files):
            print(f"✗ FAIL: Expected {len(expected_files)} files, got {len(md_files)}")
            all_passed = False
        
        if all_passed:
            print("\n🎉 All tests PASSED!")
        else:
            print("\n❌ Some tests FAILED!")
            
        assert all_passed, "Filename conversion tests failed"
            
    finally:
        # Cleanup
        shutil.rmtree(temp_base)
        print(f"\nCleaned up test directory: {temp_base}")


if __name__ == "__main__":
    test_directory_structure_preserved()

