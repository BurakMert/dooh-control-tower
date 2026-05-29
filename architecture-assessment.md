# Architecture Assessment: Generative UI for DOOH Control Tower

*Assessment date: 2026-05-29. Based on current docs for Pydantic AI, A2UI v0.9, AG-UI protocol, CopilotKit `@copilotkit/a2ui-renderer`.*

## TL;DR
**Verdict: feasible, well-matched, lock it in.** The four pieces compose cleanly into the stack the screenshot describes. The hard part isn't the wiring (CopilotKit ships a one-line A2UI renderer; Pydantic AI ships `agent.to_ag_ui()`); the hard part is designing the *custom* A2UI components for maps and heatmaps, and the action schemas for spatial interactions like polygon drawing and hex drill-down.

The thesis — "Agent decides WHAT to show, App decides HOW to render" — maps well to DOOH ops: an agent that knows the campaign domain emits semantic UI (form, diagnosis panel, heatmap), and the React app owns the visual realization.

## 1. What each piece does (verified from current docs)

### Pydantic AI (Python agent framework)
- Defines an agent with `Agent('openai:gpt-4.1', instructions=..., deps_type=...)`.
- `agent.to_ag_ui()` exposes the agent as an ASGI app — drop into FastAPI/Starlette.
- `StateDeps[SomeModel]` automatically decodes shared state from `RunAgentInput` so the agent sees current UI state on each turn.
- `@agent.tool` decorator. Tools can return AG-UI events directly (`StateSnapshotEvent`, `CustomEvent`, etc.) or domain objects.
- Streaming via `agent.run_stream(...)` for token-level deltas.

### A2UI (Google, v0.9)
- JSONL-based declarative UI spec. Three core message envelopes:
  - `surfaceUpdate` — declares the component tree for a named surface.
  - `dataModelUpdate` — seeds/updates the data the components bind to.
  - `beginRendering` — flips the surface from "being built" to "render now".
- Built-in catalog: `Text`, `Card`, `Button`, `Column/Row`, `TextField`, `DateTimeInput`, `CheckBox`, `MultipleChoice`, `Image`, `List`.
- **Bidirectional binding**: a `TextField` with `"text": {"path": "/form/name"}` reads from and writes to that data-model path on input.
- **Actions**: on user interaction (button click etc.) the renderer emits an action message back: `{action: {name, surfaceId, sourceComponentId, timestamp, context}}`. Context can carry arbitrary data the component knows about.
- **BYOC (Bring Your Own Components)**: define a Zod schema for props + a typed React component, register it in the A2UI catalog. This is how we add `TargetingMap`, `Heatmap`, etc.

### AG-UI Protocol (streaming envelope)
- SSE-based event stream between agent and client.
- Event types: `RUN_STARTED`, `TOOL_CALL_START`, `STATE_DELTA`, `A2UI_UPDATE` (or `CUSTOM` carrying A2UI lines), `TOOL_CALL_END`, `RUN_FINISHED`.
- Bidirectional: actions/inputs from the client also flow as events to the agent.
- Pydantic AI has a first-party adapter — `pydantic_ai.ag_ui.StateDeps` for the state side, `agent.to_ag_ui()` for the transport side.

### CopilotKit React SDK
- `<CopilotKitProvider runtimeUrl="/api/copilotkit-a2ui" renderActivityMessages={[A2UIRenderer]}>` wires the agent's stream into React.
- `createA2UIMessageRenderer({ theme })` returns a renderer that intercepts A2UI JSONL activity messages from the stream and renders them as live UI inside the chat or alongside it.
- `<CopilotSidebar />` provides the chat shell (collapsible side panel).
- User interactions on rendered A2UI components are automatically relayed back to the agent as tool responses / actions.

## 2. End-to-end pipeline for our project

```
[User types in CopilotSidebar]
        ↓ (HTTP/SSE)
[Next.js API route /api/copilotkit-a2ui]
        ↓ (proxies to)
[Pydantic AI agent.to_ag_ui() — ASGI]
        ├── deps: StateDeps[DOOHState]   (current_campaign_id, filters, etc.)
        ├── tools: list_campaigns, create_campaign, diagnose_campaign,
        │           get_heatmap_data, change_state, ...
        └── tool body returns A2UI JSONL ({surfaceUpdate}, {dataModelUpdate}, {beginRendering})
        ↓ (AG-UI events stream back)
[A2UIRenderer in React]
        ├── built-in catalog handles Text/Card/Button/TextField/etc.
        └── BYOC catalog handles TargetingMap, Heatmap, PacingChart, DaypartGrid
        ↓
[User clicks/drags/types]
        ↓ ({action: {name, surfaceId, context}})
[Back to Pydantic AI as tool response or new turn]
```

