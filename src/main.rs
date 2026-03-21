use clap::{Parser, ValueEnum};
use chrono::Utc;
use std::path::PathBuf;
use tokio::fs;
use tracing::{error, info, warn, Level};
use tracing_subscriber::FmtSubscriber;

use site2skill::convert::html_to_markdown;
use site2skill::fetch::{crawl, CrawlerConfig};
use site2skill::normalize::normalize_markdown_file;
use site2skill::skill::{generate_skill_structure, package_skill};
use site2skill::validate::validate_skill;
use site2skill::utils::{html_to_md_path, sanitize_path};

#[derive(Debug, Clone, ValueEnum)]
enum TargetAgent {
    Claude,
    ClaudeDesktop,
    Cursor,
    Gemini,
    Codex,
}

impl TargetAgent {
    fn default_output_dir(&self) -> &'static str {
        match self {
            TargetAgent::Claude | TargetAgent::ClaudeDesktop => ".claude/skills",
            TargetAgent::Cursor => ".cursor/skills",
            TargetAgent::Gemini => ".gemini/skills",
            TargetAgent::Codex => ".codex/skills",
        }
    }
}

#[derive(Parser, Debug)]
#[command(name = "site2skill")]
#[command(about = "Turn any documentation website into a Claude Agent Skill")]
struct Args {
    /// URL of the documentation site
    url: String,

    /// Name of the skill (e.g., payjp)
    skill_name: String,

    /// Target agent (sets default output directory)
    #[arg(long, value_enum, default_value = "claude")]
    target: TargetAgent,

    /// Base output directory for skill structure (overrides target default)
    #[arg(short, long)]
    output: Option<PathBuf>,

    /// Output directory for .skill file
    #[arg(long, default_value = ".")]
    skill_output: PathBuf,

    /// Temporary directory for processing
    #[arg(long, default_value = "build")]
    temp_dir: PathBuf,

    /// Skip the download step (use existing files in temp dir)
    #[arg(long)]
    skip_fetch: bool,

    /// Clean up temporary directory after completion
    #[arg(long)]
    clean: bool,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize logging
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .with_target(false)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    let args = Args::parse();

    // Determine output base directory
    let output_base = args.output.unwrap_or_else(|| {
        PathBuf::from(args.target.default_output_dir())
    });

    let temp_download_dir = args.temp_dir.join("download");
    let temp_md_dir = args.temp_dir.join("markdown");

    // Timestamp for fetched_at
    let fetched_at = Utc::now().to_rfc3339();

    // Step 1: Fetch
    if !args.skip_fetch {
        // Clean both download and markdown dirs to avoid stale files from previous runs
        if temp_download_dir.exists() {
            fs::remove_dir_all(&temp_download_dir).await?;
        }
        if temp_md_dir.exists() {
            fs::remove_dir_all(&temp_md_dir).await?;
        }
        fs::create_dir_all(&temp_download_dir).await?;

        info!("=== Step 1: Fetching {} ===", args.url);

        let config = CrawlerConfig {
            base_url: args.url.parse()?,
            max_depth: 5,
            domain: url::Url::parse(&args.url)?.host_str().unwrap_or("").to_string(),
            include_paths: vec![],
            exclude_query_keys: ["hl", "lang", "locale"].iter().map(|s| s.to_string()).collect(),
            delay_ms: 1000,
            max_concurrency: 10,
            user_agent: "site2skill/0.2 (+https://github.com/laiso/site2skill)".to_string(),
        };

        crawl(config, &temp_download_dir).await?;
    } else {
        info!("=== Step 1: Skipped Fetching (Using {:?}) ===", temp_download_dir);
    }

    let crawl_dir = temp_download_dir.join("crawl");

    // Step 2: Convert HTML to Markdown
    info!("=== Step 2: Converting HTML to Markdown ===");

    fs::create_dir_all(&temp_md_dir).await?;

    let mut html_files = Vec::new();
    if crawl_dir.exists() {
        let mut entries = fs::read_dir(&crawl_dir).await.map_err(Box::new)?;
        while let Some(entry) = entries.next_entry().await.map_err(Box::new)? {
            collect_html_files(entry.path(), &mut html_files).await.map_err(Box::new)?;
        }
    }

    info!("Found {} HTML files", html_files.len());

