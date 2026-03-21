//! Skill validation

use std::fs;
use std::path::Path;
use thiserror::Error;
use tracing::{error, info, warn};

#[derive(Error, Debug)]
pub enum ValidateError {
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Validation report with errors and warnings
#[derive(Debug, Default)]
pub struct ValidationReport {
    pub is_valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

/// Validate a skill directory structure and metadata
pub fn validate_skill(skill_dir: &Path) -> Result<ValidationReport, ValidateError> {
    info!("Validating skill in: {:?}", skill_dir);

    let mut report = ValidationReport::default();

    // 1. Check directory existence
    if !skill_dir.is_dir() {
        let err = format!("Directory not found: {:?}", skill_dir);
        error!("{}", err);
        report.errors.push(err);
        report.is_valid = false;
        return Ok(report);
    }

    // 2. Check SKILL.md
    let skill_md_path = skill_dir.join("SKILL.md");
    if skill_md_path.exists() {
        info!("Found SKILL.md");

        // Validate frontmatter
        match fs::read_to_string(&skill_md_path) {
            Ok(content) => {
                if content.starts_with("---\n") {
                    // Check for required fields
                    let required_fields = ["name:", "description:"];
                    for field in required_fields {
                        if !content.contains(field) {
                            report.warnings.push(format!(
                                "SKILL.md frontmatter missing '{}' field",
                                field.trim_end_matches(':')
                            ));
                        }
                    }
                    info!("  YAML frontmatter present");
                } else {
                    report.warnings.push("SKILL.md missing YAML frontmatter".to_string());
                }
            }
            Err(e) => {
                report.warnings.push(format!("Could not validate SKILL.md: {}", e));
            }
        }
    } else {
        report.errors.push("SKILL.md not found".to_string());
    }

    // 3. Check references/ directory (fallback to docs/)
    let references_dir = skill_dir.join("references");
    let docs_dir = skill_dir.join("docs");

    let content_dir = if references_dir.is_dir() {
        info!("Found references/");
        references_dir
    } else if docs_dir.is_dir() {
        report.warnings.push("references/ not found, using legacy docs/ directory".to_string());
        info!("Found docs/ (legacy)");
        docs_dir
    } else {
        report.errors.push("references/ directory not found (and no legacy docs/)".to_string());
        skill_dir.join("nonexistent")
    };

    if content_dir.is_dir() {
        // Count markdown files
        let mut md_count = 0;
        for entry in walkdir::WalkDir::new(&content_dir)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |ext| ext == "md") {
                md_count += 1;
            }
        }

        if md_count == 0 {
            report.warnings.push(format!(
                "{} directory is empty (no .md files)",
                content_dir.file_name().and_then(|n| n.to_str()).unwrap_or("content")
            ));
        } else {
            info!("  {} markdown files", md_count);
        }
    }

    // 4. Check optional directories
    let scripts_dir = skill_dir.join("scripts");
    if scripts_dir.is_dir() {
        info!("Found scripts/ (optional)");
    }

    // 5. Check skill size
    check_skill_size(&content_dir, &mut report);

    // 6. Report results
    if !report.errors.is_empty() {
        error!("VALIDATION FAILED:");
        for err in &report.errors {
            error!("  - {}", err);
        }
        report.is_valid = false;
    } else {
        if !report.warnings.is_empty() {
            warn!("Warnings:");
            for warning in &report.warnings {
                warn!("  - {}", warning);
            }
        }
        info!("Validation passed!");
        report.is_valid = true;
    }

    Ok(report)
}

