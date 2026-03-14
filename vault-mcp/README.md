# vault-mcp

Personal knowledge vault MCP server for Claude Desktop. Provides tools to capture thoughts, search notes, and read files from a local markdown-based knowledge vault.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
cd vault-mcp

# Create virtual environment and install
uv venv && source .venv/bin/activate
uv pip install -e .

# Or with pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and set your vault path:

```bash
cp .env.example .env
# Edit .env and set VAULT_LOCAL_PATH to your vault directory
```

## Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

**Using python directly:**

```json
{
  "mcpServers": {
    "vault": {
      "command": "python",
      "args": ["-m", "vault_mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/path/to/second-brain"
      }
    }
  }
}
```

**Using uv (recommended):**

```json
{
  "mcpServers": {
    "vault": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/vault-mcp", "run", "python", "-m", "vault_mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/path/to/second-brain"
      }
    }
  }
}
```

## Tools

### vault_capture

Capture a thought or insight into the vault.

- **thought** (str): The content to capture
- **tags** (list[str], optional): Tags to categorize the capture

Auto-generates a timestamped filename, extracts tags from content, and writes using the capture template format. Returns the file path and related existing captures.

### vault_search

Search the vault for notes matching a query.

- **query** (str): Text to search for in filenames and content
- **directory** (str, optional): Subdirectory to search within
- **tags** (list[str], optional): Filter results by frontmatter tags

Returns matching files with path, title, status, tags, created date, and a 200-char preview.

### vault_read

Read the full content of a vault note.

- **path** (str): Relative path to the file within the vault

Returns the complete markdown content including frontmatter.

## Auto-Tag Extraction

Tags are extracted from capture text using three sources (in priority order):

1. **tags.yaml** — If a `tags.yaml` file exists at the vault root, custom tags and synonym mappings are used
2. **Existing notes** — Tags from existing vault files' frontmatter are collected and matched
3. **Default domains** — Fallback list: ai, llm, productivity, writing, coding, design, business, learning, health, finance, philosophy, psychology

Example `tags.yaml`:

```yaml
tags:
  ai: [artificial intelligence, machine learning, ML, deep learning]
  coding: [programming, software, development, code]
  design: [UX, UI, user experience]
```

## Verification

```bash
python -m py_compile src/vault_mcp/server.py
```

## Development

```bash
# Test with MCP Inspector
mcp dev src/vault_mcp/server.py
```
