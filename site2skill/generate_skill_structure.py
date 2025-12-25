import os
import shutil
import argparse
import logging
import sys
from typing import Optional

if sys.version_info >= (3, 9):
    from importlib.resources import files as importlib_files
else:
    from importlib_resources import files as importlib_files

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_skill_structure(skill_name: str, source_dir: Optional[str], output_base: str = ".claude/skills") -> None:
    """
    Generate the Skill structure following SKILL.md + docs/ pattern.
    Structure:
      <skill-name>/
        SKILL.md         # Entry point, usage instructions
        docs/            # Documentation files (preserves directory structure)
        scripts/         # (Optional) Executable code
    """
    skill_dir = os.path.join(output_base, skill_name)

    # Define subdirectories
    docs_dir = os.path.join(skill_dir, "docs")
    scripts_dir = os.path.join(skill_dir, "scripts")

    # Create directories
    if os.path.exists(skill_dir):
        logger.warning(f"Skill directory {skill_dir} already exists.")
    else:
        os.makedirs(skill_dir)

    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    # Create SKILL.md
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md_path):
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(f"""---
name: {skill_name}
description: {skill_name.upper()} documentation assistant
---

# {skill_name.upper()} Skill

This skill provides access to {skill_name.upper()} documentation.

## Documentation

All documentation files are in the `docs/` directory as Markdown files.

## Search Tool

```bash
python scripts/search_docs.py "<query>"
```

Options:
- `--json` - Output as JSON
- `--max-results N` - Limit results (default: 10)

## Usage

1. Search or read files in `docs/` for relevant information
2. Each file has frontmatter with `source_url` and `fetched_at`
3. Always cite the source URL in responses
4. Note the fetch date - documentation may have changed

## Response Format

```
[Answer based on documentation]

**Source:** [source_url]
**Fetched:** [fetched_at]
```
""")
        logger.info(f"Created {skill_md_path}")

    # Copy scripts using importlib.resources
    dest_search_script = os.path.join(scripts_dir, "search_docs.py")
    dest_readme = os.path.join(scripts_dir, "README.md")

    try:
        templates = importlib_files("site2skill").joinpath("templates")

        search_script_resource = templates.joinpath("search_docs.py")
        with open(dest_search_script, "w", encoding="utf-8") as f:
            f.write(search_script_resource.read_text(encoding="utf-8"))
        logger.info("Installed search_docs.py")

        readme_resource = templates.joinpath("scripts_README.md")
        with open(dest_readme, "w", encoding="utf-8") as f:
            f.write(readme_resource.read_text(encoding="utf-8"))
        logger.info("Installed scripts/README.md")
    except Exception as e:
        logger.warning(f"Failed to copy templates: {e}")

    # Copy Markdown files (preserve directory structure)
    if source_dir and os.path.exists(source_dir):
        logger.info(f"Copying files from {source_dir}...")
        file_count = 0

        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".md"):
                    src_path = os.path.join(root, file)
                    
                    # Preserve directory structure relative to source_dir
                    rel_path = os.path.relpath(src_path, source_dir)
                    dst_path = os.path.join(docs_dir, rel_path)

                    # Security check: Ensure dst_path is strictly within docs_dir
                    abs_dst_path = os.path.abspath(dst_path)
                    abs_docs_dir = os.path.abspath(docs_dir)

                    if os.path.commonpath([abs_dst_path, abs_docs_dir]) != abs_docs_dir:
                        logger.warning(f"Skipping potential path traversal file: {file}")
                        continue
                    
                    # Create parent directories if needed
                    parent_dir = os.path.dirname(dst_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)

                    shutil.copy2(src_path, dst_path)
                    file_count += 1

        logger.info(f"Copied {file_count} files to docs/")
    else:
        logger.warning(f"Source directory {source_dir} not found or empty.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Skill Structure.")
    parser.add_argument("skill_name", help="Name of the skill (e.g., payjp)")
    parser.add_argument("--source", "-s", help="Source directory containing Markdown files")
    parser.add_argument("--output", "-o", default=".claude/skills", help="Base output directory")

    args = parser.parse_args()

    generate_skill_structure(args.skill_name, args.source, args.output)
