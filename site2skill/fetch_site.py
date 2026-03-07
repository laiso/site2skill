import argparse
import subprocess
import sys
import os
import shutil
import logging
import re
from urllib.parse import urlparse
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LOCALIZED_QUERY_KEYS = ("hl", "lang", "locale")


@dataclass(frozen=True)
class CrawlConstraints:
    domain: str
    include_directory: str | None
    path_description: str
    accept_regex: str
    reject_regex: str


def build_crawl_constraints(url: str) -> CrawlConstraints:
    """Build wget-compatible crawl constraints from the starting URL."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path or "/"
    has_trailing_slash = path.endswith("/")

    if has_trailing_slash:
        include_directory = path
        path_description = path
        allowed_prefix = re.escape(f"{parsed_url.scheme}://{domain}{path}")
        accept_regex = rf"^{allowed_prefix}.*$"
    else:
        include_directory = os.path.dirname(path) or "/"
        path_description = f"{path} and descendants"
        exact_url = re.escape(f"{parsed_url.scheme}://{domain}{path}")
        descendant_prefix = re.escape(f"{parsed_url.scheme}://{domain}{path}/")
        accept_regex = rf"^({exact_url}([?#].*)?|{descendant_prefix}.*)$"

    query_keys = "|".join(re.escape(key) for key in LOCALIZED_QUERY_KEYS)
    reject_regex = rf"[?&]({query_keys})="

    return CrawlConstraints(
        domain=domain,
        include_directory=include_directory,
        path_description=path_description,
        accept_regex=accept_regex,
        reject_regex=reject_regex,
    )


def check_wget_installed() -> bool:
    """Check if wget is installed and available in the PATH."""
    return shutil.which("wget") is not None


def fetch_site(url: str, output_dir: str) -> None:
    """
    Fetch a website using wget with robust settings.
    
    Args:
        url: The URL to fetch.
        output_dir: The directory to save the fetched content.
    """
    # Validate URL scheme
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ('http', 'https'):
        logger.error(f"Invalid URL scheme: {parsed_url.scheme}. Only 'http' and 'https' are supported.")
        sys.exit(1)
        
    if not parsed_url.netloc:
        logger.error(f"Invalid URL: {url}. Domain is missing.")
        sys.exit(1)

    # Check for wget
    if not check_wget_installed():
        logger.error("wget is not installed. Please install wget to use this tool.")
        sys.exit(1)

    constraints = build_crawl_constraints(url)
    
    # Define temporary crawl directory
    crawl_dir = os.path.join(output_dir, "crawl")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Clean/Create crawl directory
    if os.path.exists(crawl_dir):
        shutil.rmtree(crawl_dir)
    os.makedirs(crawl_dir)

    logger.info(f"Fetching {url} to {crawl_dir}...")
    logger.info(f"Domain restricted to: {constraints.domain}")
    logger.info(f"Path restricted to: {constraints.path_description}")
    logger.info(f"Rejected query keys: {', '.join(LOCALIZED_QUERY_KEYS)}")
    
    # Construct wget command
    # --recursive: download recursively
    # --level=5: max recursion depth
    # --no-parent: don't go up
    # --domains: restrict to specific domain
    # --adjust-extension: save as .html
    # --convert-links: make links local
    # --accept: only html files
    # --user-agent: custom UA
    # --execute robots=on: respect robots.txt
    # --wait=1: be polite
    
    cmd = [
        "wget",
        "--recursive",
        "--level=5",
        "--no-parent",
        f"--domains={constraints.domain}",
        "--adjust-extension",
        "--convert-links",
        # Use reject instead of accept to allow extensionless URLs (which are often HTML)
        "--reject=css,js,png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,zip,tar,gz,pdf,xml,json,txt",
        f"--accept-regex={constraints.accept_regex}",
        f"--reject-regex={constraints.reject_regex}",
        "--user-agent=site2skill/0.1 (+https://github.com/laiso/site2skill)",
        "--execute", "robots=on", 
        "--wait=1",
        "--random-wait",
        "-P", crawl_dir,
        "--",
        url
    ]

    if constraints.include_directory:
        cmd.insert(5, f"--include-directories={constraints.include_directory}")
    
    # Run wget with progress tracking
    try:
        import re as regex
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        import time
        downloaded_urls = set()
        current_url = ""
        start_time = time.time()

        for line in process.stdout:
            # Match URL being fetched
            url_match = regex.search(r'--\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}--\s+(\S+)', line)
            if url_match:
                current_url = url_match.group(1)

            # Match successful save
            if "saved" in line.lower() or "Saving to:" in line:
                downloaded_urls.add(current_url)
                count = len(downloaded_urls)
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                mins, secs = divmod(int(elapsed), 60)
                short_url = current_url[-40:] if len(current_url) > 40 else current_url
                print(f"\r[{count} pages | {mins}m{secs:02d}s | {rate:.1f}/s] {short_url:<40}", end="", flush=True)

        process.wait()
        print()  # New line after progress

        elapsed = time.time() - start_time
        mins, secs = divmod(int(elapsed), 60)
        logger.info(f"Download complete. {len(downloaded_urls)} pages in {mins}m{secs:02d}s.")

        if process.returncode == 4:
            logger.warning("Wget returned exit code 4 (Network Failure). Some files may not have been downloaded. Continuing...")
        elif process.returncode == 6:
            logger.warning("Wget returned exit code 6 (Username/Password Authentication Failure). Continuing...")
        elif process.returncode == 8:
            logger.warning("Wget returned exit code 8 (Server Error). Some links returned 404/403. Continuing...")
        elif process.returncode != 0:
            logger.warning(f"Wget returned exit code {process.returncode}. Download may be incomplete...")

    except Exception as e:
        logger.error(f"An error occurred while running wget: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch a website for Skill creation.")
    parser.add_argument("url", help="URL of the documentation site")
    parser.add_argument("--output", "-o", default="temp_docs", help="Output directory")
    
    args = parser.parse_args()
    
    fetch_site(args.url, args.output)
