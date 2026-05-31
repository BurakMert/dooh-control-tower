# stdio MCP wire uses stdout for JSON-RPC frames — never print() in this module.
from mcp.server.fastmcp import FastMCP

# stateless_http=True: no session IDs, every HTTP request stands alone. Flag is
# a no-op for stdio transport. streamable_http_path="/" avoids the default
# `/mcp` suffix when mounted (we mount at `/mcp` ourselves in app.py).
mcp = FastMCP(name="DOOH Control Tower", stateless_http=True)
mcp.settings.streamable_http_path = "/"

# Side-effect import: each module under .tools registers its tools via
# @mcp.tool() decorators. Must be at bottom — tools modules import `mcp` from
# this file, so a top-of-file import would be circular.
from dooh_control_tower.mcp import tools  # noqa: E402, F401


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
