# Example Vault

[English](#english) | [中文](#中文)

---

<a id="english"></a>

## English

Reference vault architecture template. Copy this directory as a starting point when creating your own vault.

### Directory Structure

| Directory | Purpose |
|-----------|---------|
| `captures/` | Raw ideas, inspirations, and quick notes. Auto-written by `vault_capture` |
| `notes/` | Evergreen notes distilled from captures, each focused on a single core idea |
| `topics/` | Higher-level topic pages that aggregate multiple notes in the same domain |
| `maps/` | Relationship maps for navigating connections between notes |
| `outputs/` | Generated deliverables: drafts, summaries, reports, etc. |
| `.brain/` | Machine-readable graph data (graph / clusters / review log) |
| `templates/` | Markdown templates used by MCP tools |
| `.obsidian/` | Obsidian app configuration (open this directory in Obsidian to browse) |

### Workflow

```
capture → note → topic → output
   ↓         ↓       ↓
        .brain/ (graph auto-maintained)
```

1. **Capture** — Record ideas anytime with auto-tagging and timestamped filenames
2. **Note** — Distill valuable captures into standalone notes with confidence and domain labels
3. **Topic** — When multiple notes form a pattern, aggregate them into a topic page
4. **Output** — Generate deliverables from the note network

### Templates

- `templates/capture.md` — Capture frontmatter format (status / tags / source)
- `templates/note.md` — Evergreen note format (domain / confidence / promoted_from)
- `templates/topic.md` — Topic page format (seed_notes / key notes)

### Usage

```bash
cp -r example_vault /path/to/my-vault
```

Then set `VAULT_LOCAL_PATH` to your vault directory.

---

<a id="中文"></a>

## 中文

参考 vault 架构模板。创建你自己的 vault 时，可以复制此目录作为起点。

### 目录结构

| 目录 | 用途 |
|------|------|
| `captures/` | 原始想法、灵感、快速记录，由 `vault_capture` 自动写入 |
| `notes/` | 从 capture 提炼的常青笔记，每条聚焦一个核心观点 |
| `topics/` | 跨笔记的主题页，汇聚同一领域的多条 notes |
| `maps/` | 关系导航图，梳理笔记之间的关联 |
| `outputs/` | 生成的交付物：草稿、摘要、报告等 |
| `.brain/` | 机器可读的图谱数据（graph / clusters / review log） |
| `templates/` | MCP 工具使用的 markdown 模板 |
| `.obsidian/` | Obsidian 应用配置（用 Obsidian 打开此目录即可浏览） |

### 工作流

```
capture → note → topic → output
   ↓         ↓       ↓
        .brain/ (图谱自动维护)
```

1. **Capture** — 随时记录想法，自动打标签、生成时间戳文件名
2. **Note** — 将有价值的 capture 提炼为独立笔记，标注 confidence 和 domain
3. **Topic** — 当多条 notes 形成模式，汇聚为主题页
4. **Output** — 基于笔记网络生成交付物

### 模板

- `templates/capture.md` — capture 的 frontmatter 格式（status / tags / source）
- `templates/note.md` — 常青笔记格式（domain / confidence / promoted_from）
- `templates/topic.md` — 主题页格式（seed_notes / key notes）

### 使用方式

```bash
cp -r example_vault /path/to/my-vault
```

然后将 `VAULT_LOCAL_PATH` 指向你的 vault 目录即可。
