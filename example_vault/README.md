# Example Vault

参考 vault 架构模板。创建你自己的 vault 时，可以复制此目录作为起点。

## 目录结构

| 目录 | 用途 |
|------|------|
| `captures/` | 原始想法、灵感、快速记录。通过 `vault_capture` 工具自动写入 |
| `notes/` | 从 capture 提炼出的 evergreen 笔记，每条聚焦一个核心观点 |
| `topics/` | 跨笔记的主题页，汇聚同一领域的多条 notes |
| `maps/` | 关系导航图，用于梳理笔记之间的关联 |
| `outputs/` | 基于笔记生成的交付物：草稿、摘要、报告等 |
| `.brain/` | 机器可读的图谱数据（graph / clusters / review log） |
| `templates/` | MCP 工具使用的 markdown 模板 |
| `.obsidian/` | Obsidian 应用配置（用 Obsidian 打开此目录即可浏览） |

## 工作流

```
capture → note → topic → output
   ↓         ↓       ↓
        .brain/ (图谱自动维护)
```

1. **Capture** — 随时记录想法，自动打标签、生成时间戳文件名
2. **Note** — 将有价值的 capture 提炼为独立笔记，标注 confidence 和 domain
3. **Topic** — 当多条 notes 形成模式，汇聚为主题页
4. **Output** — 基于笔记网络生成交付物

## 模板

- `templates/capture.md` — capture 的 frontmatter 格式（status / tags / source）
- `templates/note.md` — evergreen note 格式（domain / confidence / promoted_from）
- `templates/topic.md` — 主题页格式（seed_notes / key notes）

## 使用方式

```bash
cp -r example_vault /path/to/my-vault
```

然后将 `vault-mcp` 的 `VAULT_LOCAL_PATH` 指向你的 vault 目录即可。
