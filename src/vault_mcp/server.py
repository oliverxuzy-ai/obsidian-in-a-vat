import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from vault_mcp.adapters.local import LocalStorageAdapter
from vault_mcp.tools.read import register_read_tools
from vault_mcp.tools.write import register_write_tools

load_dotenv()

# All logging goes to stderr — stdout is reserved for JSON-RPC (stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("vault-mcp")

mcp = FastMCP("vault")


def _get_adapter() -> LocalStorageAdapter:
    vault_path = os.environ.get("VAULT_LOCAL_PATH")
    if not vault_path:
        logger.error("VAULT_LOCAL_PATH environment variable is not set")
        sys.exit(1)
    return LocalStorageAdapter(vault_path)


adapter = _get_adapter()

register_write_tools(mcp, adapter)
register_read_tools(mcp, adapter)


def main() -> None:
    logger.info("Starting vault MCP server")
    mcp.run(transport="stdio")
