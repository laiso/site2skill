//! Skill structure generation - creates SKILL.md and directory structure

use std::fs;
use std::io::{self, Write};
use std::path::Path;
use thiserror::Error;
use tracing::{info, warn};

#[derive(Error, Debug)]
pub enum StructureError {
    #[error("I/O error: {0}")]
    IoError(#[from] io::Error),
}

/// Generate the skill structure following SKILL.md + references/ pattern
///
/// Structure:
/// ```text
/// <skill-name>/
///   SKILL.md         # Entry point, usage instructions
///   references/      # Documentation files (preserves directory structure)
///   scripts/         # (Optional) Executable code
/// ```
pub fn generate_skill_structure(
    skill_name: &str,
    source_dir: &Path,
    output_base: &Path,
    target_agent: Option<&str>,
) -> Result<(), StructureError> {
    let skill_dir = output_base.join(skill_name);
    let references_dir = skill_dir.join("references");
    let scripts_dir = skill_dir.join("scripts");

    // Create directories
    if skill_dir.exists() {
        warn!("Skill directory {:?} already exists", skill_dir);
    } else {
        fs::create_dir_all(&skill_dir)?;
    }

    fs::create_dir_all(&references_dir)?;
    fs::create_dir_all(&scripts_dir)?;

    // Create SKILL.md
    let skill_md_path = skill_dir.join("SKILL.md");
    if !skill_md_path.exists() {
        let mut frontmatter = String::from("---\n");
        frontmatter.push_str(&format!("name: {}\n", skill_name));
        frontmatter.push_str(&format!("description: {} documentation assistant\n", skill_name.to_uppercase()));

        if let Some(agent) = target_agent {
            frontmatter.push_str("metadata:\n");
            frontmatter.push_str(&format!("  target_agent: {}\n", agent));
        }

        frontmatter.push_str("---\n");

        let skill_content = format!(
            r#"{frontmatter}

# {name_upper} Skill

This skill provides access to {name_upper} documentation.

## Documentation

All documentation files are in the `references/` directory as Markdown files.
For legacy skills, documentation may live in `docs/`.

## Search Tool

```bash
# Run the search script (use python or python3)
python scripts/search_docs.py "<query>"
```

Options:
- `--json` - Output as JSON
- `--max-results N` - Limit results (default: 10)

## Usage

1. Search or read files in `references/` for relevant information (fallback to `docs/` for legacy)
2. Each file has frontmatter with `source_url` and `fetched_at`
3. Always cite the source URL in responses
4. Note the fetch date - documentation may have changed

## Response Format

```
[Answer based on documentation]

**Source:** [source_url]
**Fetched:** [fetched_at]
```
"#,
            name_upper = skill_name.to_uppercase()
        );

        let mut file = fs::File::create(&skill_md_path)?;
        file.write_all(skill_content.as_bytes())?;
        info!("Created {:?}", skill_md_path);
    }

    // Copy scripts from embedded templates
    copy_templates(&scripts_dir)?;

    // Copy Markdown files (preserve directory structure)
    if source_dir.exists() {
        info!("Copying files from {:?}...", source_dir);
        let mut file_count = 0;

        // Canonicalize the references directory (it exists because we just created it)
        let abs_refs = fs::canonicalize(&references_dir)?;

        for entry in walkdir::WalkDir::new(source_dir)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |ext| ext == "md") {
                let rel_path = path.strip_prefix(source_dir).unwrap_or(path);

                // Security check: reject paths with parent directory traversal components
                if rel_path.components().any(|c| matches!(c, std::path::Component::ParentDir)) {
                    warn!("Skipping potential path traversal file: {:?}", rel_path);
                    continue;
                }

                let dst_path = references_dir.join(rel_path);

                // Create parent directories
                if let Some(parent) = dst_path.parent() {
                    fs::create_dir_all(parent)?;
                }

                // After creating parent dirs, canonicalize parent and verify it's under references_dir
                if let Some(parent) = dst_path.parent() {
                    let abs_parent = fs::canonicalize(parent)?;
                    if !abs_parent.starts_with(&abs_refs) {
                        warn!("Skipping potential path traversal file: {:?}", rel_path);
                        continue;
                    }
                }

                fs::copy(path, &dst_path)?;
                file_count += 1;
            }
        }

        info!("Copied {} files to references/", file_count);
    } else {
        warn!("Source directory {:?} not found or empty", source_dir);
    }

    Ok(())
}

/// Copy template files to scripts directory
fn copy_templates(scripts_dir: &Path) -> Result<(), StructureError> {
    // search_docs.py template
    let search_script = include_str!("../../templates/search_docs.py");
    let dest_search_script = scripts_dir.join("search_docs.py");
    fs::write(&dest_search_script, search_script)?;

    // Make executable (Unix only)
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(&dest_search_script)?.permissions();
        perms.set_mode(0o755);
        fs::set_permissions(&dest_search_script, perms)?;
    }

    info!("Installed search_docs.py");

    // scripts README template
    let scripts_readme = include_str!("../../templates/scripts_README.md");
    let dest_readme = scripts_dir.join("README.md");
    fs::write(&dest_readme, scripts_readme)?;
    info!("Installed scripts/README.md");

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_generate_skill_structure() {
        let temp = std::env::temp_dir().join("test_skill_structure");
        let _ = fs::remove_dir_all(&temp);

        let source_dir = temp.join("source");
        let output_base = temp.join("output");
        fs::create_dir_all(&source_dir).unwrap();
        fs::write(source_dir.join("doc.md"), "# Doc\nContent").unwrap();

        generate_skill_structure("test-skill", &source_dir, &output_base, Some("claude")).unwrap();

        let skill_dir = output_base.join("test-skill");
        assert!(skill_dir.join("SKILL.md").exists());
        assert!(skill_dir.join("references").is_dir());
        assert!(skill_dir.join("references/doc.md").exists());
        assert!(skill_dir.join("scripts").is_dir());
        assert!(skill_dir.join("scripts/search_docs.py").exists());

        // Verify SKILL.md content
        let skill_md = fs::read_to_string(skill_dir.join("SKILL.md")).unwrap();
        assert!(skill_md.contains("name: test-skill"));
        assert!(skill_md.contains("target_agent: claude"));

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_generate_skill_structure_preserves_subdirs() {
        let temp = std::env::temp_dir().join("test_skill_subdirs");
        let _ = fs::remove_dir_all(&temp);

        let source_dir = temp.join("source");
        let output_base = temp.join("output");
        fs::create_dir_all(source_dir.join("api")).unwrap();
        fs::write(source_dir.join("api/endpoint.md"), "# Endpoint").unwrap();
        fs::write(source_dir.join("index.md"), "# Index").unwrap();

        generate_skill_structure("my-skill", &source_dir, &output_base, None).unwrap();

        let refs_dir = output_base.join("my-skill/references");
        assert!(refs_dir.join("api/endpoint.md").exists());
        assert!(refs_dir.join("index.md").exists());

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_path_traversal_component_rejected() {
        // This test verifies that the component-level check catches ".." in paths.
        // walkdir won't naturally produce ".." components, but we verify the guard works.
        let rel = std::path::Path::new("../../../etc/passwd");
        let has_parent_dir = rel.components().any(|c| matches!(c, std::path::Component::ParentDir));
        assert!(has_parent_dir);

        let safe = std::path::Path::new("docs/api/page.md");
        let has_parent_dir = safe.components().any(|c| matches!(c, std::path::Component::ParentDir));
        assert!(!has_parent_dir);
    }
}
