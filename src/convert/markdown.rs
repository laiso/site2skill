//! HTML to Markdown conversion using htmd

use htmd::HtmlToMarkdown;
use htmd::options::{HeadingStyle, Options};
use lazy_static::lazy_static;
use regex::Regex;
use thiserror::Error;

use super::html::{clean_html, extract_content, extract_title};

lazy_static! {
    static ref MULTI_NEWLINE_RE: Regex = Regex::new(r"\n{3,}").unwrap();
    static ref TRAILING_WS_RE: Regex = Regex::new(r"[ \t]+$").unwrap();
}

#[derive(Error, Debug)]
pub enum MarkdownConvertError {
    #[error("Conversion error: {0}")]
    ConversionError(String),
}

/// Convert HTML to Markdown with frontmatter
pub fn html_to_markdown(
    html: &str,
    source_url: &str,
    fetched_at: &str,
) -> Result<String, MarkdownConvertError> {
    // Clean HTML
    let cleaned = clean_html(html);

    // Extract title
    let title = extract_title(&cleaned);

    // Extract content
    let content_html = extract_content(&cleaned).unwrap_or_default();

    // Convert to Markdown using htmd with options
    let converter = HtmlToMarkdown::builder()
        .options(Options {
            heading_style: HeadingStyle::Atx,
            ..Default::default()
        })
        .build();

    let md_body = converter
        .convert(&content_html)
        .map_err(|e| MarkdownConvertError::ConversionError(e.to_string()))?;

    // Post-process markdown
    let md_body = post_process_markdown(&md_body);

    // Create frontmatter
    let mut frontmatter = String::from("---\n");
    frontmatter.push_str(&format!("title: \"{}\"\n", escape_yaml_string(&title)));

    if !source_url.is_empty() {
        frontmatter.push_str(&format!("source_url: \"{}\"\n", escape_yaml_string(source_url)));
    }

    if !fetched_at.is_empty() {
        frontmatter.push_str(&format!("fetched_at: \"{}\"\n", fetched_at));
    }

    frontmatter.push_str("---\n\n");

    Ok(frontmatter + &md_body)
}

/// Post-process Markdown to clean up formatting
pub fn post_process_markdown(md: &str) -> String {
    let mut result = md.to_string();

    // Remove multiple consecutive blank lines (3+ newlines -> 2)
    result = MULTI_NEWLINE_RE.replace_all(&result, "\n\n").to_string();

    // Remove trailing whitespace on each line
    result = result
        .lines()
        .map(|line| TRAILING_WS_RE.replace_all(line, "").to_string())
        .collect::<Vec<_>>()
        .join("\n");

    result
}

/// Escape special characters in YAML strings
fn escape_yaml_string(s: &str) -> String {
    s.replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_html_to_markdown() {
        let html = r#"<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1><p>World</p></body></html>"#;
        let result = html_to_markdown(html, "https://example.com", "2024-01-01T00:00:00Z").unwrap();

        assert!(result.starts_with("---"));
        assert!(result.contains("title: \"Test\""));
        assert!(result.contains("source_url: \"https://example.com\""));
        assert!(result.contains("# Hello"));
        assert!(result.contains("World"));
    }

    #[test]
    fn test_post_process_markdown() {
        let input = "Line 1\n\n\n\nLine 2  \nLine 3\t";
        let result = post_process_markdown(input);
        assert_eq!(result, "Line 1\n\nLine 2\nLine 3");
    }

    #[test]
    fn test_escape_yaml_string() {
        assert_eq!(escape_yaml_string("hello"), "hello");
        assert_eq!(escape_yaml_string("hello \"world\""), "hello \\\"world\\\"");
        assert_eq!(escape_yaml_string("hello\\nworld"), "hello\\\\nworld");
    }
}
