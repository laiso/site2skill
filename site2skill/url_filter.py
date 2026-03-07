"""
URL filtering for crawl scope control.

Restricts crawl boundaries based on the starting URL and filters out
URLs with localization-only query parameters to prevent over-crawling
of duplicate content in different languages.
"""
from urllib.parse import urlparse, parse_qs

DEFAULT_EXCLUDED_QUERY_KEYS = frozenset({"hl", "lang", "locale"})


def is_url_allowed(
    start_url: str,
    candidate_url: str,
    excluded_query_keys: set[str] | None = None,
) -> bool:
    """
    Determine whether a candidate URL is within the allowed crawl scope.

    The scope is defined by two rules:

    1. **Path scope** – the candidate must share the same scheme and host as
       the starting URL and its path must be equal to or a descendant of the
       starting URL's path.
    2. **Query-key filtering** – if *every* query parameter of the candidate
       URL is in the exclusion list (e.g. localization parameters such as
       ``hl``, ``lang``, ``locale``), the URL is rejected because it is
       likely a duplicate of the same page in a different language.  URLs
       that carry at least one non-excluded query key are allowed.

    Args:
        start_url: The URL that was originally given to the crawler.
        candidate_url: The URL being evaluated for crawling.
        excluded_query_keys: Query-parameter keys to treat as
            localization-only.  Defaults to
            :data:`DEFAULT_EXCLUDED_QUERY_KEYS`.

    Returns:
        ``True`` if the URL may be crawled, ``False`` otherwise.
    """
    if excluded_query_keys is None:
        excluded_query_keys = DEFAULT_EXCLUDED_QUERY_KEYS

    start = urlparse(start_url)
    candidate = urlparse(candidate_url)

    # --- scheme & host must match ------------------------------------------
    if start.scheme != candidate.scheme:
        return False
    if start.netloc != candidate.netloc:
        return False

    # --- path scope: candidate must be under the starting path -------------
    # Normalise so that "/a/b" is treated the same as "/a/b/"
    start_path = start.path.rstrip("/") + "/"
    candidate_path = candidate.path.rstrip("/") + "/"

    if not candidate_path.startswith(start_path):
        # Also allow the exact starting path itself (without trailing slash)
        if candidate.path.rstrip("/") != start.path.rstrip("/"):
            return False

    # --- query-key filtering -----------------------------------------------
    query_params = parse_qs(candidate.query, keep_blank_values=True)

    if query_params:
        # If every key belongs to the excluded set, reject the URL.
        if all(key in excluded_query_keys for key in query_params):
            return False

    return True
