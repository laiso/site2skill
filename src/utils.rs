//! Utility functions for path sanitization and conversion

/// Sanitize a file path by replacing invalid characters with underscores
///
/// This function sanitizes each path component separately to avoid issues
/// with invalid characters in zip files or file systems.
///
/// # Examples
///
/// ```
/// use site2skill::utils::sanitize_path;
///
/// assert_eq!(sanitize_path("references.example.com/api/index.md"), "references.example.com/api/index.md");
/// assert_eq!(sanitize_path("references@example.com/api#v1/index.md"), "references_example.com/api_v1/index.md");
/// ```
pub fn sanitize_path(path: &str) -> String {
    // Split path into components
    let mut sanitized_parts = Vec::new();

    for part in path.split(std::path::MAIN_SEPARATOR) {
        if !part.is_empty() {
            // Replace non-alphanumeric characters (except ._-) with _
            let sanitized: String = part
                .chars()
                .map(|c| {
                    if c.is_alphanumeric() || c == '.' || c == '_' || c == '-' {
                        c
                    } else {
                        '_'
                    }
                })
                .collect();
            sanitized_parts.push(sanitized);
        }
    }

    // If all parts were sanitized away, use a default
    if sanitized_parts.is_empty() {
        return "file.md".to_string();
    }

    // Rejoin with path separator
    sanitized_parts.join(std::path::MAIN_SEPARATOR_STR)
}

/// Convert an HTML file path to a corresponding markdown file path
///
/// # Examples
///
/// ```
/// use site2skill::utils::html_to_md_path;
///
/// assert_eq!(html_to_md_path("references/index.html"), "references/index.md");
/// assert_eq!(html_to_md_path("page.html"), "page.md");
/// assert_eq!(html_to_md_path("references/page"), "references/page.md");
/// ```
pub fn html_to_md_path(html_path: &str) -> String {
    if html_path.ends_with(".html") {
        format!("{}.md", &html_path[..html_path.len() - 5])
    } else {
        format!("{}.md", html_path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_path() {
        assert_eq!(
            sanitize_path("references.example.com/api/index.md"),
            "references.example.com/api/index.md"
        );
        assert_eq!(
            sanitize_path("references@example.com/api#v1/index.md"),
            "references_example.com/api_v1/index.md"
        );
        assert_eq!(sanitize_path(""), "file.md");
    }

    #[test]
    fn test_html_to_md_path() {
        assert_eq!(html_to_md_path("references/index.html"), "references/index.md");
        assert_eq!(html_to_md_path("page.html"), "page.md");
        assert_eq!(html_to_md_path("references/page"), "references/page.md");
    }
}
