# Scripts

This directory contains utility scripts for working with the skill documentation.

## search_docs.py

Full-text search tool for the documentation.

### Usage

```bash
# Basic search
python search_docs.py "query"

# Limit results
python search_docs.py "query" --max-results 5

# JSON output
python search_docs.py "query" --json
```

### Options

- `query` - Search query (space-separated for multiple keywords)
- `--max-results, -n` - Maximum number of results (default: 10)
- `--json` - Output as JSON
- `--skill-dir` - Skill directory (default: auto-detected from script location)
