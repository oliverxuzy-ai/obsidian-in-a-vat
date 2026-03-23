# vault-mcp

[English](#english) | [中文](#中文)

### Demo

<video src="assets/demo.mp4" controls width="100%">
  Your browser does not support the video tag.
</video>

---

<a id="english"></a>

## English

Personal knowledge vault MCP server for Claude Desktop. Capture thoughts, search notes, and read files from a local markdown-based knowledge vault.

---

### Quick Start (uvx — Recommended)

The lightest way to run vault-mcp. No Docker, no manual venv — just [uv](https://docs.astral.sh/uv/getting-started/installation/) and one config change.

**Step 1.** Install uv (if you don't have it):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Step 2.** Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vault": {
      "command": "uvx",
      "args": ["obsidian-in-a-vat-mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/my-vault"
      }
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

---

### Alternative Setup (Docker)

If you prefer Docker:

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

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) running in the background.

Update to latest: `docker pull ghcr.io/oliverxuzy-ai/obsidian-in-a-vat:latest`

---

### Alternative Setup (Python / uv manual)

For development or if you want to pin a local checkout:

```bash
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

| Tool | Actions | Description |
|------|---------|-------------|
| `vault_read` | `search`, `get`, `list_captures` | Search vault, read files, list captures by status |
| `vault_capture` | `save`, `delete` | Capture refined insights with auto-tagging, or delete captures |
| `vault_promote` | `promote` | Promote captures into structured notes with auto-wikilinks |
| `vault_analyze` | `rebuild_graph`, `clusters`, `connections`, `orphans` | Knowledge graph: build graph, Louvain clustering, N-degree connections, orphan detection |
| `vault_topic` | `prepare`, `create`, `update` | Topic lifecycle: gather materials (progressive disclosure), create/update MOC-style topics |

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

### 快速开始（uvx — 推荐）

最轻量的运行方式。不需要 Docker，不需要手动创建虚拟环境 — 只需安装 [uv](https://docs.astral.sh/uv/getting-started/installation/) 即可。

**第一步.** 安装 uv（如果还没有）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**第二步.** 添加到 Claude Desktop 配置文件（`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "vault": {
      "command": "uvx",
      "args": ["obsidian-in-a-vat-mcp"],
      "env": {
        "VAULT_LOCAL_PATH": "/Users/yourname/my-vault"
      }
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

---

### 备选安装方式（Docker）

如果你更喜欢用 Docker：

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

需要 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 在后台运行。

更新到最新版：`docker pull ghcr.io/oliverxuzy-ai/obsidian-in-a-vat:latest`

---

### 备选安装方式（Python / uv 手动）

适用于开发或本地调试：

```bash
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

| 工具 | Actions | 说明 |
|------|---------|------|
| `vault_read` | `search`, `get`, `list_captures` | 搜索 vault、读取文件、按状态列出 captures |
| `vault_capture` | `save`, `delete` | 捕获精炼洞察并自动打标签，或删除 capture |
| `vault_promote` | `promote` | 将 captures 提升为结构化笔记，自动插入 wikilinks |
| `vault_analyze` | `rebuild_graph`, `clusters`, `connections`, `orphans` | 知识图谱：构建图谱、Louvain 聚类、N 度关联查询、孤岛检测 |
| `vault_topic` | `prepare`, `create`, `update` | Topic 生命周期：收集原材料（渐进式披露）、创建/更新 MOC 结构笔记 |

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
