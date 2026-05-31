# stdio MCP wire uses stdout for JSON-RPC frames — never print() in this module.
import contextlib
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP

from dooh_control_tower.db import lifespan as db_lifespan


@contextlib.asynccontextmanager
async def stdio_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Engine pool lifecycle for the stdio transport.

    HTTP transport handles db disposal via app.lifespan + AsyncExitStack.
    SQLAlchemy's engine.dispose() is idempotent, so a double-fire under
    unusual mounting setups is harmless.
    """
    async with db_lifespan():
        yield {}


# stateless_http=True: no session IDs, every HTTP request stands alone. Flag is
# a no-op for stdio transport. streamable_http_path="/" avoids the default
# `/mcp` suffix when mounted (we mount at `/mcp` ourselves in app.py).
mcp = FastMCP(name="DOOH Control Tower", stateless_http=True, lifespan=stdio_lifespan)
mcp.settings.streamable_http_path = "/"

# Side-effect import: each module under .tools registers its tools via
# @mcp.tool() decorators. Must be at bottom — tools modules import `mcp` from
# this file, so a top-of-file import would be circular.
from dooh_control_tower.mcp import tools  # noqa: E402, F401


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
