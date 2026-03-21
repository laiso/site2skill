# Pull Request: Rust Rewrite & PyPI Binary Distribution

Background: [ISSUE.md](./ISSUE.md)

## How

### Rust implementation (`src/`)

Reimplemented the 6-step pipeline from Python in Rust.

- **Fetch** — async crawler with reqwest + tokio. Semaphore-based concurrency control, robots.txt compliance
- **Convert** — HTML parsing with scraper, Markdown conversion with htmd. Removes nav/sidebar/footer via regex
- **Normalize** — reads source_url from frontmatter, resolves relative links to absolute URLs
- **Generate** — creates SKILL.md + references/ directory structure. Bundles search_docs.py template
- **Validate** — checks SKILL.md frontmatter, references/ existence, 8MB size limit
- **Package** — generates .skill file as ZIP archive

### PyPI distribution (`python/`)

Bundles the Rust binary inside a wheel using the [sqlite-scanner pattern](https://simonwillison.net/2026/Feb/4/distributing-go-binaries/).

```
python/site2skill/
├── __init__.py    # thin wrapper that locates and execs the binary
├── __main__.py    # python -m site2skill support
└── bin/site2skill  # compiled binary
```

`scripts/build-wheel.sh` handles platform detection, build, and wheel renaming.

### Code quality fixes

| Issue | Fix |
|-------|-----|
| `url_to_file_path` produces `api..html` for extensionless URLs | Append `.html` to full filename |
| `generate_skill_structure` path traversal check bypassed | Component-level `..` detection + post-mkdir canonicalize |
| `clean_html` strips only class/id attributes, leaving elements | Remove entire nav/header/footer/aside/sidebar elements via regex |
| Duplicate scope logic in `is_url_in_scope` and `url_filter::is_url_allowed` | Unified to `is_url_allowed` |
| `Regex::new()` compiled on every call across all modules | Cached with `lazy_static!` |
| Crawler accumulates all page content in `Vec<Page>` | Replaced with counter |
| Compiler warnings | All resolved (unused variables, unused types) |

### Tests

49 unit tests + 2 doc tests. Expanded from 15 to 49.

| Module | +Tests | Coverage |
|--------|--------|----------|
| `convert::html` | +8 | multiline script/style removal, nav/sidebar/footer removal, content extraction |
| `fetch::crawler` | +9 | `url_to_file_path` 6 edge cases, link extraction 3 patterns |
| `normalize` | +4 | missing frontmatter, no source_url, anchor/mailto preservation |
| `skill::structure` | +3 | structure generation, subdirectory preservation, path traversal detection |
| `skill::package` | +2 | ZIP creation with content verification, nonexistent directory |
| `validate` | +6 | valid skill, missing SKILL.md, missing references, missing frontmatter, legacy docs |

## Files Changed

### Added
- `src/` — Rust implementation
- `python/` — PyPI distribution wrapper
- `scripts/build-wheel.sh` — wheel build script
- `.cargo/config.toml` — build optimization settings
- `Cargo.toml`, `Cargo.lock`
- `templates/` — bundled templates

### Removed
- `site2skill/` — Python implementation
- `test_*.py` — Python tests

### Modified
- `pyproject.toml` — changed to hatchling-based binary distribution
- `ISSUE.md` — rewritten as motivation document

## Benchmark

Measured the conversion pipeline (Convert, Normalize, Generate, Validate) against 100 pre-downloaded HTML pages using `--skip-fetch`. Crawling (Fetch) excluded because the architectures differ (Python uses external `wget`, Rust uses a built-in async crawler).

| | Python | Rust | Ratio |
|---|--------|------|-------|
| Wall time | 0.77s | 0.15s | **5.1x** |
| CPU (user) | 0.64s | 0.09s | 7.1x |
| Peak memory (RSS) | 34MB | 11MB | 3.1x |
| Output files | 101 | 101 | equal |

Environment: macOS ARM64 (Apple Silicon), static HTML served from localhost, generated with `scripts/generate_bench_site.py --pages 100`

## Release

Version `0.2.0b1` (pre-release). `pip install site2skill` still installs the stable Python version (0.1.1). Use `pip install --pre site2skill` or `pip install site2skill==0.2.0b1` for the Rust beta.

### How to publish

1. Merge this PR
2. Tag and push: `git tag v0.2.0b1 && git push origin v0.2.0b1`
3. GHA builds wheels for 4 platforms (linux x86_64/aarch64, macOS arm64/x86_64) and publishes to PyPI

### PyPI auth setup required

The release workflow uses [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/). Before the first release:

1. Go to https://pypi.org/manage/project/site2skill/settings/publishing/
2. Add a new publisher:
   - Owner: `laiso`
   - Repository: `site2skill`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. On GitHub, go to Settings > Environments > create `pypi` environment (no secrets needed with Trusted Publishers)

## TODO

- [x] Linux build verification (GHA ubuntu-latest)
- [x] GitHub Actions CI (`cargo test`)
- [x] Multi-platform wheels (release workflow)
- [ ] PyPI Trusted Publisher setup (see above)
- [ ] Tag `v0.2.0b1` and publish
