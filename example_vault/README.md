# Example Vault

Reference vault architecture template. Copy this directory as a starting point when creating your own vault.

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `captures/` | Raw ideas, inspirations, and quick notes. Auto-written by the `vault_capture` tool |
| `notes/` | Evergreen notes distilled from captures, each focused on a single core idea |
| `topics/` | Higher-level topic pages that aggregate multiple notes in the same domain |
| `maps/` | Relationship maps for navigating connections between notes |
| `outputs/` | Generated deliverables: drafts, summaries, reports, etc. |
| `.brain/` | Machine-readable graph data (graph / clusters / review log) |
| `templates/` | Markdown templates used by MCP tools |
| `.obsidian/` | Obsidian app configuration (open this directory in Obsidian to browse) |

## Workflow

```
capture → note → topic → output
   ↓         ↓       ↓
        .brain/ (graph auto-maintained)
```

1. **Capture** — Record ideas anytime with auto-tagging and timestamped filenames
2. **Note** — Distill valuable captures into standalone notes with confidence and domain labels
3. **Topic** — When multiple notes form a pattern, aggregate them into a topic page
4. **Output** — Generate deliverables from the note network

## Templates

- `templates/capture.md` — Capture frontmatter format (status / tags / source)
- `templates/note.md` — Evergreen note format (domain / confidence / promoted_from)
- `templates/topic.md` — Topic page format (seed_notes / key notes)

## Usage

```bash
cp -r example_vault /path/to/my-vault
```

Then set `VAULT_LOCAL_PATH` to your vault directory.
