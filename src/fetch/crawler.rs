//! Async HTTP crawler with concurrency control

use indicatif::{ProgressBar, ProgressStyle};
use lazy_static::lazy_static;
use regex::Regex;
use reqwest::Client;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;
use tokio::fs;
use tokio::sync::{Mutex, Semaphore};
use tracing::{debug, error, info, warn};
use url::Url;

use crate::url_filter::is_url_allowed;

use super::robots::RobotsTxtCache;

lazy_static! {
    static ref HREF_RE: Regex = Regex::new(r#"href=["']([^"']+)["']"#).unwrap();
}

#[derive(Error, Debug)]
pub enum CrawlerError {
    #[error("HTTP error: {0}")]
    HttpError(#[from] reqwest::Error),

    #[error("URL parse error: {0}")]
    UrlParseError(#[from] url::ParseError),

    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Robots.txt denied: {0}")]
    RobotsDenied(Url),

    #[error("Invalid URL: {0}")]
    InvalidUrl(String),

    #[error("Template error: {0}")]
    TemplateError(String),

    #[error("Semaphore error: {0}")]
    SemaphoreError(String),
}

#[derive(Debug, Clone)]
pub struct CrawlerConfig {
    pub base_url: Url,
    pub max_depth: u8,
    pub domain: String,
    pub include_paths: Vec<String>,
    pub exclude_query_keys: HashSet<String>,
    pub delay_ms: u64,
    pub max_concurrency: usize,
    pub user_agent: String,
}

impl Default for CrawlerConfig {
    fn default() -> Self {
        Self {
            base_url: Url::parse("https://example.com").unwrap(),
            max_depth: 5,
            domain: String::new(),
            include_paths: vec![],
            exclude_query_keys: ["hl", "lang", "locale"]
                .iter()
                .map(|s| s.to_string())
                .collect(),
            delay_ms: 1000,
            max_concurrency: 10,
            user_agent: "site2skill/0.2 (+https://github.com/laiso/site2skill)".to_string(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Page {
    pub url: Url,
    pub content: String,
    pub links: Vec<Url>,
}

pub async fn crawl(config: CrawlerConfig, output_dir: &Path) -> Result<(), CrawlerError> {
    let client = Client::builder()
        .user_agent(&config.user_agent)
        .timeout(Duration::from_secs(30))
        .build()?;

    let robots_cache = RobotsTxtCache::new(client.clone());

    // Create crawl directory
    let crawl_dir = output_dir.join("crawl");
    fs::create_dir_all(&crawl_dir).await?;

    // State tracking
    let visited = Arc::new(Mutex::new(HashSet::new()));
    let semaphore = Arc::new(Semaphore::new(config.max_concurrency));
    let progress = ProgressBar::new(0);
    progress.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta})")
            .map_err(|e| CrawlerError::TemplateError(e.to_string()))?
            .progress_chars("=>-"),
    );

    // Start with the base URL
    let mut urls_to_visit = vec![config.base_url.clone()];
    let mut pages_fetched: usize = 0;

    info!(
        "Starting crawl: {} (max_depth={}, concurrency={})",
        config.base_url, config.max_depth, config.max_concurrency
    );

    let base_url_str = config.base_url.as_str();

    let mut depth = 0;
    while depth <= config.max_depth && !urls_to_visit.is_empty() {
        info!("Crawling at depth {} with {} URLs", depth, urls_to_visit.len());
        let mut next_urls: HashSet<Url> = HashSet::new();
        let mut current_urls = Vec::new();

        // Filter URLs at this depth using the unified url_filter
        for url in &urls_to_visit {
            if !is_url_allowed(base_url_str, url.as_str(), Some(&config.exclude_query_keys)) {
                debug!("URL out of scope: {}", url);
                continue;
            }

            // Check robots.txt
            if !robots_cache.is_allowed(url).await? {
                warn!("Blocked by robots.txt: {}", url);
                continue;
            }

            // Check if already visited
            let mut visited_guard = visited.lock().await;
            if visited_guard.contains(url) {
                continue;
            }
            visited_guard.insert(url.clone());
            current_urls.push(url.clone());
        }

        if current_urls.is_empty() {
            depth += 1;
            continue;
        }

        progress.set_length(current_urls.len() as u64);
        progress.set_position(0);

        // Fetch URLs concurrently
        let mut tasks = Vec::new();
        for url in current_urls {
            let permit = semaphore.clone().acquire_owned().await
                .map_err(|e| CrawlerError::SemaphoreError(e.to_string()))?;
            let client_clone = client.clone();
            let progress_clone = progress.clone();

            let task = tokio::spawn(async move {
                let result = fetch_page(&client_clone, &url).await;
                progress_clone.inc(1);
                drop(permit); // Release permit
                (url, result)
            });

            tasks.push(task);
        }

        // Collect results
        for task in tasks {
            match task.await {
                Ok((_url, Ok(page))) => {
                    debug!("Fetched: {} ({} bytes)", page.url, page.content.len());

                    // Save page to disk
                    let file_path = url_to_file_path(&page.url, &crawl_dir, &config.domain)?;
                    if let Some(parent) = file_path.parent() {
                        fs::create_dir_all(parent).await?;
                    }
                    fs::write(&file_path, &page.content).await?;

                    // Collect links for next depth
                    for link in &page.links {
                        if is_url_allowed(base_url_str, link.as_str(), Some(&config.exclude_query_keys)) {
                            next_urls.insert(link.clone());
                        }
                    }

                    pages_fetched += 1;
                }
                Ok((url, Err(e))) => {
                    warn!("Failed to fetch {}: {}", url, e);
                }
                Err(e) => {
                    error!("Task failed: {}", e);
                }
            }
        }

        urls_to_visit = next_urls.into_iter().collect();
        depth += 1;

        // Rate limiting between batches
        if !urls_to_visit.is_empty() && config.delay_ms > 0 {
            tokio::time::sleep(Duration::from_millis(config.delay_ms)).await;
        }
    }

    progress.finish_with_message(format!("Crawl complete: {} pages", pages_fetched));
    info!("Crawl complete: {} pages fetched", pages_fetched);

    Ok(())
}

async fn fetch_page(
    client: &Client,
    url: &Url,
) -> Result<Page, CrawlerError> {
    let response = client.get(url.as_str()).send().await?;

    if !response.status().is_success() {
        return Err(CrawlerError::HttpError(
            reqwest::Error::from(response.error_for_status().unwrap_err()),
        ));
    }

    let content = response.text().await?;

    // Extract links
    let links = extract_links(&content, url)?;

    Ok(Page {
        url: url.clone(),
        content,
        links,
    })
}

fn extract_links(html: &str, base_url: &Url) -> Result<Vec<Url>, CrawlerError> {
    let mut links = Vec::new();

    for cap in HREF_RE.captures_iter(html) {
        if let Some(href) = cap.get(1) {
            let href_str = href.as_str();

            // Skip non-HTTP links
            if href_str.starts_with('#')
                || href_str.starts_with("javascript:")
                || href_str.starts_with("mailto:")
                || href_str.starts_with("data:")
            {
                continue;
            }

            // Resolve relative URLs
            if let Ok(absolute_url) = base_url.join(href_str) {
                // Only keep HTTP(S) URLs
                if absolute_url.scheme() == "http" || absolute_url.scheme() == "https" {
                    links.push(absolute_url);
                }
            }
        }
    }

    Ok(links)
}

/// Convert a URL to a file path under the crawl directory
pub fn url_to_file_path(url: &Url, crawl_dir: &Path, domain: &str) -> Result<PathBuf, CrawlerError> {
    // Create directory structure: crawl_dir/domain/path/to/file.html
    let path = url.path();

    // Build the file path
    let mut file_path = crawl_dir.join(domain);

    // Add path components
    if !path.is_empty() && path != "/" {
        for component in path.split('/').filter(|s| !s.is_empty()) {
            file_path = file_path.join(component);
        }
    }

    // Determine filename
    if path.ends_with('/') || path.is_empty() || path == "/" {
        file_path = file_path.join("index.html");
    } else if file_path.extension().map_or(true, |ext| ext != "html") {
        // No extension or non-html extension: append .html
        let current_name = file_path
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string();
        file_path.set_file_name(format!("{}.html", current_name));
    }

    Ok(file_path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    #[test]
    fn test_url_to_file_path_with_trailing_slash() {
        let url = Url::parse("https://example.com/docs/").unwrap();
        let crawl_dir = Path::new("/tmp/crawl");
        let result = url_to_file_path(&url, crawl_dir, "example.com").unwrap();
        assert_eq!(result, Path::new("/tmp/crawl/example.com/docs/index.html"));
    }

    #[test]
    fn test_url_to_file_path_root() {
        let url = Url::parse("https://example.com/").unwrap();
        let crawl_dir = Path::new("/tmp/crawl");
        let result = url_to_file_path(&url, crawl_dir, "example.com").unwrap();
        assert_eq!(result, Path::new("/tmp/crawl/example.com/index.html"));
    }

    #[test]
    fn test_url_to_file_path_no_extension() {
        let url = Url::parse("https://example.com/docs/api").unwrap();
        let crawl_dir = Path::new("/tmp/crawl");
        let result = url_to_file_path(&url, crawl_dir, "example.com").unwrap();
        assert_eq!(result, Path::new("/tmp/crawl/example.com/docs/api.html"));
    }

    #[test]
    fn test_url_to_file_path_html_extension() {
        let url = Url::parse("https://example.com/page.html").unwrap();
        let crawl_dir = Path::new("/tmp/crawl");
        let result = url_to_file_path(&url, crawl_dir, "example.com").unwrap();
        assert_eq!(result, Path::new("/tmp/crawl/example.com/page.html"));
    }

    #[test]
    fn test_url_to_file_path_non_html_extension() {
        let url = Url::parse("https://example.com/data.json").unwrap();
        let crawl_dir = Path::new("/tmp/crawl");
        let result = url_to_file_path(&url, crawl_dir, "example.com").unwrap();
        assert_eq!(result, Path::new("/tmp/crawl/example.com/data.json.html"));
    }

    #[test]
    fn test_url_to_file_path_empty_path() {
        let url = Url::parse("https://example.com").unwrap();
        let crawl_dir = Path::new("/tmp/crawl");
        let result = url_to_file_path(&url, crawl_dir, "example.com").unwrap();
        assert_eq!(result, Path::new("/tmp/crawl/example.com/index.html"));
    }

    #[test]
    fn test_extract_links_absolute() {
        let html = r#"<a href="https://example.com/page">link</a>"#;
        let base = Url::parse("https://example.com/").unwrap();
        let links = extract_links(html, &base).unwrap();
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].as_str(), "https://example.com/page");
    }

    #[test]
    fn test_extract_links_relative() {
        let html = r#"<a href="page.html">link</a>"#;
        let base = Url::parse("https://example.com/docs/").unwrap();
        let links = extract_links(html, &base).unwrap();
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].as_str(), "https://example.com/docs/page.html");
    }

    #[test]
    fn test_extract_links_skips_anchors() {
        let html = r##"<a href="#section">anchor</a><a href="javascript:void(0)">js</a><a href="mailto:a@b.com">mail</a>"##;
        let base = Url::parse("https://example.com/").unwrap();
        let links = extract_links(html, &base).unwrap();
        assert_eq!(links.len(), 0);
    }
}
