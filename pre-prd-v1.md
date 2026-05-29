# Pre-PRD v1: DOOH Lite — Chat-Driven Control Tower

*Snapshot from 2026-05-29 exploration. Tech architecture section is being revisited after introduction of Generative UI architecture (Pydantic AI + A2UI + AG-UI + CopilotKit). See `architecture-assessment.md` once written.*

## Thesis
A complete operational tool (campaign planning, mid-flight optimization, geospatial reporting) can be driven primarily through a chat interface using generative UI techniques. **DOOH adtech is the canvas; the control tower IS the product.** The adtech layer stays deliberately lite so design effort concentrates on the chat UX.

## Scope guardrails
- **In scope**: adserver (even pacing), campaign manager, hourly pacing rebalancer, geospatial reporting (H3 heatmaps), synthetic screen network + PoP simulator, generative-UI chat surface, minimal web admin for file/bulk flows.
- **Out of scope**: auctions, SSP/DSP integration, real player SDKs, multi-tenant SaaS, real audience modeling, mobile/native apps, billing.

## Core posture choices (locked)

| Decision | Choice | Rationale |
|---|---|---|
| PoP → impressions | 1:1 | Skip audience modeling; focus on UX, not adtech math. |
| Inventory | Simulated synthetic network | Self-contained, fast to spin up. |
| UI surface | Chat-primary + minimal web admin | Chat handles ops/reporting; web for uploads, CSV, raw inspection. |
| Flagship journeys | Planning + Diagnosis + Reporting (equal weight) | Broad demo of control-tower thesis. |

## Decisions under revision (pending architecture assessment)

| Decision | Original choice | Why revisiting |
|---|---|---|
| Chat host | Claude Desktop primary | Switching to custom React app (CopilotKit) per Generative UI architecture. |
| Workflow style | mcp-ui form-driven | A2UI declarative components likely replace mcp-ui forms. |
| Tech stack | Open | Pydantic AI implies Python backend. |
| UI protocol | MCP + mcp-ui | A2UI (declarative spec) + AG-UI (streaming events) instead. |

## System building blocks

### 1. Adserver (lite)
- `GET /ad?screen_id=&ts=` → returns winning creative + records PoP.
- Eligibility filter: campaign active, daypart match, geo includes screen, has hour budget remaining.
- Selection: priority-weighted round robin among eligible (no auction).
- PoP write is sync to event store; everything else off the hot path.

### 2. Campaign Manager
- Entities: Campaign, Creative, Targeting (geo polygons + daypart + screen include/exclude), Schedule (start/end/goal).
- State machine: `draft → scheduled → active → paused → completed`.
- Every operation surfaced through chat-resident generative UI.

### 3. Pacing rebalancer (async)
- Runs at hour boundary.
- Inputs: PoPs last hour, total goal, time remaining, forecasted opportunity per remaining hour (= eligible screens × eligible slots).
- Output: `pacing_bucket` rows — `(campaign_id, hour_ts, impression_target)` for remaining hours.
- Adserver consults current-hour bucket to throttle.

### 4. Reporting
- Storage: Postgres + PostGIS for raw entities/events; H3 cells (res 8 primary, res 9 drill-down) precomputed per screen.
- Aggregations: `(campaign × hex × hour)` impressions, plus per-screen and per-campaign rollups.
- Reads served via agent tools, rendered through generative UI components.

### 5. Agent + UI surface (to be revised)
Tool taxonomy (transport-agnostic):
- **Query**: `list_campaigns`, `get_campaign`, `get_pacing_status`, `get_heatmap_data`, `get_screen_detail`, `diagnose_campaign`.
- **Mutation**: `create_campaign`, `update_targeting`, `change_state` (pause/resume/launch), `attach_creative`.
- **UI emission**: agent emits component specs (form, map, heatmap, diagnosis panel, card) rather than UI launcher tools.

