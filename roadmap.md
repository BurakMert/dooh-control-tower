# Roadmap — DOOH Control Tower

A summer-long, two-phase build. Optimized for **30-min daily pomodoro chunks**. Each chunk = one PR-shaped unit that ends with `git push` and a visible artifact.

## Working agreements
- **One chunk per session.** ~25 minutes of work, one closable unit, one commit/PR. If a chunk doesn't fit a pomodoro, split it.
- **Streak > volume.** A 25-min closed chunk beats a 3-hour incomplete one.
- **Session end ritual.** Last sentence of every session: *"tomorrow we start here: M[X.Y]."* Captured in this file or in the open PR.
- **Public quiet.** Repo public from day one. No announcement (LinkedIn / Twitter / blog) until at least Phase 1 milestone M4 ships.
- **No premature polish.** README + screenshots happen at milestone boundaries, not after every chunk.
- **Visual reflections on key parts.** Concept-introducing chunks ship with a layered HTML reflection page in `docs/reflections/` (Tailwind CDN + Mermaid, single-file, no build step). Pure plumbing chunks skip it. Structure: Big Picture → What we did → How it works → Why this way (collapsed) → Go deeper (collapsed). User pulls deeper via follow-up questions; HTML expandables mirror that.
- **AI workflow skills, used habitually.** Slot skills at high-leverage moments — not every chunk. `grill-with-docs` before track design notes and library-binding chunks. `grill-me` before lessons-learned and Phase 2 design. `handoff` at session end (replaces ad-hoc "tomorrow we start here"). `/ultrareview` at milestone boundaries (end of M0/M4/M5/M6/M7). Skip a skill on any chunk where it wouldn't add value — discipline is *using them where they help*, not performing them.
- **Commit message footer when skills fire.** When one or more skills were used during a chunk, the commit message ends with `Skills: <name>, <name>` (e.g., `Skills: grill-me-with-docs, hand-over`). Git log becomes evidence of the workflow muscle, not just code muscle.
- **Biweekly workflow refresh.** Recurring `WRn` chunks between milestones (~end of M2 / M4 / M6). One pomodoro each. Strict checklist: Anthropic news + Claude Code changelog; context7 check on MCP/Pydantic AI/A2UI/CopilotKit; skim 1 community workflow source; update `CLAUDE.md` / memory **only if it changes how we work**.

---

## Phase 1 — MCP + Claude Desktop + mcp-ui  (~6 weeks)
Goal: shippable demo of all three hero journeys (planning, diagnosis, reporting) running inside Claude Desktop as an MCP server.

### M0 — Setup & first MCP tool (Week 1 — 7 chunks)
- [x] **M0.1** — Init repo, push public to GitHub (no announcement), README skeleton with thesis statement. *Shipped 2026-05-29.*
- [x] **M0.2** — Python project setup (pyproject.toml + uv + ruff), FastAPI hello-world on `/health`. *Shipped 2026-05-29.*
- [x] **M0.3** — MCP server hello-world (Python `mcp` lib), one tool returning a static string. *Shipped 2026-05-30. Reflection: [`docs/reflections/m0-3-mcp-hello-world.html`](docs/reflections/m0-3-mcp-hello-world.html).*
- [ ] **M0.4** — Register MCP server in Claude Desktop config; verify the tool appears and calls.
- [ ] **M0.4b** — Also expose the MCP server over `streamable-http`; observe SSE on the wire; reflection comparing stdio vs streamable-http side-by-side.
- [ ] **M0.5** — First domain-shaped tool: `health_check` returning a structured response.
- [ ] **M0.6** — Docker compose with Postgres + PostGIS; verify connection from FastAPI.

### M1 — Domain model & synthetic network (~5 chunks)
- [ ] M1.1 — Schema: `screen` table with PostGIS geometry column.
- [ ] M1.2 — Synthetic network generator (100 NYC screens with realistic clustering).
- [ ] M1.3 — Schema: `campaign`, `creative`, `targeting` tables.
- [ ] M1.4 — Schema: `pop_event` (daily partitions) + `pacing_bucket`.
- [ ] M1.5 — H3 indexing job (precompute res-8 and res-9 cells per screen).

### M2 — Read-only MCP surface (~5 chunks)
- [ ] M2.1 — `list_campaigns` tool.
- [ ] M2.2 — `get_campaign` tool with detail.
- [ ] M2.3 — `list_screens` tool with geo filter.
- [ ] M2.4 — First mcp-ui surface: `CampaignCard`.
- [ ] M2.5 — First mcp-ui surface: `ScreenList`.

