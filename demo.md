# site2skill Demo

*2026-03-07T03:05:15Z by Showboat 0.6.1*
<!-- showboat-id: c2840ff1-ad33-4e79-905f-3c533f2eeed2 -->

site2skill turns any documentation website into a Claude Agent Skill. This demo walks through the tool's features and a complete example run.

## Installation

```bash
pip install site2skill 2>&1 | tail -1
```

```output
Requirement already satisfied: six<2,>=1.15 in /usr/lib/python3/dist-packages (from markdownify>=0.11.0->site2skill) (1.16.0)
```

## CLI Help

```bash
site2skill --help
```

```output
usage: site2skill [-h] [--target {claude,claude-desktop,cursor,gemini,codex}]
                  [--output OUTPUT] [--skill-output SKILL_OUTPUT]
                  [--temp-dir TEMP_DIR] [--skip-fetch] [--clean]
                  url skill_name

Web Docs to Claude Code Skill Pipeline

positional arguments:
  url                   URL of the documentation site
  skill_name            Name of the skill (e.g., payjp)

options:
  -h, --help            show this help message and exit
  --target {claude,claude-desktop,cursor,gemini,codex}
                        Target agent (sets default output directory)
  --output OUTPUT, -o OUTPUT
                        Base output directory for skill structure (overrides
                        target default)
  --skill-output SKILL_OUTPUT
                        Output directory for .skill file
  --temp-dir TEMP_DIR   Temporary directory for processing
  --skip-fetch          Skip the download step (use existing files in temp
                        dir)
  --clean               Clean up temporary directory after completion
```

Now run site2skill with `--skip-fetch` to convert the pre-downloaded HTML into a skill:

```bash
site2skill https://example.com/docs/ example-docs --skip-fetch --temp-dir /tmp/demo-build --output /tmp/demo-output 2>&1
```

```output
2026-03-07 03:06:31,162 - INFO - === Step 1: Skipped Fetching (Using /tmp/demo-build/download) ===
2026-03-07 03:06:31,162 - INFO - === Step 2: Converting HTML to Markdown ===
2026-03-07 03:06:31,162 - INFO - Found 3 HTML files.
2026-03-07 03:06:31,164 - INFO - Converted: /tmp/demo-build/download/crawl/example.com/docs/index.html -> /tmp/demo-build/markdown/example.com/docs/index.md
2026-03-07 03:06:31,166 - INFO - Converted: /tmp/demo-build/download/crawl/example.com/docs/api-reference.html -> /tmp/demo-build/markdown/example.com/docs/api-reference.md
2026-03-07 03:06:31,167 - INFO - Converted: /tmp/demo-build/download/crawl/example.com/docs/getting-started.html -> /tmp/demo-build/markdown/example.com/docs/getting-started.md
2026-03-07 03:06:31,167 - INFO - === Step 3: Normalizing Markdown ===
2026-03-07 03:06:31,168 - INFO - === Step 4: Generating Skill Structure ===
2026-03-07 03:06:31,169 - INFO - Created /tmp/demo-output/example-docs/SKILL.md
2026-03-07 03:06:31,172 - INFO - Installed search_docs.py
2026-03-07 03:06:31,172 - INFO - Installed scripts/README.md
2026-03-07 03:06:31,172 - INFO - Copying files from /tmp/demo-build/markdown...
2026-03-07 03:06:31,172 - INFO - Copied 3 files to references/
2026-03-07 03:06:31,172 - INFO - === Step 5: Validating Skill ===
2026-03-07 03:06:31,172 - INFO - Validating skill in: /tmp/demo-output/example-docs
2026-03-07 03:06:31,172 - INFO - Found SKILL.md
2026-03-07 03:06:31,173 - INFO -   YAML frontmatter present
2026-03-07 03:06:31,173 - INFO - Found references/
2026-03-07 03:06:31,173 - INFO -   3 markdown files
2026-03-07 03:06:31,173 - INFO - Found scripts/ (optional)
2026-03-07 03:06:31,173 - INFO - 
--- Skill Size Analysis ---
2026-03-07 03:06:31,173 - INFO - Total Uncompressed Size: 0.00 MB
2026-03-07 03:06:31,173 - INFO - Size is within limits (< 8MB).
2026-03-07 03:06:31,173 - INFO - 
Top 10 Largest Files:
2026-03-07 03:06:31,173 - INFO -   0.3 KB - references/example.com/docs/index.md
2026-03-07 03:06:31,173 - INFO -   0.3 KB - references/example.com/docs/getting-started.md
2026-03-07 03:06:31,173 - INFO -   0.3 KB - references/example.com/docs/api-reference.md
2026-03-07 03:06:31,173 - INFO - ---------------------------

2026-03-07 03:06:31,173 - INFO - Validation passed!
2026-03-07 03:06:31,173 - INFO - === Step 6: Packaging Skill (skipped for non-claude-desktop targets) ===
2026-03-07 03:06:31,173 - INFO - === Done! ===
2026-03-07 03:06:31,173 - INFO - Skill directory: /tmp/demo-output/example-docs
2026-03-07 03:06:31,173 - INFO - Temporary files kept in /tmp/demo-build
Normalized: /tmp/demo-build/markdown/example.com/docs/getting-started.md
Normalized: /tmp/demo-build/markdown/example.com/docs/api-reference.md
Normalized: /tmp/demo-build/markdown/example.com/docs/index.md
```

## Output Structure

