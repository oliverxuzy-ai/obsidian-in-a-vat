# vault-mcp

[English](#english) | [中文](#中文)

---

<a id="english"></a>

## English

Personal knowledge vault MCP server for Claude Desktop. Provides tools to capture thoughts, search notes, and read files from a local markdown-based knowledge vault.

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
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
# Edit .env — default points to ./example_vault for development
# For production, set VAULT_LOCAL_PATH to your own vault directory
```

### Claude Desktop Configuration

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
      "args": ["--directory", "/absolute/path/to/obsidian-in-a-vat", "run", "python", "-m", "vault_mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/path/to/second-brain"
      }
    }
  }
}
```

### Example Vault

`example_vault/` is a reference vault architecture template showing the directory structure and template formats. Copy it as a starting point when creating your own vault:

```bash
cp -r example_vault /path/to/my-vault
```

See [`example_vault/README.md`](example_vault/README.md) for details.

### Tools

#### vault_capture

Capture a thought or insight into the vault.

- **thought** (str): The content to capture
- **tags** (list[str], optional): Tags to categorize the capture

Auto-generates a timestamped filename, extracts tags from content, and writes using the capture template format. Returns the file path and related existing captures.

#### vault_search

Search the vault for notes matching a query.

- **query** (str): Text to search for in filenames and content
- **directory** (str, optional): Subdirectory to search within
- **tags** (list[str], optional): Filter results by frontmatter tags

Returns matching files with path, title, status, tags, created date, and a 200-char preview.

#### vault_read

Read the full content of a vault note.

- **path** (str): Relative path to the file within the vault

Returns the complete markdown content including frontmatter.

### Auto-Tag Extraction

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

### Verification

```bash
python -m py_compile src/vault_mcp/server.py
```

### Development

```bash
# Test with MCP Inspector
mcp dev src/vault_mcp/server.py
```

---

<a id="中文"></a>

## 中文

个人知识库 MCP 服务器，适配 Claude Desktop。提供工具来捕获想法、搜索笔记、读取本地 markdown 知识库中的文件。

### 前置要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 安装

```bash
# 创建虚拟环境并安装
uv venv && source .venv/bin/activate
uv pip install -e .

# 或使用 pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

将 `.env.example` 复制为 `.env` 并设置你的 vault 路径：

```bash
cp .env.example .env
# 编辑 .env — 默认指向 ./example_vault，方便开发测试
# 生产环境请将 VAULT_LOCAL_PATH 设为你自己的 vault 目录
```

### Claude Desktop 配置

添加到你的 Claude Desktop 配置文件（`~/Library/Application Support/Claude/claude_desktop_config.json`）：

**直接使用 python：**

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

**使用 uv（推荐）：**

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

### 示例 Vault

`example_vault/` 是参考 vault 架构模板，展示目录结构和模板格式。创建你自己的 vault 时可以复制它作为起点：

```bash
cp -r example_vault /path/to/my-vault
```

详见 [`example_vault/README.md`](example_vault/README.md)。

### 工具

#### vault_capture

捕获一个想法或洞察到 vault 中。

- **thought** (str)：要捕获的内容
- **tags** (list[str], 可选)：分类标签

自动生成时间戳文件名，从内容中提取标签，使用 capture 模板格式写入。返回文件路径和相关的已有 captures。

#### vault_search

搜索 vault 中匹配查询的笔记。

- **query** (str)：在文件名和内容中搜索的文本
- **directory** (str, 可选)：搜索的子目录
- **tags** (list[str], 可选)：按 frontmatter 标签过滤结果

返回匹配的文件，包含路径、标题、状态、标签、创建日期和 200 字符预览。

#### vault_read

读取 vault 笔记的完整内容。

- **path** (str)：vault 内文件的相对路径

返回完整的 markdown 内容（含 frontmatter）。

### 自动标签提取

标签从 capture 文本中提取，使用三个来源（按优先级排序）：

1. **tags.yaml** — 若 vault 根目录存在 `tags.yaml`，使用自定义标签和同义词映射
2. **已有笔记** — 收集已有 vault 文件 frontmatter 中的标签进行匹配
3. **默认领域** — 兜底列表：ai, llm, productivity, writing, coding, design, business, learning, health, finance, philosophy, psychology

`tags.yaml` 示例：

```yaml
tags:
  ai: [artificial intelligence, machine learning, ML, deep learning]
  coding: [programming, software, development, code]
  design: [UX, UI, user experience]
```

### 验证

```bash
python -m py_compile src/vault_mcp/server.py
```

### 开发

```bash
# 使用 MCP Inspector 测试
mcp dev src/vault_mcp/server.py
```