## 3. Mapping to our hero journeys

### A. Planning & launch — `campaign-form` surface
Agent emits a `surfaceUpdate` with this skeleton:

```jsonl
{"surfaceUpdate": {"surfaceId": "campaign-form", "components": [
  {"id": "root", "component": "Column", "children": ["title", "basics", "schedule", "targeting", "creative", "submit"]},
  {"id": "title", "component": "Text", "text": "# New campaign", "variant": "h1"},
  {"id": "basics-name", "component": "TextField", "label": "Campaign name", "text": {"path": "/campaign/name"}},
  {"id": "basics-adv",  "component": "TextField", "label": "Advertiser", "text": {"path": "/campaign/advertiser"}},
  {"id": "schedule-start", "component": "DateTimeInput", "label": "Start", "value": {"path": "/campaign/start_ts"}},
  {"id": "schedule-end",   "component": "DateTimeInput", "label": "End",   "value": {"path": "/campaign/end_ts"}},
  {"id": "targeting-map",  "component": "TargetingMap", "polygons": {"path": "/campaign/targeting/polygons"}, "screens": {"path": "/campaign/targeting/screens"}},
  {"id": "targeting-daypart", "component": "DaypartGrid", "value": {"path": "/campaign/targeting/dayparts"}},
  {"id": "submit", "component": "Button", "label": "Launch campaign", "action": {"event": {"name": "create_campaign"}}}
]}}
{"dataModelUpdate": {"surfaceId": "campaign-form", "path": "/campaign", "contents": [
  {"key": "name", "value": "Brand X — Times Square"},
  {"key": "advertiser", "value": "Brand X"},
  {"key": "start_ts", "value": "2026-06-01T00:00:00Z"},
  {"key": "end_ts",   "value": "2026-06-15T00:00:00Z"},
  {"key": "targeting", "value": {"polygons": [...], "dayparts": {...}}}
]}}
{"beginRendering": {"surfaceId": "campaign-form", "root": "root"}}
```

Pre-fill from the user's natural-language prompt happens at `dataModelUpdate` time. Submit dispatches an `action` event with `/campaign` resolved as context — Pydantic AI `@agent.tool` for `create_campaign` receives it.

### B. Mid-flight diagnosis — `diagnosis` surface
Agent calls `diagnose_campaign(id, dimension)`, the tool builds findings, and emits a surface with:
- `Card` summary of pacing actual vs plan.
- `Heatmap` (BYOC) showing geo distribution of under-delivery.
- `List` of suspected causes, each row with an action `Button` that dispatches a micro-form for the suggested change.

Action chips re-enter the agent loop, which emits a follow-up surface (e.g., `expand-polygon-form`). Iterative refinement loop matches the chat metaphor.

### C. Reporting & insight — `heatmap` surface
Custom `Heatmap` component:
- Props (path-bound): `cells` (H3 → impressions count), `timeRange`, `selectedHour`, `selectedHex`.
- Internal interactivity: time slider, hex hover, hex click → emits action `drill_hex` with `{hex, hour}` in context.
- Agent receives `drill_hex` → fetches per-screen breakdown → emits a `screen-list` sub-surface or updates a sidecar `Card`.

## 4. Custom A2UI components we need (BYOC)

| Component | Purpose | Bound paths | Actions |
|---|---|---|---|
| `TargetingMap` | Mapbox + polygon draw + screen-include/exclude layer | `polygons`, `screens` | `polygon_drawn`, `screen_toggled` |
| `Heatmap` | Mapbox + H3 hex overlay + time slider | `cells`, `timeRange`, `selectedHex` | `hex_clicked`, `time_changed` |
| `DaypartGrid` | 7×24 toggle grid | `dayparts` | `daypart_toggled` |
| `PacingChart` | Time series, actual vs plan | `series`, `target` | `point_clicked` (drill) |
| `CampaignCard` | Compact summary used inline | (data props) | `open_detail`, `pause`, `resume` |
| `DiagnosisPanel` | Composite of findings + action chips | (data props) | `apply_suggestion` |

Everything else (Card, Text, Button, TextField, DateTimeInput, etc.) is in A2UI's built-in catalog — no work needed.

## 5. What this locks vs the original pre-PRD

