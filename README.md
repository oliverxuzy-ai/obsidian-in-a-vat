# vault-mcp

Personal knowledge vault MCP server for Claude Desktop. Provides tools to capture thoughts, search notes, and read files from a local markdown-based knowledge vault.

个人知识库 MCP 服务器，适配 Claude Desktop。提供工具来捕获想法、搜索笔记、读取本地 markdown 知识库中的文件。

## Prerequisites / 前置要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended / 推荐) or pip

## Setup / 安装

```bash
# Create virtual environment and install / 创建虚拟环境并安装
uv venv && source .venv/bin/activate
uv pip install -e .

# Or with pip / 或使用 pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and set your vault path:
将 `.env.example` 复制为 `.env` 并设置你的 vault 路径：

```bash
cp .env.example .env
# Edit .env — default points to ./example_vault for development
# 编辑 .env — 默认指向 ./example_vault，方便开发测试
```

## Claude Desktop Configuration / Claude Desktop 配置

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
添加到你的 Claude Desktop 配置文件：

**Using python directly / 直接使用 python：**

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

**Using uv (recommended / 推荐)：**

```json
{
  "mcpServers": {
    "vault": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/obsidian-in-a-vat", "run", "python", "-m", "vault_mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/path/to/second-brain"
      }
    }
  }
}
```

## Example Vault / 示例 Vault

`example_vault/` is a reference vault architecture template showing the directory structure and template formats. Copy it as a starting point when creating your own vault:

`example_vault/` 是参考 vault 架构模板，展示目录结构和模板格式。创建你自己的 vault 时可以复制它作为起点：

```bash
cp -r example_vault /path/to/my-vault
```

See [`example_vault/README.md`](example_vault/README.md) for details.
详见 [`example_vault/README.md`](example_vault/README.md)。

## Tools / 工具

### vault_capture

Capture a thought or insight into the vault.
捕获一个想法或洞察到 vault 中。

- **thought** (str): The content to capture / 要捕获的内容
- **tags** (list[str], optional): Tags to categorize the capture / 分类标签

Auto-generates a timestamped filename, extracts tags from content, and writes using the capture template format. Returns the file path and related existing captures.

自动生成时间戳文件名，从内容中提取标签，使用 capture 模板格式写入。返回文件路径和相关的已有 captures。

### vault_search

Search the vault for notes matching a query.
搜索 vault 中匹配查询的笔记。

- **query** (str): Text to search for in filenames and content / 在文件名和内容中搜索的文本
- **directory** (str, optional): Subdirectory to search within / 搜索的子目录
- **tags** (list[str], optional): Filter results by frontmatter tags / 按 frontmatter 标签过滤结果

Returns matching files with path, title, status, tags, created date, and a 200-char preview.
返回匹配的文件，包含路径、标题、状态、标签、创建日期和 200 字符预览。

### vault_read

Read the full content of a vault note.
读取 vault 笔记的完整内容。

- **path** (str): Relative path to the file within the vault / vault 内文件的相对路径

Returns the complete markdown content including frontmatter.
返回完整的 markdown 内容（含 frontmatter）。

## Auto-Tag Extraction / 自动标签提取

Tags are extracted from capture text using three sources (in priority order):
标签从 capture 文本中提取，使用三个来源（按优先级排序）：

1. **tags.yaml** — If a `tags.yaml` file exists at the vault root, custom tags and synonym mappings are used / 若 vault 根目录存在 `tags.yaml`，使用自定义标签和同义词映射
2. **Existing notes / 已有笔记** — Tags from existing vault files' frontmatter are collected and matched / 收集已有 vault 文件 frontmatter 中的标签进行匹配
3. **Default domains / 默认领域** — Fallback list / 兜底列表: ai, llm, productivity, writing, coding, design, business, learning, health, finance, philosophy, psychology

Example `tags.yaml`:

```yaml
tags:
  ai: [artificial intelligence, machine learning, ML, deep learning]
  coding: [programming, software, development, code]
  design: [UX, UI, user experience]
```

## Verification / 验证

```bash
python -m py_compile src/vault_mcp/server.py
```

## Development / 开发

```bash
# Test with MCP Inspector / 使用 MCP Inspector 测试
mcp dev src/vault_mcp/server.py
```
