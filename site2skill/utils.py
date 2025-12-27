"""
Utility functions for site2skill.
"""
import os
import re


def sanitize_path(path: str) -> str:
    """
    Sanitize a file path by replacing invalid characters with underscores.
    
    This function sanitizes each path component separately to avoid issues
    with invalid characters in zip files or file systems.
    
    Args:
        path: The file path to sanitize (can be relative or absolute)
        
    Returns:
        The sanitized path with safe characters only. If all parts are empty
        after sanitization, returns "file.md" as a safe default.
        
    Examples:
        >>> sanitize_path("docs.example.com/api/index.md")
        'docs.example.com/api/index.md'
        >>> sanitize_path("docs@example.com/api#v1/index.md")
        'docs_example.com/api_v1/index.md'
        >>> sanitize_path("")
        'file.md'
    """
    # Split path into components
    path_parts = path.split(os.sep)
    
    # Sanitize each component
    sanitized_parts = []
    for part in path_parts:
        if part:  # Skip empty parts
            # Replace non-alphanumeric characters (except ._-) with _
            sanitized_part = re.sub(r'[^a-zA-Z0-9._-]', '_', part)
            sanitized_parts.append(sanitized_part)
    
    # If all parts were sanitized away, use a default
    if not sanitized_parts:
        return "file.md"
    
    # Rejoin with path separator
    return os.path.join(*sanitized_parts)


def html_to_md_path(html_path: str) -> str:
    """
    Convert an HTML file path to a corresponding markdown file path.
    
    Args:
        html_path: Path to HTML file (e.g., "docs/page.html")
        
    Returns:
        Path to markdown file (e.g., "docs/page.md")
        
    Examples:
        >>> html_to_md_path("docs/index.html")
        'docs/index.md'
        >>> html_to_md_path("page.html")
        'page.md'
        >>> html_to_md_path("docs/page")
        'docs/page.md'
    """
    if html_path.endswith('.html'):
        return html_path[:-5] + '.md'
    else:
        return html_path + '.md'