### 6. UI component library (the design surface)
- `campaign-form` — multi-section form (basics, schedule, targeting embed, creative ref).
- `targeting-map` — interactive map for polygon draw + screen include/exclude + dayparting picker.
- `heatmap` — H3 hex overlay with time slider, hover detail, click-to-drill.
- `time-series-chart` — pacing actual vs plan, daypart distribution.
- `diagnosis-panel` — under-pacing breakdown with inline action chips that trigger micro-forms.
- `campaign-card` — compact summary used inline by query tools.

### 7. Web admin (intentionally tiny)
- Single-user auth (session cookie, hardcoded creds for dev).
- Creative upload (PNG/JPG/MP4 → object store).
- Bulk CSV imports (screens, targeting rules).
- Raw event log viewer (escape hatch for debugging).

### 8. Synthetic network + PoP simulator
- Generates ~500 fictional screens across one city (NYC default) with realistic lat/lng clustering + daypart profiles.
- Simulator hits the live adserver at configurable QPS, with realistic spatial/temporal distribution.
- Used in dev and demo; bypassed in any future "real" mode.

## Hero journeys

### A. Planning & launch
> "Plan a 2-week Times Square campaign for Brand X, weekday mornings only, 500k impressions."
- Agent opens a campaign form, pre-filled with inferable fields from the prompt.
- Targeting map embedded; user draws/selects polygon; daypart matrix below.
- Submit → `create_campaign` → confirmation card with state transition button.

### B. Mid-flight diagnosis
> "Brand X is under-pacing in Brooklyn — why?"
- Agent emits diagnosis panel.
- Shows: plan vs actual, geo breakdown, suspected causes (low opportunity, daypart conflict, creative rejection).
- Inline action chips ("expand polygon by 2km", "raise priority", "add adjacent hexes") → micro-form → applies change.

### C. Reporting & insight
> "Show yesterday's delivery heatmap for Brand X by hour."
- Agent emits heatmap component with filter → H3 hex overlay, time slider, color by impression count.
- Drill: click hex → screen list → click screen → screen detail card.

## Data model sketch
- `screen(id, lat, lng, h3_r8, h3_r9, loop_slots, daypart_profile_id)`
- `campaign(id, name, advertiser, state, start_ts, end_ts, goal_impressions, priority)`
- `creative(id, campaign_id, file_uri, duration_s, format)`
- `targeting(campaign_id, geo_polygons jsonb, dayparts jsonb, screen_include[], screen_exclude[])`
- `pop_event(ts, screen_id, campaign_id, creative_id, h3_r8, h3_r9)` — partitioned by day.
- `pacing_bucket(campaign_id, hour_ts, target, actual)`

## Open questions for grill-me
1. **Tech stack** (now leaning Python via Pydantic AI): exact framework choices for adserver, reporting, web admin.
2. **A2UI component sourcing**: build all from scratch vs find a starter kit.
3. **Pacing cadence**: hourly vs 15-min rebalance. Hourly is simpler; 15-min more responsive in the diagnosis demo.
4. **Daypart granularity**: hour-of-week (168 buckets) vs minute-level (more realistic, more UI work).
5. **Synthetic network size**: 100 vs 500 vs 2000 screens. Affects sim load, map readability, query plans.
6. **Event store**: Postgres rows vs TimescaleDB hypertable vs DuckDB analytics layer.
7. **Chat session state**: how does the agent "remember" the current campaign across turns — pure tool-call args, agent-side session, or frontend-resident state?
8. **Failure UX**: when a tool/form errors mid-flow, what's the chat-native recovery pattern?
9. **Creative formats**: PNG/JPG only or include MP4? Affects storage, web admin, preview rendering.
10. **Reach estimation**: at creation time, do we forecast reachable impressions from targeting? Adds value to the planning journey but needs an opportunity model.

## Success criteria
- All three hero journeys complete fully in chat, with web admin only used for legitimate escape-valve cases.
- The demo reads as one coherent product, not a chatbot wrapped around an app.
- Single-person buildable on nights/weekends.