### WR1 — Workflow refresh #1 (~Day 14)
- [ ] **WR1** — Workflow refresh: Anthropic news + Claude Code changelog, context7 version check (MCP / Pydantic AI / A2UI / CopilotKit), skim 1 community workflow source. Update `CLAUDE.md` / memory **only if** it changes how we work.

### M3 — Lite adserver + PoP capture (~5 chunks)
- [ ] M3.1 — `/ad` endpoint, deterministic round-robin, no targeting yet.
- [ ] M3.2 — Eligibility filter: active campaigns + daypart.
- [ ] M3.3 — Eligibility filter: geo targeting via PostGIS containment.
- [ ] M3.4 — Sync PoP write to event store.
- [ ] M3.5 — Synthetic PoP simulator (async driver, configurable QPS).

### M4 — Reporting hero journey (~6 chunks) **← first announcement-eligible milestone**
- [ ] M4.1 — Heatmap aggregation query (impressions × hex × hour).
- [ ] M4.2 — `get_heatmap_data` MCP tool.
- [ ] M4.3 — mcp-ui heatmap surface (H3 hex overlay).
- [ ] M4.4 — Time slider on heatmap.
- [ ] M4.5 — Drill-down on hex click → screen list.
- [ ] M4.6 — Milestone polish: README screenshot + demo gif.

### WR2 — Workflow refresh #2 (~Day 28)
- [ ] **WR2** — Workflow refresh: same checklist as WR1.

### M5 — Campaign creation hero journey (~6 chunks)
- [ ] M5.1 — `create_campaign` tool (basics only).
- [ ] M5.2 — mcp-ui campaign form (name, advertiser, schedule).
- [ ] M5.3 — Daypart picker on the form.
- [ ] M5.4 — Geo targeting (polygon paste-in or fixture).
- [ ] M5.5 — State transition `change_state` tool.
- [ ] M5.6 — Milestone polish: README update + demo gif.

### M6 — Diagnosis hero journey (~6 chunks)
- [ ] M6.1 — Pacing rebalancer service (hourly job).
- [ ] M6.2 — `get_pacing_status` tool.
- [ ] M6.3 — `diagnose_campaign` tool with cause taxonomy.
- [ ] M6.4 — mcp-ui diagnosis panel with action chips.
- [ ] M6.5 — Micro-form for one suggestion (e.g., expand polygon).
- [ ] M6.6 — Milestone polish: README update + demo gif.

### WR3 — Workflow refresh #3 (~Day 42)
- [ ] **WR3** — Workflow refresh: same checklist as WR1.

### M7 — Phase 1 closeout (~4 chunks)
- [ ] M7.1 — README v1: thesis, architecture diagram, three demo gifs.
- [ ] M7.2 — Lessons-learned doc — raw material for Phase 2 motivation (what was constrained by MCP host, what would be better owning the canvas).
- [ ] M7.3 — Tag `v0.1.0-mcp`.
- [ ] M7.4 — Optional: short blog post draft, kept private.

**Phase 1 total:** ~47 chunks (44 milestone + 3 workflow refreshes). At 30 min/day = ~6 weeks of consistent showing-up (with ~1.5 weeks of life-slack).

---

## Phase 2 — Pydantic AI + A2UI + AG-UI + CopilotKit  (~6 weeks)
Goal: standalone Next.js app, own the canvas, custom A2UI components that escape MCP host constraints. See `architecture-assessment.md` for the target architecture.

Milestone shape (to be detailed once Phase 1 M7.2 lessons-learned is written — we want the *real* motivation to drive Phase 2 priorities, not pre-decided ones):
- **P2-M0** — Spike: CopilotKit + Pydantic AI + one A2UI form, end-to-end loop proven.
- **P2-M1** — Port domain & adserver as-is (no changes), rewrite agent as Pydantic AI.
- **P2-M2** — Port reporting journey, build custom `Heatmap` A2UI component.
- **P2-M3** — Port creation journey, build custom `TargetingMap` A2UI component.
- **P2-M4** — Port diagnosis journey, build `DiagnosisPanel` A2UI component.
- **P2-M5** — Web admin routes (upload / CSV / log viewer) as plain Next.js pages.
- **P2-M6** — Closeout: architecture diagram v2, "MCP vs Generative UI" comparison post.

---

## Today's start
**Next chunk: M0.4** — Register the `dooh-mcp` server in Claude Desktop's `claude_desktop_config.json`; verify the `about` tool appears in the MCP picker and can be called from a chat. Plumbing chunk — no reflection expected.
