//! ZIP packaging for skills

use std::fs::File;
use std::io::{self};
use std::path::{Path, PathBuf};
use thiserror::Error;
use tracing::info;
use zip::write::FileOptions;

#[derive(Error, Debug)]
pub enum PackageError {
    #[error("I/O error: {0}")]
    IoError(#[from] io::Error),

    #[error("ZIP error: {0}")]
    ZipError(#[from] zip::result::ZipError),
}

/// Package a skill directory into a .skill file (ZIP archive)
pub fn package_skill(skill_dir: &Path, output_dir: &Path) -> Result<PathBuf, PackageError> {
    if !skill_dir.is_dir() {
        return Err(PackageError::IoError(io::Error::new(
            io::ErrorKind::NotFound,
            format!("Directory not found: {:?}", skill_dir),
        )));
    }

    let skill_name = skill_dir
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("skill");

    let output_path = output_dir.join(format!("{}.skill", skill_name));

    info!("Packaging {:?} to {:?}", skill_dir, output_path);

    // Create ZIP file
    let zip_file = File::create(&output_path)?;
    let mut zip = zip::ZipWriter::new(zip_file);

    let options = FileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated)
        .unix_permissions(0o644);

    // Walk the skill directory and add files to ZIP
    for entry in walkdir::WalkDir::new(skill_dir)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        let rel_path = path.strip_prefix(skill_dir).unwrap_or(path);

        // Skip directories (they're created implicitly)
        if path.is_dir() {
            continue;
        }

        // Convert to Unix-style path for ZIP
        let zip_path = rel_path
            .components()
            .map(|c| c.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/");

        // Add file to ZIP
        zip.start_file(&zip_path, options)?;

        let mut file = File::open(path)?;
        io::copy(&mut file, &mut zip)?;
    }

    zip.finish()?;

    info!("Successfully created: {:?}", output_path);

    Ok(output_path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::io::Read;

    #[test]
    fn test_package_skill() {
        let temp = std::env::temp_dir().join("test_package_skill");
        let _ = fs::remove_dir_all(&temp);

        let skill_dir = temp.join("my-skill");
        let output_dir = temp.join("output");
        fs::create_dir_all(skill_dir.join("references")).unwrap();
        fs::create_dir_all(&output_dir).unwrap();
        fs::write(skill_dir.join("SKILL.md"), "# Skill").unwrap();
        fs::write(skill_dir.join("references/doc.md"), "# Doc").unwrap();

        let result = package_skill(&skill_dir, &output_dir).unwrap();
        assert!(result.exists());
        assert_eq!(result.file_name().unwrap(), "my-skill.skill");

        // Verify ZIP contents
        let file = File::open(&result).unwrap();
        let mut archive = zip::ZipArchive::new(file).unwrap();
        let mut names: Vec<String> = (0..archive.len())
            .map(|i| archive.by_index(i).unwrap().name().to_string())
            .collect();
        names.sort();
        assert!(names.contains(&"SKILL.md".to_string()));
        assert!(names.contains(&"references/doc.md".to_string()));

        // Verify content
        let mut skill_md = String::new();
        archive.by_name("SKILL.md").unwrap().read_to_string(&mut skill_md).unwrap();
        assert_eq!(skill_md, "# Skill");

        let _ = fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_package_skill_nonexistent_dir() {
        let result = package_skill(Path::new("/nonexistent/dir"), Path::new("/tmp"));
        assert!(result.is_err());
    }
}
