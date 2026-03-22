# site2skill

**Turn any documentation website into a Claude Agent Skill.**

`site2skill` is a tool that scrapes a documentation website, converts it to Markdown, and packages it as a Claude [Agent Skill](https://www.anthropic.com/news/skills) (ZIP format) with a proper `SKILL.md` entry point.

Agent Skills are dynamically loaded knowledge modules that Claude uses on demand. They work across Claude Code, Claude apps, and the API.

## Installation

### Install from PyPI (stable)

```bash
pip install site2skill
```

This installs the stable Python version (0.1.x), which requires Python 3.10+ and wget.

### Try the Rust beta

A rewrite in Rust is available as a beta. It's ~4x faster, has no wget dependency, and ships as a single binary.

```bash
pip install --pre site2skill
```

Or pin the version:

```bash
pip install 'site2skill==0.2.0b1'
```

Verify you're running the Rust version:

```bash
site2skill --version
# site2skill 0.2.0-beta.1
```

The stable version has no `--version` flag, so if you see a version string, you're on the Rust beta.

To go back to stable:

```bash
pip install 'site2skill<0.2'
```

### Run without Installation

```bash
# Beta (Rust)
uvx --pre site2skill <URL> <SKILL_NAME>

# Stable (Python, from legacy branch)
uvx --from 'git+https://github.com/laiso/site2skill@legacy' site2skill <URL> <SKILL_NAME>
```

### Build from Source

```bash
git clone https://github.com/laiso/site2skill.git
cd site2skill
cargo build --release
./target/release/site2skill --help
```

## Usage

```bash
# Basic usage
site2skill <URL> <SKILL_NAME>

# Example: Create a skill for PAY.JP
site2skill https://docs.pay.jp/v1/ payjp

# Example: Create a skill for uv documentation
site2skill https://docs.astral.sh/uv/ uv-docs

# Target specific agent (sets default output directory)
site2skill <URL> <SKILL_NAME> --target claude-desktop
```

## CLI Options

```
site2skill <URL> <SKILL_NAME> [options]

Options:
  --target           Target agent (claude|claude-desktop|cursor|gemini|codex). Sets default output directory
  --output, -o       Base output directory for skill structure (overrides target default)
  --skill-output     Output directory for .skill file (default: .)
  --temp-dir         Temporary directory for processing (default: build)
  --max-concurrency  Maximum number of HTTP requests to run at once (default: 10)
  --skip-fetch       Skip the download step (use existing files in temp dir)
  --clean            Clean up temporary directory after completion
  --version          Print version (Rust beta only)
```

## How it works

1.  **Fetch**: Crawls the documentation site with a built-in async HTTP crawler (robots.txt compliant, concurrent).
2.  **Convert**: Converts HTML pages to Markdown using scraper and htmd.
3.  **Normalize**: Resolves relative links to absolute URLs.
4.  **Validate**: Checks the skill structure and size limits.
5.  **Package**: Generates `SKILL.md` and zips everything into a `.skill` file.

## Output

The tool generates a skill directory in `.claude/skills/<skill_name>/` containing:

```
<skill_name>/
├── SKILL.md           # Entry point with usage instructions
├── references/        # Markdown documentation files (preferred)
└── scripts/
    └── search_docs.py # Search tool for documentation
```

Additionally, a `<skill_name>.skill` file (ZIP archive) is created in the current directory when targeting `claude-desktop`.

Legacy note: older skills may use `docs/` instead of `references/`. The search tool and validator
now support both, preferring `references/` when present.

### Search Tool

Each generated skill includes a Python search script (requires Python 3 at runtime):

```bash
python scripts/search_docs.py "<query>"
python scripts/search_docs.py "<query>" --json --max-results 5
```

## License

MIT