| Decision | Was | Now |
|---|---|---|
| Chat host | Claude Desktop | Custom Next.js app + CopilotSidebar |
| UI protocol | MCP + mcp-ui | A2UI + AG-UI streaming |
| Workflow style | mcp-ui form-driven | A2UI form-driven (bidirectional path binding) |
| Backend stack | Open | Python + Pydantic AI + FastAPI + PostGIS |
| Frontend stack | Open | Next.js + React + CopilotKit + `@copilotkit/a2ui-renderer` |
| Chat session state | Open | Pydantic AI `StateDeps[DOOHState]` |
| Web admin | Separate tiny app | Plain Next.js routes in the same app |

## 6. Build effort calibration

| Slice | Effort | Notes |
|---|---|---|
| Chat shell wiring | < 1 day | `CopilotKitProvider` + `createA2UIMessageRenderer` is ~50 lines. |
| Adserver + Postgres/PostGIS schema | 1 weekend | FastAPI, no auction, deterministic eligibility. |
| Synthetic network + PoP sim | 1-2 days | Python generator + async load script. |
| Pacing rebalancer | 1-2 days | APScheduler or simple cron, hourly recompute. |
| Pydantic AI agent + tools | 1 weekend | Tool surface + StateDeps model + A2UI emission helpers. |
| Built-in A2UI forms (campaign create, micro-forms) | 1 weekend | A2UI form skeletons are concise. |
| `TargetingMap` component | 1-2 weekends | Mapbox + Mapbox Draw + screen layer + action wiring. |
| `Heatmap` component | 1-2 weekends | Mapbox + h3-js + deck.gl HexagonLayer + time slider + actions. |
| `DaypartGrid`, `PacingChart`, `CampaignCard`, `DiagnosisPanel` | 1 weekend total | Smaller, conventional React. |
| Web admin (upload, CSV, log viewer) | 1 weekend | Standard Next.js routes. |
| Polish + demo scenarios | 1-2 weekends | Scripts that drive the three hero journeys end-to-end. |

**Realistic estimate: 8-12 weekends end-to-end** for a polished demo of all three hero journeys.

## 7. Risks and unknowns

1. **A2UI v0.9 is pre-1.0.** Expect breaking changes; pin the version, monitor releases. The flatter v0.9 format shown in docs already moved away from v0.8's nested `userAction` structure — clearly evolving fast.
2. **Action payload size limits.** When `TargetingMap` emits `polygon_drawn` with a GeoJSON polygon, the action `context` carries it. Need to verify there's no soft size cap in the A2UI client SDK and that nested objects survive the path-resolution step.
3. **Multiple concurrent surfaces.** Dashboard + campaign-form + heatmap simultaneously is plausible (A2UI supports it via distinct `surfaceId`s) but the CopilotKit layout for "where each surface renders" needs design — sidebar vs main canvas vs modal.
4. **AG-UI event multiplexing.** Whether each tool call creates a new activity message vs streaming into an existing surface needs to be exercised on a small prototype before committing to a layout strategy.
5. **CopilotKit version pinning.** The renderer package (`@copilotkit/a2ui-renderer`) is younger than the core (`@copilotkit/react`); compatibility matrices may matter.
6. **Streaming heatmaps.** Live impression updates flowing into a rendered heatmap via `dataModelUpdate` deltas is conceptually clean but unproven at high update frequency; may need to throttle on the agent side.
7. **`@copilotkit/react` vs `@copilotkitnext/react`.** The docs reference both — need to confirm which is current and align all packages.

## 8. Recommendation

**Lock the architecture.** It satisfies the original thesis cleanly:
- Agent decides WHAT — Pydantic AI tools and A2UI emission.
- App decides HOW — custom React components honoring the Finch / DOOH design language.
- Chat is the primary surface, with web admin as a tiny escape valve in the same app.

The grill-me session should now sharpen:
- Concrete custom-component contracts (props, actions, bound paths).
- Surface composition rules (which surfaces are persistent vs ephemeral, where each renders).
- Tool granularity (one fat `diagnose_campaign` vs multiple narrow tools).
- A scrappy spike: ~2 days to wire CopilotKit + Pydantic AI hello-world with one built-in form, before locking the component plan.

## 9. Next steps

1. Spin up a thin spike: Next.js app + Pydantic AI agent + one A2UI form → just prove the loop.
2. Promote pre-PRD to v2 with this architecture locked.
3. Run v2 through grill-me to harden component contracts and surface composition.
4. Then break into issues via `to-issues`.
