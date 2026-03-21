//! site2skill - Turn any documentation website into a Claude Agent Skill
//!
//! This library provides tools to:
//! - Crawl documentation websites
//! - Convert HTML to Markdown
//! - Normalize links and formatting
//! - Generate skill structure with SKILL.md
//! - Package skills into ZIP files

pub mod convert;
pub mod fetch;
pub mod normalize;
pub mod skill;
pub mod utils;
pub mod url_filter;
pub mod validate;
