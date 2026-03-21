//! URL filtering for crawl scope control
//!
//! Restricts crawl boundaries based on the starting URL and filters out
//! URLs with localization-only query parameters to prevent over-crawling
//! of duplicate content in different languages.

use std::collections::HashSet;
use url::Url;

const DEFAULT_EXCLUDED_QUERY_KEYS: &[&str] = &["hl", "lang", "locale"];

/// Determine whether a candidate URL is within the allowed crawl scope.
///
/// The scope is defined by two rules:
///
/// 1. **Path scope** – the candidate must share the same scheme and host as
///    the starting URL and its path must be equal to or a descendant of the
///    starting URL's path.
/// 2. **Query-key filtering** – if *every* query parameter of the candidate
///    URL is in the exclusion list (e.g. localization parameters such as
///    `hl`, `lang`, `locale`), the URL is rejected because it is
///    likely a duplicate of the same page in a different language. URLs
///    that carry at least one non-excluded query key are allowed.
///
/// # Arguments
///
/// * `start_url` - The URL that was originally given to the crawler
/// * `candidate_url` - The URL being evaluated for crawling
/// * `excluded_query_keys` - Query-parameter keys to treat as localization-only
///
/// # Returns
///
/// `true` if the URL may be crawled, `false` otherwise.
pub fn is_url_allowed(
    start_url: &str,
    candidate_url: &str,
    excluded_query_keys: Option<&HashSet<String>>,
) -> bool {
    let excluded_keys: HashSet<&str> = excluded_query_keys
        .map(|keys| keys.iter().map(|s| s.as_str()).collect())
        .unwrap_or_else(|| DEFAULT_EXCLUDED_QUERY_KEYS.iter().copied().collect());

    let start = match Url::parse(start_url) {
        Ok(u) => u,
        Err(_) => return false,
    };

    let candidate = match Url::parse(candidate_url) {
        Ok(u) => u,
        Err(_) => return false,
    };

    // Scheme & host must match
    if start.scheme() != candidate.scheme() {
        return false;
    }
    if start.host_str() != candidate.host_str() {
        return false;
    }

    // Path scope: candidate must be equal to or a descendant of the starting path.
    // Append '/' before the prefix check to avoid matching sibling paths that
    // share a prefix (e.g. /docs must not match /docs-extra).
    let start_path = format!("{}/", start.path().trim_end_matches('/'));
    let candidate_path = format!("{}/", candidate.path().trim_end_matches('/'));

    if !candidate_path.starts_with(&start_path) {
        return false;
    }

    // Query-key filtering
    if let Some(_query) = candidate.query() {
        let query_pairs: Vec<(String, String)> = candidate.query_pairs().map(|(k, v)| (k.to_string(), v.to_string())).collect();

        if !query_pairs.is_empty() {
            // If every key belongs to the excluded set, reject the URL
            let all_excluded = query_pairs
                .iter()
                .all(|(key, _)| excluded_keys.contains(key.as_str()));

            if all_excluded {
                return false;
            }
        }
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_same_path_allowed() {
        assert!(is_url_allowed(
            "https://docs.example.com/api/",
            "https://docs.example.com/api/page",
            None
        ));
    }

    #[test]
    fn test_different_domain_rejected() {
        assert!(!is_url_allowed(
            "https://docs.example.com/",
            "https://other.com/",
            None
        ));
    }

    #[test]
    fn test_localization_params_rejected() {
        assert!(!is_url_allowed(
            "https://docs.example.com/",
            "https://docs.example.com/page?hl=en",
            None
        ));
    }

    #[test]
    fn test_non_localization_params_allowed() {
        assert!(is_url_allowed(
            "https://docs.example.com/",
            "https://docs.example.com/page?id=123",
            None
        ));
    }

    #[test]
    fn test_sibling_path_prefix_rejected() {
        // /docs must not match /docs-extra (sibling with shared prefix)
        assert!(!is_url_allowed(
            "https://example.com/docs",
            "https://example.com/docs-extra/page",
            None
        ));
    }

    #[test]
    fn test_exact_path_allowed() {
        assert!(is_url_allowed(
            "https://example.com/docs",
            "https://example.com/docs",
            None
        ));
    }

    #[test]
    fn test_descendant_path_allowed() {
        assert!(is_url_allowed(
            "https://example.com/docs",
            "https://example.com/docs/api/v1",
            None
        ));
    }
}
