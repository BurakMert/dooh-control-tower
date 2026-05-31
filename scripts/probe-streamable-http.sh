#!/usr/bin/env bash
# Probe the streamable-http MCP transport. Captures raw SSE frames for three
# calls: initialize, tools/list, tools/call about. Run while uvicorn is up:
#   uv run uvicorn dooh_control_tower.app:app --reload
# Override the URL via MCP_URL=... if you serve on a different host/port.

set -euo pipefail

URL="${MCP_URL:-http://localhost:8000/mcp/}"

call() {
  local label="$1"
  local body="$2"
  echo "=== $label ==="
  curl -sN \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$body" \
    "$URL"
  echo
  echo
}

call "initialize" \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"0.0"}}}'

call "tools/list" \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

call "tools/call about" \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"about","arguments":{}}}'

call "tools/call health_check" \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"health_check","arguments":{}}}'
