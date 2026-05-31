# DOOH Control Tower

A chat-driven operational tool for Digital Out-of-Home (DOOH) advertising.

> **Thesis:** *Agent decides WHAT to show, App decides HOW to render.*
> DOOH adtech is the canvas; the chat-driven operational tool IS the product.

## Status

Active learning project, summer 2026. Two-phase build:

- **Phase 1** — MCP server + Claude Desktop + mcp-ui
- **Phase 2** — Pydantic AI + A2UI + AG-UI + CopilotKit (Next.js app)

See [`roadmap.md`](./roadmap.md) for the milestone + chunk plan.

## Docs

- [`pre-prd-v1.md`](./pre-prd-v1.md) — initial pre-PRD snapshot
- [`architecture-assessment.md`](./architecture-assessment.md) — Phase 2 target architecture
- [`roadmap.md`](./roadmap.md) — milestone + chunk plan (source of truth)

## Reflections

Layered HTML reflection pages — what we built, how it works, decisions, prompts to go deeper.

- [`m0-3-mcp-hello-world.html`](./docs/reflections/m0-3-mcp-hello-world.html) — FastMCP hello-world over stdio (M0.3)
- [`m0-4b-stdio-vs-streamable-http.html`](./docs/reflections/m0-4b-stdio-vs-streamable-http.html) — one FastMCP instance, two transports: stdio + streamable-http/SSE (M0.4b)
- [`m0-5-structured-output.html`](./docs/reflections/m0-5-structured-output.html) — typed Pydantic returns, auto-generated outputSchema, structuredContent on the wire (M0.5)
