import contextlib

from fastapi import FastAPI

from dooh_control_tower.mcp.server import mcp


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # FastMCP's session manager owns streamable-http connection lifecycle —
    # must run exactly once per process (here: per uvicorn worker).
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="DOOH Control Tower", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/mcp", mcp.streamable_http_app())
