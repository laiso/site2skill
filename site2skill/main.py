import argparse
import os
import shutil
import glob
import datetime
import re
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our modules
try:
    from .fetch_site import fetch_site
    from .convert_to_markdown import convert_html_to_md
    from .normalize_markdown import normalize_markdown
    from .generate_skill_structure import generate_skill_structure
    from .validate_skill import validate_skill
    from .package_skill import package_skill
    from .utils import sanitize_path, html_to_md_path
except ImportError as e:
    logger.error(f"Could not import pipeline modules: {e}")
    logger.error("Make sure you have installed dependencies: pip install beautifulsoup4 markdownify pyyaml")
    exit(1)

def main():
    parser = argparse.ArgumentParser(description="Web Docs to Claude Code Skill Pipeline")
    parser.add_argument("url", help="URL of the documentation site")
    parser.add_argument("skill_name", help="Name of the skill (e.g., payjp)")
    parser.add_argument("--output", "-o", default=".claude/skills", help="Base output directory for skill structure")
    parser.add_argument("--skill-output", default=".", help="Output directory for .skill file")
    parser.add_argument("--temp-dir", default="build", help="Temporary directory for processing")
    
    parser.add_argument("--skip-fetch", action="store_true", help="Skip the download step (use existing files in temp dir)")
    parser.add_argument("--clean", action="store_true", help="Clean up temporary directory after completion")
    
    args = parser.parse_args()
    
    try:
        # 1. Setup Directories
        temp_download_dir = os.path.join(args.temp_dir, "download")
        temp_md_dir = os.path.join(args.temp_dir, "markdown")
        
        if not args.skip_fetch:
            if os.path.exists(args.temp_dir):
                shutil.rmtree(args.temp_dir)
            os.makedirs(temp_download_dir)
        
        os.makedirs(temp_md_dir, exist_ok=True)
        
        # Timestamp for fetched_at
        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not args.skip_fetch:
            logger.info(f"=== Step 1: Fetching {args.url} ===")
            fetch_site(args.url, temp_download_dir)
        else:
            logger.info(f"=== Step 1: Skipped Fetching (Using {temp_download_dir}) ===")
        
        # fetch_site creates a 'crawl' subdirectory
        crawl_dir = os.path.join(temp_download_dir, "crawl")
        
        logger.info(f"=== Step 2: Converting HTML to Markdown ===")
        # Find all HTML files in the crawl directory
        html_files = glob.glob(os.path.join(crawl_dir, "**/*.html"), recursive=True)
        logger.info(f"Found {len(html_files)} HTML files.")
        
        for html_file in html_files:
            # Calculate source_url
            # wget creates directory structure: crawl_dir/domain/path/to/file.html
            # We need to reconstruct the URL.
            
            # Security check: Ensure html_file is strictly within crawl_dir
            abs_html_file = os.path.abspath(html_file)
            abs_crawl_dir = os.path.abspath(crawl_dir)
            
            if os.path.commonpath([abs_html_file, abs_crawl_dir]) != abs_crawl_dir:
                logger.warning(f"Skipping potential path traversal file: {html_file}")
                continue

            # Rel path from crawl_dir
            rel_path = os.path.relpath(html_file, crawl_dir)
            # rel_path is like "docs.pay.jp/v1/cardtoken.html"
            # We assume https for now, or we could parse args.url to get scheme
            parsed_input_url = urlparse(args.url)
            scheme = parsed_input_url.scheme if parsed_input_url.scheme else "https"
            
            # Construct URL
            # Note: This assumes wget preserved the domain directory.
            # If wget was run with -nH (no host directories), this might be different.
            # But fetch_site.py uses standard wget -r, which usually creates host dir.
            # Remove .html extension from source_url (PAY.JP site doesn't use .html in URLs)
            rel_path_for_url = rel_path[:-5] if rel_path.endswith('.html') else rel_path
            source_url = f"{scheme}://{rel_path_for_url}"
            
            # Determine output filename (preserve directory structure)
            # rel_path is like "docs.pay.jp/v1/cardtoken.html" or "docs.pay.jp/a/b/index.html"
            # We want to preserve the structure and replace .html with .md
            md_rel_path = html_to_md_path(rel_path)
            
            # Sanitize path components to avoid invalid characters in zip
            md_rel_path = sanitize_path(md_rel_path)
            md_path = os.path.join(temp_md_dir, md_rel_path)
            
            if os.path.exists(md_path):
                logger.warning(f"Name collision for {md_rel_path}. Overwriting.")
                
            convert_html_to_md(html_file, md_path, source_url=source_url, fetched_at=fetched_at)
            
        logger.info(f"=== Step 3: Normalizing Markdown ===")
        md_files = glob.glob(os.path.join(temp_md_dir, "**/*.md"), recursive=True)
        for md_file in md_files:
            # Normalize in place
            normalize_markdown(md_file, md_file)
            
        logger.info(f"=== Step 4: Generating Skill Structure ===")
        generate_skill_structure(args.skill_name, temp_md_dir, args.output)
        
        skill_dir = os.path.join(args.output, args.skill_name)
        
        logger.info(f"=== Step 5: Validating Skill ===")
        if not validate_skill(skill_dir):
            logger.error("Validation failed. Please check errors.")
            # We don't exit here, we might still want to package or debug
        
        # Note: check_skill_size is now called inside validate_skill
        
        logger.info(f"=== Step 6: Packaging Skill ===")
        skill_file = package_skill(skill_dir, args.skill_output)

        logger.info(f"=== Done! ===")
        logger.info(f"Skill directory: {skill_dir}")
        logger.info(f"Skill package: {skill_file}")
        
        # Cleanup
        if args.clean:
            shutil.rmtree(args.temp_dir)
            logger.info(f"Temporary files removed from {args.temp_dir}")
        else:
            logger.info(f"Temporary files kept in {args.temp_dir}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    main()
