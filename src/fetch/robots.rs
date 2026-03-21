//! robots.txt handling for crawler compliance

use reqwest::{Client, StatusCode};
use std::collections::HashMap;
use tokio::sync::RwLock;
use tracing::{debug, warn};
use url::Url;

use super::CrawlerError;

/// Simple robots.txt parser and cache
pub struct RobotsTxtCache {
    client: Client,
    cache: RwLock<HashMap<String, RobotsTxt>>,
}

impl RobotsTxtCache {
    pub fn new(client: Client) -> Self {
        Self {
            client,
            cache: RwLock::new(HashMap::new()),
        }
    }

    /// Check if a URL is allowed by robots.txt
    pub async fn is_allowed(&self, url: &Url) -> Result<bool, CrawlerError> {
        let robots_url = robots_txt_url(url);

        // Check cache first
        {
            let cache_guard = self.cache.read().await;
            if let Some(robots) = cache_guard.get(&robots_url) {
                return Ok(robots.is_allowed(url.path(), "site2skill"));
            }
        }

        // Fetch robots.txt
        let robots = match self.fetch_robots(&robots_url).await {
            Ok(Some(content)) => RobotsTxt::parse(&content),
            Ok(None) => RobotsTxt::default(), // No robots.txt means everything is allowed
            Err(e) => {
                debug!("Failed to fetch robots.txt from {}: {}", robots_url, e);
                RobotsTxt::default()
            }
        };

        // Cache the result
        {
            let mut cache_guard = self.cache.write().await;
            cache_guard.insert(robots_url.clone(), robots);
        }

        // Check if allowed
        {
            let cache_guard = self.cache.read().await;
            if let Some(robots) = cache_guard.get(&robots_url) {
                return Ok(robots.is_allowed(url.path(), "site2skill"));
            }
        }

        Ok(true)
    }

    async fn fetch_robots(&self, url: &str) -> Result<Option<String>, CrawlerError> {
        let response = self.client.get(url).send().await?;

        match response.status() {
            StatusCode::OK => Ok(Some(response.text().await?)),
            StatusCode::NOT_FOUND => Ok(None),
            _ => {
                warn!("robots.txt returned status {}: {}", url, response.status());
                Ok(None)
            }
        }
    }
}

fn robots_txt_url(url: &Url) -> String {
    let scheme = url.scheme();
    let host = url.host_str().unwrap_or("");

    match url.port_or_known_default() {
        Some(port) => format!("{}://{}:{}/robots.txt", scheme, host, port),
        None => format!("{}://{}/robots.txt", scheme, host),
    }
}

/// Simple robots.txt representation
#[derive(Debug, Default)]
struct RobotsTxt {
    disallow_rules: Vec<String>,
    allow_rules: Vec<String>,
}

impl RobotsTxt {
    /// Parse robots.txt content
    pub fn parse(content: &str) -> Self {
        let mut disallow_rules = Vec::new();
        let mut allow_rules = Vec::new();
        let mut matching_user_agent = false;

        for line in content.lines() {
            let line = line.trim();

            // Skip comments and empty lines
            if line.is_empty() || line.starts_with('#') {
                continue;
            }

            // Parse directive
            if let Some((directive, value)) = line.split_once(':') {
                let directive = directive.trim().to_lowercase();
                let value = value.trim();

                match directive.as_str() {
                    "user-agent" => {
                        let ua = value.to_lowercase();
                        matching_user_agent = ua == "site2skill" || ua == "*";
                    }
                    "disallow" => {
                        if matching_user_agent && !value.is_empty() {
                            disallow_rules.push(value.to_string());
                        }
                    }
                    "allow" => {
                        if matching_user_agent && !value.is_empty() {
                            allow_rules.push(value.to_string());
                        }
                    }
                    _ => {}
                }
            }
        }

        Self {
            disallow_rules,
            allow_rules,
        }
    }

    /// Check if a path is allowed using longest-match semantics
    pub fn is_allowed(&self, path: &str, _user_agent: &str) -> bool {
        let mut longest_match_len: usize = 0;
        let mut longest_match_is_allow = true; // default: allowed

        for rule in &self.allow_rules {
            if path.starts_with(rule) && rule.len() > longest_match_len {
                longest_match_len = rule.len();
                longest_match_is_allow = true;
            }
        }

        for rule in &self.disallow_rules {
            if path.starts_with(rule) && rule.len() > longest_match_len {
                longest_match_len = rule.len();
                longest_match_is_allow = false;
            }
        }

        longest_match_is_allow
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_robots_url_keeps_non_default_port() {
        let url = Url::parse("http://localhost:3000/docs").unwrap();
        assert_eq!(robots_txt_url(&url), "http://localhost:3000/robots.txt");
    }

    #[test]
    fn test_robots_url_normalizes_default_https_port() {
        let implicit = Url::parse("https://example.com/docs").unwrap();
        let explicit = Url::parse("https://example.com:443/docs").unwrap();

        assert_eq!(robots_txt_url(&implicit), "https://example.com:443/robots.txt");
        assert_eq!(robots_txt_url(&explicit), "https://example.com:443/robots.txt");
    }

    #[test]
    fn test_robots_parse() {
        let content = r#"
User-agent: *
Disallow: /admin/
Allow: /admin/public/
"#;

        let robots = RobotsTxt::parse(content);
        assert!(robots.is_allowed("/index.html", "site2skill"));
        assert!(!robots.is_allowed("/admin/secret", "site2skill"));
        assert!(robots.is_allowed("/admin/public/page", "site2skill"));
    }
}
