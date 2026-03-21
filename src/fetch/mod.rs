//! Fetch module for crawling websites
//!
//! This module provides an async HTTP crawler with:
//! - robots.txt compliance
//! - Concurrent fetching with semaphore-based parallelism
//! - Rate limiting
//! - Domain and path restrictions

mod crawler;
mod robots;

pub use crawler::{crawl, CrawlerConfig, CrawlerError, Page};
pub use robots::RobotsTxtCache;
