# vault-mcp

[English](#english) | [中文](#中文)

---

<a id="english"></a>

## English

Personal knowledge vault MCP server for Claude Desktop. Capture thoughts, search notes, and read files from a local markdown-based knowledge vault.

---

### Quick Start (Docker — Recommended)

**Step 1.** Make sure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is running.

**Step 2.** Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vault": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/yourname/my-vault:/vault",
        "ghcr.io/oliverxuzy-ai/obsidian-in-a-vat:latest"
      ]
    }
  }
}
```

Replace `/Users/yourname/my-vault` with the absolute path to your local vault directory.

**Step 3.** Fully quit and reopen Claude Desktop. The `vault` tools will appear automatically.

> **Don't have a vault yet?** Copy the included template:
> ```bash
> cp -r example_vault /Users/yourname/my-vault
> ```

#### Updating to the Latest Version

When a new version is released, pull the latest image before restarting Claude Desktop:

```bash
docker pull ghcr.io/oliverxuzy-ai/obsidian-in-a-vat:latest
```

---

### Alternative Setup (Python / uv)

If you prefer not to use Docker:

```bash
# Install
uv venv && source .venv/bin/activate
uv pip install -e .
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "vault": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "vault_mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/my-vault"
      }
    }
  }
}
```

> Use the absolute path to the venv's python — Claude Desktop does not inherit your shell PATH.

---

### Tools

| Tool | Description |
|------|-------------|
| `vault_capture` | Capture a refined insight — Claude distills your thought, confirms with you, then stores it with auto-tagging |
| `vault_promote` | Promote one or more captures into a structured note with auto-wikilink insertion |
| `vault_search` | Search the vault by text query, subdirectory, or frontmatter tags |
| `vault_read` | Read the full markdown content of a vault note |
| `vault_list_captures` | List captures filtered by status (`capture` / `promoted` / `all`), sorted newest first |

---

### Auto-Tag Extraction

Tags are extracted from capture text using three sources (in priority order):

1. **tags.yaml** — Custom tags and synonym mappings at the vault root
2. **Existing notes** — Tags collected from existing vault files' frontmatter
3. **Default domains** — Fallback: ai, llm, productivity, writing, coding, design, business, learning, health, finance, philosophy, psychology

Example `tags.yaml` in your vault root:

```yaml
tags:
  ai: [artificial intelligence, machine learning, ML, deep learning]
  coding: [programming, software, development, code]
  design: [UX, UI, user experience]
```

---

### Development

```bash
# Build image locally
docker build -t vault-mcp .

# Test the container starts (Ctrl+C to stop)
echo '{}' | docker run -i --rm -v $(pwd)/example_vault:/vault vault-mcp

# Syntax check
python -m py_compile src/vault_mcp/server.py

# Interactive MCP Inspector
mcp dev src/vault_mcp/server.py
```

---

<a id="中文"></a>

## 中文

个人知识库 MCP 服务器，适配 Claude Desktop。捕获想法、搜索笔记、读取本地 markdown 知识库中的文件。

---

### 快速开始（Docker — 推荐）

**第一步.** 确保 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 正在运行。

**第二步.** 添加到 Claude Desktop 配置文件（`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "vault": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/yourname/my-vault:/vault",
        "ghcr.io/oliverxuzy-ai/obsidian-in-a-vat:latest"
      ]
    }
  }
}
```

将 `/Users/yourname/my-vault` 替换为你本地 vault 目录的绝对路径。

**第三步.** 完全退出并重新打开 Claude Desktop，`vault` 工具会自动出现。

> **还没有 vault？** 复制内置模板：
> ```bash
> cp -r example_vault /Users/yourname/my-vault
> ```

#### 更新到最新版本

当有新版本发布时，在重启 Claude Desktop 前先拉取最新镜像：

```bash
docker pull ghcr.io/oliverxuzy-ai/obsidian-in-a-vat:latest
```

---

### 备选安装方式（Python / uv）

如果不想使用 Docker：

```bash
# 安装
uv venv && source .venv/bin/activate
uv pip install -e .
```

Claude Desktop 配置：

```json
{
  "mcpServers": {
    "vault": {
      "command": "/绝对路径/.venv/bin/python",
      "args": ["-m", "vault_mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/my-vault"
      }
    }
  }
}
```

> 必须使用 venv 内 python 的绝对路径 — Claude Desktop 不继承你的 shell PATH。

---

### 工具

| 工具 | 说明 |
|------|------|
| `vault_capture` | 捕获精炼洞察 — Claude 提炼你的想法，经确认后存储并自动打标签 |
| `vault_promote` | 将一个或多个 capture 提升为结构化笔记，自动插入 wikilinks |
| `vault_search` | 按文本、子目录或 frontmatter 标签搜索 vault |
| `vault_read` | 读取 vault 笔记的完整 markdown 内容 |
| `vault_list_captures` | 按状态筛选 captures（`capture` / `promoted` / `all`），按时间倒序排列 |

---

### 自动标签提取

标签从 capture 文本中提取，使用三个来源（按优先级排序）：

1. **tags.yaml** — vault 根目录的自定义标签和同义词映射
2. **已有笔记** — 收集已有 vault 文件 frontmatter 中的标签进行匹配
3. **默认领域** — 兜底列表：ai, llm, productivity, writing, coding, design, business, learning, health, finance, philosophy, psychology

`tags.yaml` 示例（放在 vault 根目录）：

```yaml
tags:
  ai: [artificial intelligence, machine learning, ML, deep learning]
  coding: [programming, software, development, code]
  design: [UX, UI, user experience]
```

---

### 开发

```bash
# 本地构建镜像
docker build -t vault-mcp .

# 测试容器启动（Ctrl+C 停止）
echo '{}' | docker run -i --rm -v $(pwd)/example_vault:/vault vault-mcp

# 语法检查
python -m py_compile src/vault_mcp/server.py

# 使用 MCP Inspector 交互测试
mcp dev src/vault_mcp/server.py
```