/// Check the total size of the skill directory
fn check_skill_size(content_dir: &Path, report: &mut ValidationReport) {
    if !content_dir.is_dir() {
        return;
    }

    let mut total_size: u64 = 0;
    let mut file_sizes: Vec<(u64, String)> = Vec::new();

    for entry in walkdir::WalkDir::new(content_dir)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        if path.is_file() {
            if let Ok(size) = fs::metadata(path).map(|m| m.len()) {
                total_size += size;
                let rel_path = path
                    .strip_prefix(content_dir)
                    .unwrap_or(path)
                    .to_string_lossy()
                    .to_string();
                file_sizes.push((size, rel_path));
            }
        }
    }

    // Sort by size descending
    file_sizes.sort_by(|a, b| b.0.cmp(&a.0));

    let total_size_mb = total_size as f64 / (1024.0 * 1024.0);

    info!("\n--- Skill Size Analysis ---");
    info!("Total Uncompressed Size: {:.2} MB", total_size_mb);

    if total_size > 8 * 1024 * 1024 {
        warn!("Skill uncompressed size exceeds Claude's 8MB limit.");
        warn!("The skill may fail to load in Claude.");
        report.warnings.push("Skill size exceeds 8MB limit".to_string());
    } else {
        info!("Size is within limits (< 8MB).");
    }

    info!("\nTop 10 Largest Files:");
    for (size, path) in file_sizes.iter().take(10) {
        info!("  {:.1} KB - {}", *size as f64 / 1024.0, path);
    }
    info!("---------------------------\n");
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_validate_valid_skill() {
        let temp = std::env::temp_dir().join("test_validate_valid");
        let _ = fs::remove_dir_all(&temp);

        let skill_dir = temp.join("my-skill");
        fs::create_dir_all(skill_dir.join("references")).unwrap();
        fs::write(
            skill_dir.join("SKILL.md"),
            "---\nname: my-skill\ndescription: test\n---\n\n# Skill",
        ).unwrap();
        fs::write(skill_dir.join("references/doc.md"), "# Doc").unwrap();

        let report = validate_skill(&skill_dir).unwrap();
        assert!(report.is_valid);
        assert!(report.errors.is_empty());

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_validate_missing_skill_md() {
        let temp = std::env::temp_dir().join("test_validate_no_skill_md");
        let _ = fs::remove_dir_all(&temp);

        let skill_dir = temp.join("my-skill");
        fs::create_dir_all(skill_dir.join("references")).unwrap();

        let report = validate_skill(&skill_dir).unwrap();
        assert!(!report.is_valid);
        assert!(report.errors.iter().any(|e| e.contains("SKILL.md not found")));

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_validate_missing_references_dir() {
        let temp = std::env::temp_dir().join("test_validate_no_refs");
        let _ = fs::remove_dir_all(&temp);

        let skill_dir = temp.join("my-skill");
        fs::create_dir_all(&skill_dir).unwrap();
        fs::write(
            skill_dir.join("SKILL.md"),
            "---\nname: my-skill\ndescription: test\n---\n",
        ).unwrap();

        let report = validate_skill(&skill_dir).unwrap();
        assert!(!report.is_valid);
        assert!(report.errors.iter().any(|e| e.contains("references/")));

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_validate_nonexistent_dir() {
        let report = validate_skill(Path::new("/nonexistent/skill")).unwrap();
        assert!(!report.is_valid);
        assert!(report.errors.iter().any(|e| e.contains("Directory not found")));
    }

    #[test]
    fn test_validate_missing_frontmatter() {
        let temp = std::env::temp_dir().join("test_validate_no_frontmatter");
        let _ = fs::remove_dir_all(&temp);

        let skill_dir = temp.join("my-skill");
        fs::create_dir_all(skill_dir.join("references")).unwrap();
        fs::write(skill_dir.join("SKILL.md"), "# No frontmatter").unwrap();
        fs::write(skill_dir.join("references/doc.md"), "# Doc").unwrap();

        let report = validate_skill(&skill_dir).unwrap();
        assert!(report.is_valid); // Missing frontmatter is a warning, not error
        assert!(report.warnings.iter().any(|w| w.contains("frontmatter")));

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_validate_legacy_docs_dir() {
        let temp = std::env::temp_dir().join("test_validate_legacy_docs");
        let _ = fs::remove_dir_all(&temp);

        let skill_dir = temp.join("my-skill");
        fs::create_dir_all(skill_dir.join("docs")).unwrap();
        fs::write(
            skill_dir.join("SKILL.md"),
            "---\nname: my-skill\ndescription: test\n---\n",
        ).unwrap();
        fs::write(skill_dir.join("docs/doc.md"), "# Doc").unwrap();

        let report = validate_skill(&skill_dir).unwrap();
        assert!(report.is_valid);
        assert!(report.warnings.iter().any(|w| w.contains("legacy docs/")));

        let _ = fs::remove_dir_all(&temp);
    }
}
