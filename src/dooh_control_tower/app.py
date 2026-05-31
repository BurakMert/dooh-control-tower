import contextlib

from fastapi import FastAPI

from dooh_control_tower.db import lifespan as db_lifespan
from dooh_control_tower.mcp.server import mcp


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Two resources to manage per uvicorn worker:
    #   1. mcp.session_manager — streamable-http session lifecycle (FastMCP).
    #   2. db engine pool — disposed on shutdown.
    # AsyncExitStack composes them; both unwind cleanly on exception.
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        await stack.enter_async_context(db_lifespan())
        yield


app = FastAPI(title="DOOH Control Tower", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/mcp", mcp.streamable_http_app())
