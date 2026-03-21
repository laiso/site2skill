#!/usr/bin/env python3
"""
Generate a static documentation website for benchmarking site2skill.

Creates a realistic documentation site with:
- Main index page
- Multiple documentation pages with headings, paragraphs, code blocks, and links
- Inter-page linking for crawler testing
- Consistent structure across all pages
"""

import argparse
import os
import random
from pathlib import Path


def generate_page_content(page_num: int, total_pages: int, all_page_nums: list[int]) -> str:
    """Generate realistic documentation content for a page."""
    
    topics = [
        "Getting Started",
        "Installation",
        "Configuration",
        "API Reference",
        "Usage Guide",
        "Best Practices",
        "Troubleshooting",
        "Advanced Topics",
        "Examples",
        "FAQ",
    ]
    
    topic = topics[page_num % len(topics)]
    
    # Generate related links (link to nearby pages for realistic structure)
    related_pages = []
    for i in range(min(3, total_pages)):
        related_idx = (page_num + i + 1) % total_pages
        if related_idx != page_num:
            related_pages.append(related_pages)
    
    # Build related links HTML
    related_links = ""
    for idx in random.sample(all_page_nums, min(3, len(all_page_nums))):
        if idx != page_num:
            related_links += f'            <li><a href="page{idx}.html">Related: Page {idx}</a></li>\n'
    
    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic} - Documentation Page {page_num}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; line-height: 1.6; }}
        main {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #666; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre code {{ background: none; padding: 0; }}
        nav {{ margin-bottom: 30px; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
        nav ul {{ list-style: none; padding: 0; }}
        nav li {{ margin: 5px 0; }}
        a {{ color: #0066cc; }}
    </style>
</head>
<body>
    <main>
        <nav>
            <strong>Navigation</strong>
            <ul>
                <li><a href="index.html">Home</a></li>
{related_links}
            </ul>
        </nav>
        
        <h1>{topic}</h1>
        <p>This is documentation page <strong>{page_num}</strong> of {total_pages}. 
           This page covers {topic.lower()} for the project.</p>
        
        <h2>Overview</h2>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor 
           incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis 
           nostrud exercitation ullamco laboris.</p>
        
        <h3>Key Points</h3>
        <ul>
            <li>First important point about {topic.lower()}</li>
            <li>Second consideration for implementation</li>
            <li>Third best practice to follow</li>
            <li>Additional notes and recommendations</li>
        </ul>
        
        <h2>Installation</h2>
        <p>To get started, install the package using one of the following methods:</p>
        
        <pre><code># Using pip
pip install example-package

# Using uv
uv pip install example-package

# From source
git clone https://github.com/example/repo.git
cd repo
pip install -e .</code></pre>
        
        <h2>Usage</h2>
        <p>Here's a basic example of how to use the library:</p>
        
        <pre><code>import example_package

# Initialize the client
client = example_package.Client(api_key="your-key")

# Make a request
result = client.process(data)
print(result)</code></pre>
        
        <h2>Configuration</h2>
        <p>The following configuration options are available:</p>
        
        <table>
            <thead>
                <tr>
                    <th>Option</th>
                    <th>Type</th>
                    <th>Default</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>timeout</code></td>
                    <td>int</td>
                    <td>30</td>
                    <td>Request timeout in seconds</td>
                </tr>
                <tr>
                    <td><code>retries</code></td>
                    <td>int</td>
                    <td>3</td>
                    <td>Number of retry attempts</td>
                </tr>
                <tr>
                    <td><code>debug</code></td>
                    <td>bool</td>
                    <td>false</td>
                    <td>Enable debug logging</td>
                </tr>
            </tbody>
        </table>
        
        <h2>Advanced Example</h2>
        <p>For more complex use cases, you can use the advanced API:</p>
        
        <pre><code>from example_package import AdvancedClient, Config

config = Config(
    timeout=60,
    retries=5,
    debug=True
)

client = AdvancedClient(config=config)

async def process_data():
    async with client.session() as session:
        result = await session.fetch(url)
        return result.transform()</code></pre>
        
        <h2>Troubleshooting</h2>
        <p>Common issues and solutions:</p>
        
        <h3>Connection Errors</h3>
        <p>If you encounter connection errors, check your network settings and firewall 
           configuration. Ensure that the API endpoint is accessible.</p>
        
        <h3>Authentication Failures</h3>
        <p>Verify that your API key is correct and has not expired. You can regenerate 
           your API key from the dashboard.</p>
        
        <h2>See Also</h2>
        <ul>
            <li><a href="page{(page_num + 1) % total_pages}.html">Next: Related Topic</a></li>
            <li><a href="page{(page_num - 1) % total_pages}.html">Previous: Prerequisites</a></li>
            <li><a href="https://example.com/external">External Resource</a></li>
        </ul>
    </main>
</body>
</html>
'''
    return content


def generate_index_page(total_pages: int) -> str:
    """Generate the main index page."""
    
    page_links = ""
    for i in range(1, total_pages + 1):
        page_links += f'            <li><a href="page{i}.html">Documentation Page {i}</a></li>\n'
    
    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Site</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; line-height: 1.6; }}
        main {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; }}
        nav {{ background: #f9f9f9; padding: 20px; border-radius: 5px; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin: 8px 0; }}
        a {{ color: #0066cc; }}
    </style>
</head>
<body>
    <main>
        <h1>Documentation Site</h1>
        <p>Welcome to the benchmark documentation site. This site contains {total_pages} pages 
           of sample documentation for testing the site2skill tool.</p>
        
        <h2>Navigation</h2>
        <nav>
            <ul>
{page_links}
            </ul>
        </nav>
        
        <h2>About This Site</h2>
        <p>This site was generated for benchmarking purposes. Each page contains typical 
           documentation elements including:</p>
        <ul>
            <li>Headings (h1, h2, h3)</li>
            <li>Paragraphs with text content</li>
            <li>Code blocks (inline and block)</li>
            <li>Tables</li>
            <li>Lists (ordered and unordered)</li>
            <li>Internal and external links</li>
        </ul>
        
        <h2>Usage</h2>
        <p>Use this site to test the performance of HTML to Markdown conversion tools. 
           The site is designed to be served locally for consistent benchmarking.</p>
        
        <pre><code># Serve this site locally
python -m http.server 8888 --directory bench-site

# Test with site2skill
site2skill http://localhost:8888/ test-skill</code></pre>
    </main>
</body>
</html>
'''
    return content


def generate_site(num_pages: int, output_dir: str) -> None:
    """Generate the complete documentation site."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate index page
    index_content = generate_index_page(num_pages)
    (output_path / "index.html").write_text(index_content)
    
    # Generate all documentation pages
    all_page_nums = list(range(1, num_pages + 1))
    for page_num in all_page_nums:
        page_content = generate_page_content(page_num, num_pages, all_page_nums)
        (output_path / f"page{page_num}.html").write_text(page_content)
    
    print(f"Generated {num_pages + 1} files in {output_dir}/")
    print(f"  - 1 index page")
    print(f"  - {num_pages} documentation pages")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a static documentation website for benchmarking site2skill"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=100,
        help="Number of documentation pages to generate (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bench-site",
        help="Output directory for the generated site (default: bench-site)"
    )
    
    args = parser.parse_args()
    
    generate_site(args.pages, args.output)


if __name__ == "__main__":
    main()
