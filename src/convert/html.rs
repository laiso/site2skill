//! HTML parsing and content extraction

use lazy_static::lazy_static;
use regex::Regex;
use scraper::{Html, Selector};

lazy_static! {
    /// Regex patterns for paired tags (script, style, etc.) - matches open+content+close
    static ref PAIRED_TAG_REGEXES: Vec<Regex> = {
        ["script", "style", "noscript", "iframe", "svg"]
            .iter()
            .map(|tag| Regex::new(&format!(r"(?si)<{tag}[^>]*>.*?</{tag}>")).unwrap())
            .collect()
    };

    /// Regex patterns for self-closing/void tags (meta, link)
    static ref VOID_TAG_REGEXES: Vec<Regex> = {
        ["meta", "link"]
            .iter()
            .map(|tag| Regex::new(&format!(r"(?si)<{tag}[^>]*/?>")).unwrap())
            .collect()
    };

    /// Regex patterns for nav/sidebar/footer elements (tag with class/id + all content + closing tag)
    static ref NAV_ELEMENT_REGEXES: Vec<Regex> = vec![
        Regex::new(r"(?si)<nav[^>]*>.*?</nav>").unwrap(),
        Regex::new(r"(?si)<header[^>]*>.*?</header>").unwrap(),
        Regex::new(r"(?si)<footer[^>]*>.*?</footer>").unwrap(),
        Regex::new(r"(?si)<aside[^>]*>.*?</aside>").unwrap(),
        Regex::new(r#"(?si)<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>.*?</div>"#).unwrap(),
        Regex::new(r#"(?si)<div[^>]*id="[^"]*sidebar[^"]*"[^>]*>.*?</div>"#).unwrap(),
        Regex::new(r#"(?si)<div[^>]*class="[^"]*navigation[^"]*"[^>]*>.*?</div>"#).unwrap(),
        Regex::new(r#"(?si)<div[^>]*id="[^"]*toc[^"]*"[^>]*>.*?</div>"#).unwrap(),
        Regex::new(r#"(?si)<div[^>]*id="[^"]*footer[^"]*"[^>]*>.*?</div>"#).unwrap(),
    ];

    static ref MAIN_SELECTOR: Selector = Selector::parse("main").unwrap();
    static ref ARTICLE_SELECTOR: Selector = Selector::parse("article").unwrap();
    static ref CONTENT_SELECTOR: Selector = Selector::parse(".content").unwrap();
    static ref BODY_SELECTOR: Selector = Selector::parse("body").unwrap();
    static ref TITLE_SELECTOR: Selector = Selector::parse("title").unwrap();
    static ref H1_SELECTOR: Selector = Selector::parse("h1").unwrap();
}

/// Extract the title from HTML
pub fn extract_title(html: &str) -> String {
    let document = Html::parse_document(html);

    // Try <title> tag first
    if let Some(title_elem) = document.select(&TITLE_SELECTOR).next() {
        let title = title_elem.text().collect::<String>().trim().to_string();
        if !title.is_empty() {
            return title;
        }
    }

    // Try <h1> tag
    if let Some(h1_elem) = document.select(&H1_SELECTOR).next() {
        let title = h1_elem.text().collect::<String>().trim().to_string();
        if !title.is_empty() {
            return title;
        }
    }

    "Untitled".to_string()
}

/// Extract the main content from HTML
pub fn extract_content(html: &str) -> Option<String> {
    let document = Html::parse_document(html);

    // Try to find the most relevant content container
    // Order: <main> > <article> > .content > <body>

    if let Some(elem) = document.select(&MAIN_SELECTOR).next() {
        return Some(elem.inner_html());
    }

    if let Some(elem) = document.select(&ARTICLE_SELECTOR).next() {
        return Some(elem.inner_html());
    }

    if let Some(elem) = document.select(&CONTENT_SELECTOR).next() {
        return Some(elem.inner_html());
    }

    if let Some(elem) = document.select(&BODY_SELECTOR).next() {
        return Some(elem.inner_html());
    }

    Some(document.html())
}

/// Clean HTML by removing unwanted tags and noise
///
/// Removes: script, style, noscript, iframe, svg, meta, link tags,
/// and navigation elements (nav, header, footer, aside, sidebar divs).
pub fn clean_html(html: &str) -> String {
    let mut result = html.to_string();

    // Remove paired tags (script, style, etc.)
    for re in PAIRED_TAG_REGEXES.iter() {
        result = re.replace_all(&result, "").to_string();
    }

    // Remove void/self-closing tags (meta, link)
    for re in VOID_TAG_REGEXES.iter() {
        result = re.replace_all(&result, "").to_string();
    }

    // Remove navigation/sidebar/footer elements
    for re in NAV_ELEMENT_REGEXES.iter() {
        result = re.replace_all(&result, "").to_string();
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_title() {
        let html = r#"<!DOCTYPE html><html><head><title>Test Page</title></head><body><h1>Other</h1></body></html>"#;
        assert_eq!(extract_title(html), "Test Page");
    }

    #[test]
    fn test_extract_title_from_h1() {
        let html = r#"<!DOCTYPE html><html><head></head><body><h1>Page Title</h1></body></html>"#;
        assert_eq!(extract_title(html), "Page Title");
    }

    #[test]
    fn test_extract_title_untitled() {
        let html = r#"<!DOCTYPE html><html><head></head><body><p>No title</p></body></html>"#;
        assert_eq!(extract_title(html), "Untitled");
    }

    #[test]
    fn test_clean_html() {
        let html = r#"<html><body><script>alert("hi")</script><p>Hello</p></body></html>"#;
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("<script>"));
        assert!(cleaned.contains("<p>"));
    }

    #[test]
    fn test_clean_html_removes_multiline_script() {
        let html = "<html><body><script type=\"text/javascript\">\nvar x = 1;\nvar y = 2;\nalert(x + y);\n</script><p>Content</p></body></html>";
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("<script"));
        assert!(!cleaned.contains("alert"));
        assert!(cleaned.contains("<p>Content</p>"));
    }

    #[test]
    fn test_clean_html_removes_style() {
        let html = "<html><head><style>\nbody { color: red; }\n.hidden { display: none; }\n</style></head><body><p>Visible</p></body></html>";
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("<style"));
        assert!(!cleaned.contains("color: red"));
        assert!(cleaned.contains("Visible"));
    }

    #[test]
    fn test_clean_html_removes_nav_elements() {
        let html = r#"<html><body><nav><a href="/">Home</a></nav><p>Main content</p></body></html>"#;
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("<nav>"));
        assert!(cleaned.contains("Main content"));
    }

    #[test]
    fn test_clean_html_removes_sidebar() {
        let html = r#"<html><body><div class="sidebar"><ul><li>Link</li></ul></div><p>Content</p></body></html>"#;
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("sidebar"));
        assert!(cleaned.contains("Content"));
    }

    #[test]
    fn test_clean_html_removes_footer() {
        let html = r#"<html><body><p>Content</p><footer><p>Copyright 2024</p></footer></body></html>"#;
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("<footer"));
        assert!(!cleaned.contains("Copyright"));
        assert!(cleaned.contains("Content"));
    }

    #[test]
    fn test_clean_html_removes_noscript() {
        let html = r#"<html><body><noscript>Enable JS</noscript><p>Content</p></body></html>"#;
        let cleaned = clean_html(html);
        assert!(!cleaned.contains("noscript"));
        assert!(cleaned.contains("Content"));
    }

    #[test]
    fn test_extract_content_from_main() {
        let html = r#"<html><body><header>Nav</header><main><p>Main content</p></main><footer>Foot</footer></body></html>"#;
        let content = extract_content(html).unwrap();
        assert!(content.contains("Main content"));
    }

    #[test]
    fn test_extract_content_from_article() {
        let html = r#"<html><body><article><p>Article content</p></article></body></html>"#;
        let content = extract_content(html).unwrap();
        assert!(content.contains("Article content"));
    }

    #[test]
    fn test_extract_content_from_body_fallback() {
        let html = r#"<html><body><p>Body content</p></body></html>"#;
        let content = extract_content(html).unwrap();
        assert!(content.contains("Body content"));
    }
}
