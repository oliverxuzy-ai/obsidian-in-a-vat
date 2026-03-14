# Example Vault / 示例 Vault

Reference vault architecture template. Copy this directory as a starting point when creating your own vault.

参考 vault 架构模板。创建你自己的 vault 时，可以复制此目录作为起点。

## Directory Structure / 目录结构

| Directory | Purpose | 用途 |
|-----------|---------|------|
| `captures/` | Raw ideas, inspirations, and quick notes. Auto-written by `vault_capture` | 原始想法、灵感、快速记录，由 `vault_capture` 自动写入 |
| `notes/` | Evergreen notes distilled from captures, each focused on a single core idea | 从 capture 提炼的常青笔记，每条聚焦一个核心观点 |
| `topics/` | Higher-level topic pages that aggregate multiple notes in the same domain | 跨笔记的主题页，汇聚同一领域的多条 notes |
| `maps/` | Relationship maps for navigating connections between notes | 关系导航图，梳理笔记之间的关联 |
| `outputs/` | Generated deliverables: drafts, summaries, reports, etc. | 生成的交付物：草稿、摘要、报告等 |
| `.brain/` | Machine-readable graph data (graph / clusters / review log) | 机器可读的图谱数据 |
| `templates/` | Markdown templates used by MCP tools | MCP 工具使用的 markdown 模板 |
| `.obsidian/` | Obsidian app configuration (open this directory in Obsidian to browse) | Obsidian 应用配置 |

## Workflow / 工作流

```
capture → note → topic → output
   ↓         ↓       ↓
        .brain/ (graph auto-maintained / 图谱自动维护)
```

1. **Capture** — Record ideas anytime with auto-tagging and timestamped filenames / 随时记录想法，自动打标签、生成时间戳文件名
2. **Note** — Distill valuable captures into standalone notes with confidence and domain labels / 将有价值的 capture 提炼为独立笔记，标注 confidence 和 domain
3. **Topic** — When multiple notes form a pattern, aggregate them into a topic page / 当多条 notes 形成模式，汇聚为主题页
4. **Output** — Generate deliverables from the note network / 基于笔记网络生成交付物

## Templates / 模板

- `templates/capture.md` — Capture frontmatter format (status / tags / source) / capture 的 frontmatter 格式
- `templates/note.md` — Evergreen note format (domain / confidence / promoted_from) / 常青笔记格式
- `templates/topic.md` — Topic page format (seed_notes / key notes) / 主题页格式

## Usage / 使用方式

```bash
cp -r example_vault /path/to/my-vault
```

Then set `VAULT_LOCAL_PATH` to your vault directory.
然后将 `VAULT_LOCAL_PATH` 指向你的 vault 目录即可。
