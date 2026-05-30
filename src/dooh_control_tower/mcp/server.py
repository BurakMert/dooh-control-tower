# stdio MCP wire uses stdout for JSON-RPC frames — never print() in this module.
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="DOOH Control Tower")


@mcp.tool()
def about() -> str:
    """Describe the DOOH Control Tower MCP server: purpose, thesis, and current build phase."""
    return (
        "DOOH Control Tower — a chat-driven operational tool for Digital Out-of-Home "
        "advertising. Thesis: the agent decides WHAT to show, the app decides HOW to "
        "render. Phase 1 build: MCP + Claude Desktop + mcp-ui. The DOOH adtech "
        "(adserver, campaign manager, reporting) is the canvas; the chat-driven "
        "operational tool is the product."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
