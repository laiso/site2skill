//! Markdown normalization - link normalization and frontmatter handling

use lazy_static::lazy_static;
use regex::Regex;
use serde_yaml::Value;
use std::path::Path;
use thiserror::Error;
use tokio::fs;
use url::Url;

lazy_static! {
    static ref FRONTMATTER_RE: Regex = Regex::new(r"(?s)^---\n(.*?)\n---\n").unwrap();
    static ref LINK_RE: Regex = Regex::new(r"\[([^\]]*)\]\(([^)]+)\)").unwrap();
}

#[derive(Error, Debug)]
pub enum NormalizeError {
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("YAML parse error: {0}")]
    YamlError(#[from] serde_yaml::Error),

    #[error("URL parse error: {0}")]
    UrlParseError(#[from] url::ParseError),
}

/// Extract YAML frontmatter from markdown content
pub fn extract_frontmatter(content: &str) -> Option<serde_yaml::Mapping> {
    if let Some(caps) = FRONTMATTER_RE.captures(content) {
        if let Ok(Value::Mapping(map)) = serde_yaml::from_str::<Value>(&caps[1]) {
            return Some(map);
        }
    }

    None
}

/// Normalize relative links to absolute URLs based on source_url
pub fn normalize_links(content: &str, source_url: Option<&str>) -> Result<String, NormalizeError> {
    let Some(base_url) = source_url else {
        return Ok(content.to_string());
    };

    let base = Url::parse(base_url)?;

    let result = LINK_RE.replace_all(content, |caps: &regex::Captures| {
        let text = &caps[1];
        let url_str = &caps[2];

        // Skip if already absolute or special
        if url_str.starts_with("http:")
            || url_str.starts_with("https:")
            || url_str.starts_with("mailto:")
            || url_str.starts_with('#')
        {
            return caps[0].to_string();
        }

        // Resolve relative URL
        match base.join(url_str) {
            Ok(absolute_url) => format!("[{}]({})", text, absolute_url),
            Err(_) => caps[0].to_string(),
        }
    });

    Ok(result.to_string())
}

/// Normalize a markdown file in place
pub async fn normalize_markdown_file(path: &Path) -> Result<(), NormalizeError> {
    let content = fs::read_to_string(path).await?;

    // Extract source_url from frontmatter
    let frontmatter = extract_frontmatter(&content);
    let source_url = frontmatter
        .as_ref()
        .and_then(|map| map.get(&Value::String("source_url".to_string())))
        .and_then(|v| v.as_str());

    let normalized = normalize_links(&content, source_url)?;

    fs::write(path, normalized).await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_frontmatter() {
        let content = r#"---
title: "Test"
source_url: "https://example.com"
---

Body content
"#;

        let frontmatter = extract_frontmatter(content).unwrap();
        assert_eq!(
            frontmatter.get(&Value::String("title".to_string())).and_then(|v| v.as_str()),
            Some("Test")
        );
    }

    #[test]
    fn test_extract_frontmatter_missing() {
        let content = "No frontmatter here\n";
        assert!(extract_frontmatter(content).is_none());
    }

    #[test]
    fn test_normalize_links() {
        let content = r#"---
source_url: "https://example.com/docs/"
---

[Link](page.html)
[Absolute](https://other.com)
"#;

        let normalized = normalize_links(content, Some("https://example.com/docs/")).unwrap();
        assert!(normalized.contains("[Link](https://example.com/docs/page.html)"));
        assert!(normalized.contains("[Absolute](https://other.com)"));
    }

    #[test]
    fn test_normalize_links_no_source_url() {
        let content = "[Link](page.html)";
        let result = normalize_links(content, None).unwrap();
        assert_eq!(result, content);
    }

    #[test]
    fn test_normalize_links_anchor_preserved() {
        let content = "[Section](#heading)";
        let result = normalize_links(content, Some("https://example.com/")).unwrap();
        assert_eq!(result, "[Section](#heading)");
    }

    #[test]
    fn test_normalize_links_mailto_preserved() {
        let content = "[Email](mailto:user@example.com)";
        let result = normalize_links(content, Some("https://example.com/")).unwrap();
        assert_eq!(result, "[Email](mailto:user@example.com)");
    }
}
