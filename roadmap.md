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
- [x] **M0.4** — Register MCP server in Claude Desktop config; verify the tool appears and calls. *Shipped 2026-05-30. Verified via Connectors panel + live `about` call.*
- [x] **M0.4b** — Also expose the MCP server over `streamable-http`; observe SSE on the wire; reflection comparing stdio vs streamable-http side-by-side. *Shipped 2026-05-30. Reflection: [`docs/reflections/m0-4b-stdio-vs-streamable-http.html`](docs/reflections/m0-4b-stdio-vs-streamable-http.html).*
- [x] **M0.5** — First domain-shaped tool: `health_check` returning a structured response. *Shipped 2026-05-31. Reflection: [`docs/reflections/m0-5-structured-output.html`](docs/reflections/m0-5-structured-output.html).*
- [x] **M0.6** — Docker compose with Postgres + PostGIS; verify connection from FastAPI. *Shipped 2026-05-31. Reflection: [`docs/reflections/m0-6-postgres-bind.html`](docs/reflections/m0-6-postgres-bind.html).*
  - [x] **M0.6a** — `docker-compose.yml` with `postgis/postgis:17-3.5` (Apple Silicon: `platform: linux/amd64` pin); verified via `psql` (PostgreSQL 17.5, PostGIS 3.5 with GEOS/PROJ/STATS). *Shipped 2026-05-31.*
  - [x] **M0.6b** — SQLAlchemy 2.0 async + psycopg3 (chosen via `grill-with-docs` over asyncpg for the sync+async one-driver win). `db.py` engine + session factory + lifespan; `app.py` composes lifespans via `AsyncExitStack`; `health_check` extended with a `postgres` component running `SELECT PostGIS_full_version()`. *Shipped 2026-05-31.*

### M1 — Domain model & synthetic network (~6 chunks)
- [x] **M1.1** — Schema: `screen` table with PostGIS geometry column. SQLA 2.0 Declarative + `Mapped[T]`, GeoAlchemy2 `Geometry("POINT", srid=4326, spatial_index=True)`, Alembic bootstrapped with `include_object` filter (skips postgis/TIGER tables), `count_screens` MCP tool. *Shipped 2026-06-01. Reflection: [`docs/reflections/m1-1-first-spatial-table.html`](docs/reflections/m1-1-first-spatial-table.html).*
- [x] **M1.2** — Synthetic network generator. 100 screens, 12 hand-curated NYC anchors (Manhattan 60% / Brooklyn 25% / Queens 15%), seeded `random.Random(42)`, ~500m uniform jitter. CLI entrypoint `dooh-seed` (registered in pyproject). SQLA Core bulk insert via `pg_insert.on_conflict_do_nothing(external_id)` — idempotent. Verified: `count_screens` returns 100; market tally 53/28/19. *Shipped 2026-06-01. Reflection: [`docs/reflections/m1-2-synthetic-network.html`](docs/reflections/m1-2-synthetic-network.html).*
- [x] **M1.3** — *First mcp-ui surface.* `show_screen_map` registered as a `@mcp.resource(ui://dooh-control-tower/screen-map)` returning a self-contained ~26KB Leaflet rawHtml page (CARTO Voyager Light tiles, MIME `text/html;profile=mcp-app`); tool's `_meta.ui.resourceUri` points the host at it (MCP Apps SEP-1724 pattern). 100 markers color-coded by market (Manhattan indigo / Brooklyn emerald / Queens amber). HTML loads `@modelcontextprotocol/ext-apps@^1.7.0` and calls `App.connect({strict:true})` for the host handshake. Resource carries `preferred-frame-size: [100%, 560px]`. Sibling `list_screens` tool ships `ScreenSummary` (M2.3-extensible). *Verified in MCPJam Inspector* (renders cleanly). *Does not render in stock Claude Desktop* (host categorizes as Interactive + injects "widget rendered" context message, but iframe contents invisible — tracking via `anthropics/claude-ai-mcp#165`). Pulled forward from M2.4/M2.5. *Shipped 2026-06-02. Reflection: [`docs/reflections/m1-3-first-mcp-ui-surface.html`](docs/reflections/m1-3-first-mcp-ui-surface.html).*
- [x] **M1.4** — Schema: `campaign`, `creative`, `targeting` tables. SQLA 2.0 `Mapped[T]` with one 1:N (`campaign` → `creative`) and one 1:1 (`campaign` → `targeting`, enforced via UNIQUE on `campaign_id`). FK `ON DELETE CASCADE` both ways. First `MULTIPOLYGON` column on `targeting.geom` (4326, GiST). Single Alembic revision — the `include_object` filter from M1.1 kept the diff clean (60 lines, zero TIGER drift). Extended `seed.py` with `seed_campaigns()`: 10 campaigns (7 active / 1 draft / 1 paused / 1 completed), 16 creatives (1-3 per campaign), 10 bbox+buffer targeting polygons sampled from existing screens. Two-phase async insert (campaigns → resolve UUIDs → wire FK on children). Verified: `ST_Contains(targeting.geom, screen.geom)` returns 19-48 screens/polygon — M3.3 eligibility sets will not be empty. *Shipped 2026-06-03. Reflection: [`docs/reflections/m1-4-multi-table-schema.html`](docs/reflections/m1-4-multi-table-schema.html).*
- [ ] M1.5 — Schema: `pop_event` (daily partitions) + `pacing_bucket`.
- [ ] M1.6 — H3 indexing job (precompute res-8 and res-9 cells per screen).

### M2 — Read-only MCP surface (~5 chunks)
- [ ] M2.1 — `list_campaigns` tool.
- [ ] M2.2 — `get_campaign` tool with detail.
- [ ] M2.3 — `list_screens` tool with geo filter (extends the minimal `list_screens` shipped in M1.3 with geo predicates).
- [ ] M2.4 — Second mcp-ui surface: `CampaignCard`.
- [ ] M2.5 — Third mcp-ui surface: `ScreenList` (tabular complement to the M1.3 map).

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
**Next chunk: M1.5** — `pop_event` (daily partitions) + `pacing_bucket`. First time-series schema in the project. Decisions to land at the top: (1) **partition strategy** — declarative `PARTITION BY RANGE (event_date)` with one partition per day, or month-level partitions with daily indexes? Daily is cheaper to drop/archive; monthly is fewer DDL objects. (2) **PK shape on a partitioned table** — Postgres requires the partition key in any UNIQUE/PK; common patterns are `(id, event_date)` composite PK or no surrogate PK at all (just a covering index). (3) **`pacing_bucket` cardinality** — one row per (campaign, hour) for the last N days? Or (campaign, hour-of-day) collapsed across days? M6.1 (pacing rebalancer) needs the former; M4 (heatmap) might want both. (4) **Alembic + partitioning** — Alembic doesn't autogenerate `PARTITION BY` syntax; we'll likely need to write the migration mostly by hand using `op.execute()`. (5) **PoP simulator (M3.5) scale** — what QPS is realistic for the seed? 10 events/sec for 7 days = ~6M rows. Daily partitions handle that comfortably; flat table starts to feel it. Reflection-eligible (first partitioning, first hand-written migration).

**Reminder:** docker compose stack is left running. If it's not, `docker compose up -d` from the repo root.

**Reminder:** docker compose stack is left running. If it's not, `docker compose up -d` from the repo root.