    for html_file in html_files {
        // Calculate source_url
        let rel_path = html_file.strip_prefix(&crawl_dir).unwrap_or(&html_file);
        let rel_path_str = rel_path.to_string_lossy();

        // Remove .html extension for URL
        let rel_path_for_url = rel_path_str.strip_suffix(".html").unwrap_or(&rel_path_str);

        let parsed_input_url = url::Url::parse(&args.url)?;
        let scheme = parsed_input_url.scheme();
        let source_url = format!("{}://{}", scheme, rel_path_for_url);

        // Determine output filename
        let md_rel_path = html_to_md_path(&rel_path_str);
        let md_rel_path_sanitized = sanitize_path(&md_rel_path);
        let md_path = temp_md_dir.join(&md_rel_path_sanitized);

        if md_path.exists() {
            warn!("Name collision for {}. Overwriting.", md_rel_path);
        }

        // Create parent directories
        if let Some(parent) = md_path.parent() {
            fs::create_dir_all(parent).await?;
        }

        // Read and convert
        let html_content = fs::read_to_string(&html_file).await?;
        let md_content = html_to_markdown(&html_content, &source_url, &fetched_at)?;
        fs::write(&md_path, md_content).await?;
        info!("Converted: {:?} -> {:?}", html_file, md_path);
    }

    // Step 3: Normalize Markdown
    info!("=== Step 3: Normalizing Markdown ===");

    let mut md_files = Vec::new();
    collect_md_files(&temp_md_dir, &mut md_files).await.map_err(Box::new)?;

    for md_file in md_files {
        normalize_markdown_file(&md_file).await?;
    }

    // Step 4: Generate Skill Structure
    info!("=== Step 4: Generating Skill Structure ===");

    generate_skill_structure(
        &args.skill_name,
        &temp_md_dir,
        &output_base,
        Some(&format!("{:?}", args.target)),
    )?;

    let skill_dir = output_base.join(&args.skill_name);

    // Step 5: Validate Skill
    info!("=== Step 5: Validating Skill ===");

    let validation_result = validate_skill(&skill_dir)?;
    if !validation_result.is_valid {
        error!("Validation failed. Please check errors.");
        for err in validation_result.errors {
            error!("  - {}", err);
        }
    }
    for warning in validation_result.warnings {
        warn!("  - {}", warning);
    }

    // Step 6: Package Skill
    let skill_file = if matches!(args.target, TargetAgent::ClaudeDesktop) {
        info!("=== Step 6: Packaging Skill ===");
        Some(package_skill(&skill_dir, &args.skill_output)?)
    } else {
        info!("=== Step 6: Packaging Skill (skipped for non-claude-desktop targets) ===");
        None
    };

    info!("=== Done! ===");
    info!("Skill directory: {:?}", skill_dir);
    if let Some(ref file) = skill_file {
        info!("Skill package: {:?}", file);
    }

    // Cleanup
    if args.clean {
        fs::remove_dir_all(&args.temp_dir).await?;
        info!("Temporary files removed from {:?}", args.temp_dir);
    } else {
        info!("Temporary files kept in {:?}", args.temp_dir);
    }

    Ok(())
}

async fn collect_html_files(
    start_path: PathBuf,
    files: &mut Vec<PathBuf>,
) -> Result<(), std::io::Error> {
    let mut stack = vec![start_path];

    while let Some(path) = stack.pop() {
        let metadata = fs::metadata(&path).await?;
        if metadata.is_file() {
            if path.extension().map_or(false, |ext| ext == "html") {
                files.push(path);
            }
        } else if metadata.is_dir() {
            let mut entries = fs::read_dir(&path).await?;
            while let Some(entry) = entries.next_entry().await? {
                stack.push(entry.path());
            }
        }
    }
    Ok(())
}

async fn collect_md_files(
    dir: &PathBuf,
    files: &mut Vec<PathBuf>,
) -> Result<(), std::io::Error> {
    if !dir.exists() {
        return Ok(());
    }

    let mut stack = vec![dir.clone()];

    while let Some(current_dir) = stack.pop() {
        let mut entries = fs::read_dir(&current_dir).await?;
        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            let metadata = fs::metadata(&path).await?;
            if metadata.is_file() {
                if path.extension().map_or(false, |ext| ext == "md") {
                    files.push(path);
                }
            } else if metadata.is_dir() {
                stack.push(path);
            }
        }
    }

    Ok(())
}
