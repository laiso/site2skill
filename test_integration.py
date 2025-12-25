"""
End-to-end integration test for the site2skill pipeline.

This test validates that the entire pipeline preserves directory structure
from HTML download through final skill generation.
"""
import os
import tempfile
import shutil
import sys
import glob

# Add the package to path
sys.path.insert(0, '/home/runner/work/site2skill/site2skill')

from site2skill.convert_to_markdown import convert_html_to_md
from site2skill.generate_skill_structure import generate_skill_structure
from site2skill.normalize_markdown import normalize_markdown
import re
import datetime


def create_test_site():
    """Create a realistic test site structure with multiple index.html files."""
    temp_base = tempfile.mkdtemp()
    crawl_dir = os.path.join(temp_base, "download", "crawl")
    site_dir = os.path.join(crawl_dir, "docs.example.com")
    
    # Create realistic directory structure
    dirs = [
        "",
        "getting-started",
        "api",
        "api/reference",
        "guides",
        "guides/advanced",
    ]
    
    for d in dirs:
        os.makedirs(os.path.join(site_dir, d), exist_ok=True)
    
    # Create HTML files
    html_template = """<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
    <main>
        <h1>{title}</h1>
        <p>This is the documentation for {path}.</p>
        <h2>Overview</h2>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
    </main>
</body>
</html>"""
    
    test_files = [
        ("index.html", "Home", ""),
        ("getting-started/index.html", "Getting Started", "getting-started"),
        ("getting-started/installation.html", "Installation", "getting-started"),
        ("api/index.html", "API Overview", "api"),
        ("api/authentication.html", "Authentication", "api"),
        ("api/reference/index.html", "API Reference", "api/reference"),
        ("api/reference/users.html", "Users API", "api/reference"),
        ("guides/index.html", "Guides", "guides"),
        ("guides/quickstart.html", "Quickstart Guide", "guides"),
        ("guides/advanced/index.html", "Advanced Topics", "guides/advanced"),
    ]
    
    for filename, title, subdir in test_files:
        full_path = os.path.join(site_dir, filename)
        with open(full_path, "w") as f:
            f.write(html_template.format(title=title, path=filename))
    
    return temp_base, crawl_dir


def run_conversion_pipeline(crawl_dir, temp_base):
    """Run the conversion pipeline simulating main.py logic."""
    temp_md_dir = os.path.join(temp_base, "markdown")
    os.makedirs(temp_md_dir, exist_ok=True)
    
    # Find all HTML files
    html_files = glob.glob(os.path.join(crawl_dir, "**/*.html"), recursive=True)
    
    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    for html_file in html_files:
        # Get relative path
        abs_html_file = os.path.abspath(html_file)
        abs_crawl_dir = os.path.abspath(crawl_dir)
        
        if os.path.commonpath([abs_html_file, abs_crawl_dir]) != abs_crawl_dir:
            continue
        
        rel_path = os.path.relpath(html_file, crawl_dir)
        source_url = f"https://{rel_path[:-5] if rel_path.endswith('.html') else rel_path}"
        
        # Apply the fix: preserve directory structure
        if rel_path.endswith('.html'):
            md_rel_path = rel_path[:-5] + '.md'
        else:
            md_rel_path = rel_path + '.md'
        
        # Sanitize path components
        path_parts = md_rel_path.split(os.sep)
        sanitized_parts = [re.sub(r'[^a-zA-Z0-9._-]', '_', part) for part in path_parts]
        md_rel_path = os.path.join(*sanitized_parts) if sanitized_parts else md_rel_path
        md_path = os.path.join(temp_md_dir, md_rel_path)
        
        # Convert
        convert_html_to_md(html_file, md_path, source_url=source_url, fetched_at=fetched_at)
    
    # Normalize
    md_files = glob.glob(os.path.join(temp_md_dir, "**/*.md"), recursive=True)
    for md_file in md_files:
        normalize_markdown(md_file, md_file)
    
    return temp_md_dir


def verify_results(skill_dir):
    """Verify the final skill structure."""
    docs_dir = os.path.join(skill_dir, "docs")
    
    # Expected files based on our test structure
    expected_files = [
        "docs.example.com/index.md",
        "docs.example.com/getting-started/index.md",
        "docs.example.com/getting-started/installation.md",
        "docs.example.com/api/index.md",
        "docs.example.com/api/authentication.md",
        "docs.example.com/api/reference/index.md",
        "docs.example.com/api/reference/users.md",
        "docs.example.com/guides/index.md",
        "docs.example.com/guides/quickstart.md",
        "docs.example.com/guides/advanced/index.md",
    ]
    
    all_passed = True
    
    print("\n=== Verifying Final Skill Structure ===")
    for expected in expected_files:
        expected_path = os.path.join(docs_dir, expected)
        if os.path.exists(expected_path):
            # Verify content
            with open(expected_path, 'r') as f:
                content = f.read()
                if "---" in content and "title:" in content:
                    print(f"✓ PASS: {expected}")
                else:
                    print(f"✗ FAIL: {expected} has invalid content")
                    all_passed = False
        else:
            print(f"✗ FAIL: {expected} does NOT exist")
            all_passed = False
    
    # Count index.md files
    all_files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)
    index_files = [f for f in all_files if f.endswith("index.md")]
    
    print(f"\nTotal files in docs/: {len(all_files)}")
    print(f"Index.md files: {len(index_files)}")
    
    # We should have 6 different index.md files
    if len(index_files) != 6:
        print(f"✗ FAIL: Expected 6 index.md files, got {len(index_files)}")
        all_passed = False
    else:
        print("✓ PASS: Correct number of index.md files")
    
    # Verify SKILL.md exists
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_md):
        print("✓ PASS: SKILL.md exists")
    else:
        print("✗ FAIL: SKILL.md does not exist")
        all_passed = False
    
    return all_passed


def main():
    """Run the end-to-end integration test."""
    print("=== End-to-End Integration Test ===")
    
    # Create test site
    print("\n1. Creating test site structure...")
    temp_base, crawl_dir = create_test_site()
    print(f"   Test directory: {temp_base}")
    
    try:
        # Run conversion
        print("\n2. Running HTML to Markdown conversion...")
        temp_md_dir = run_conversion_pipeline(crawl_dir, temp_base)
        print(f"   Converted to: {temp_md_dir}")
        
        # Generate skill structure
        print("\n3. Generating skill structure...")
        output_base = os.path.join(temp_base, "skills")
        skill_name = "example-docs"
        generate_skill_structure(skill_name, temp_md_dir, output_base)
        skill_dir = os.path.join(output_base, skill_name)
        print(f"   Skill directory: {skill_dir}")
        
        # Verify results
        print("\n4. Verifying results...")
        success = verify_results(skill_dir)
        
        if success:
            print("\n🎉 All integration tests PASSED!")
            print("\nThe fix successfully preserves directory structure throughout the entire pipeline:")
            print("  ✓ Multiple index.html files are kept separate")
            print("  ✓ Directory structure is preserved in markdown conversion")
            print("  ✓ Directory structure is preserved in final skill structure")
            return 0
        else:
            print("\n❌ Some integration tests FAILED!")
            return 1
    
    finally:
        # Cleanup
        shutil.rmtree(temp_base)
        print(f"\nCleaned up test directory: {temp_base}")


if __name__ == "__main__":
    sys.exit(main())
