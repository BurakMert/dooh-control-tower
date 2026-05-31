# Side-effect imports: each module registers its tools by applying the
# @mcp.tool() decorator at import time. server.py imports this package once
# during startup; new tools are added by creating a new module here and adding
# it to the line below.
from dooh_control_tower.mcp.tools import about, health  # noqa: F401
