# site2skill

**Turn any documentation website into a Claude Agent Skill.**

`site2skill` is a tool that scrapes a documentation website, converts it to Markdown, and packages it as a Claude [Agent Skill](https://www.anthropic.com/news/skills) (ZIP format) with a proper `SKILL.md` entry point.

Agent Skills are dynamically loaded knowledge modules that Claude uses on demand. They work across Claude Code, Claude apps, and the API.

## Installation

**Requirements:**
*   **Python 3.10+**
*   **wget**: Must be installed and available in your PATH.
    *   macOS: `brew install wget`
    *   Linux: `apt install wget`
    *   Windows: Use WSL, or install via `choco install wget` / `scoop install wget`

### Install from PyPI

```bash
# Standard installation with pip
pip install site2skill

# Or with uv
uv tool install site2skill
```

### Run without Installation

```bash
# Run directly with uvx
uvx site2skill <URL> <SKILL_NAME>
```

### Install from GitHub (Latest)

```bash
pip install git+https://github.com/laiso/site2skill.git
uvx --from git+https://github.com/laiso/site2skill site2skill <URL> <SKILL_NAME>
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
  --skip-fetch       Skip the download step (use existing files in temp dir)
  --clean            Clean up temporary directory after completion
```

## How it works

1.  **Fetch**: Downloads the documentation site recursively using `wget`.
2.  **Convert**: Converts HTML pages to Markdown using `beautifulsoup4` and `markdownify`.
3.  **Normalize**: Cleans up links and formatting.
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

Additionally, a `<skill_name>.skill` file (ZIP archive) is created in the current directory.

Legacy note: older skills may use `docs/` instead of `references/`. The search tool and validator
now support both, preferring `references/` when present.

### Search Tool

Each generated skill includes a search script:

```bash
python scripts/search_docs.py "<query>"
python scripts/search_docs.py "<query>" --json --max-results 5
```

## License

MIT