The generated skill directory contains SKILL.md (entry point), references/ (converted markdown), and scripts/ (search tool):

```bash
find /tmp/demo-output/example-docs -type f | sort | sed 's|/tmp/demo-output/example-docs/||'
```

```output
SKILL.md
references/example.com/docs/api-reference.md
references/example.com/docs/getting-started.md
references/example.com/docs/index.md
scripts/README.md
scripts/search_docs.py
```

### SKILL.md

The entry point describes the skill and its usage:

```bash
cat /tmp/demo-output/example-docs/SKILL.md
```

````output
---
name: example-docs
description: EXAMPLE-DOCS documentation assistant
metadata:
  target_agent: claude
---

# EXAMPLE-DOCS Skill

This skill provides access to EXAMPLE-DOCS documentation.

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
````

### Converted Markdown

Each HTML page is converted to Markdown with YAML frontmatter (title, source URL, fetch timestamp):

```bash
cat /tmp/demo-output/example-docs/references/example.com/docs/getting-started.md
```

````output
---
title: "Getting Started"
source_url: "https://example.com/docs/getting-started"
fetched_at: "2026-03-07T03:06:31.162093+00:00"
---



# Getting Started

Install the package with pip:

```
pip install example-lib
```

Then import it in your code:

```
import example_lib
```
````

## URL Filtering

site2skill includes a URL filter module that restricts the crawl scope to prevent over-crawling. It rejects localization-only query parameters (`hl`, `lang`, `locale`) while allowing content-switching queries (`version`, `tab`):

```python3

from site2skill.url_filter import is_url_allowed

start = 'https://developer.android.com/training/data-storage/room'

# Localization queries are rejected
print('?hl=en      =>', is_url_allowed(start, start + '?hl=en'))
print('?lang=ja    =>', is_url_allowed(start, start + '?lang=ja'))

# Content queries are allowed
print('?version=2  =>', is_url_allowed(start, start + '?version=2'))
print('?tab=api    =>', is_url_allowed(start, start + '?tab=api'))

# Sibling paths outside the start URL are rejected
print('sibling     =>', is_url_allowed(start, 'https://developer.android.com/training/data-storage/shared-prefs'))

# Descendant paths are allowed
print('descendant  =>', is_url_allowed(start, start + '/advanced'))

```

```output
?hl=en      => False
?lang=ja    => False
?version=2  => True
?tab=api    => True
sibling     => False
descendant  => True
```

## Running Tests

```bash
cd /home/runner/work/site2skill/site2skill && python3 -m pytest test_site2skill.py test_url_filter.py test_integration.py test_filename_conversion.py -v 2>&1
```

```output
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/runner/work/site2skill/site2skill
configfile: pyproject.toml
collecting ... collected 26 items

test_site2skill.py::TestSite2Skill::test_generate_skill_structure PASSED [  3%]
test_site2skill.py::TestSite2Skill::test_sanitize_path PASSED            [  7%]
test_url_filter.py::TestDefaultExcludedKeys::test_default_keys PASSED    [ 11%]
test_url_filter.py::TestQueryKeyFiltering::test_hl_query_rejected PASSED [ 15%]
test_url_filter.py::TestQueryKeyFiltering::test_lang_query_rejected PASSED [ 19%]
test_url_filter.py::TestQueryKeyFiltering::test_locale_query_rejected PASSED [ 23%]
test_url_filter.py::TestQueryKeyFiltering::test_mixed_query_with_excluded_key_allowed PASSED [ 26%]
test_url_filter.py::TestQueryKeyFiltering::test_multiple_excluded_keys_rejected PASSED [ 30%]
test_url_filter.py::TestQueryKeyFiltering::test_no_query_allowed PASSED  [ 34%]
test_url_filter.py::TestQueryKeyFiltering::test_tab_query_allowed PASSED [ 38%]
test_url_filter.py::TestQueryKeyFiltering::test_version_query_allowed PASSED [ 42%]
test_url_filter.py::TestPathScope::test_descendant_path_allowed PASSED   [ 46%]
test_url_filter.py::TestPathScope::test_different_host_rejected PASSED   [ 50%]
test_url_filter.py::TestPathScope::test_different_scheme_rejected PASSED [ 53%]
test_url_filter.py::TestPathScope::test_different_section_rejected PASSED [ 57%]
test_url_filter.py::TestPathScope::test_exact_start_url_allowed PASSED   [ 61%]
test_url_filter.py::TestPathScope::test_parent_path_rejected PASSED      [ 65%]
test_url_filter.py::TestPathScope::test_sibling_path_rejected PASSED     [ 69%]
test_url_filter.py::TestPathScope::test_sibling_with_query_still_rejected PASSED [ 73%]
test_url_filter.py::TestCustomExcludedKeys::test_custom_key_rejected PASSED [ 76%]
test_url_filter.py::TestCustomExcludedKeys::test_empty_exclusion_set_allows_all_queries PASSED [ 80%]
test_url_filter.py::TestTrailingSlashNormalization::test_both_trailing_slashes PASSED [ 84%]
test_url_filter.py::TestTrailingSlashNormalization::test_candidate_with_trailing_slash PASSED [ 88%]
test_url_filter.py::TestTrailingSlashNormalization::test_start_with_trailing_slash PASSED [ 92%]
test_integration.py::test_integration_pipeline PASSED                    [ 96%]
test_filename_conversion.py::test_directory_structure_preserved PASSED   [100%]

============================== 26 passed in 0.16s ==============================
```
