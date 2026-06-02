# DOOH Control Tower

A chat-driven operational tool for Digital Out-of-Home (DOOH) advertising — campaigns flying on a synthetic NYC screen network, with an agent that can plan, diagnose, and act through MCP tools and generative UI.

## Language

**Screen**:
A physical DOOH placement — billboard, transit panel, street furniture, mall kiosk. Has a fixed location (`geom`) and a `market` (Manhattan / Brooklyn / Queens).
_Avoid_: Display, panel, slot.

**Campaign**:
An advertiser's buy — flight window, daily budget, pacing strategy, one targeting spec, one or more creatives.
_Avoid_: Order, deal, line item.

**Creative**:
A single ad asset (image or video) belonging to one campaign. Has format dimensions and a play duration.
_Avoid_: Asset, ad, banner.

**Targeting (polygon)**:
The MULTIPOLYGON within which a campaign is eligible to serve, plus its daypart window. Evaluated via `ST_Contains` against the screen's point at ad-request time.
_Avoid_: Geofence, coverage area, region.

**Proof of Play (PoP)**:
One event per actual creative render on one screen at one instant. 1:1:1 with impression. Industry-standard DOOH primitive — the durable receipt that an ad actually played.
_Avoid_: Playback log, render event, ad event.

**Impression**:
A single playback of a creative on a screen. Counted once per render. Synonymous with PoP in our model.
_Avoid_: View, exposure (those are audience-measurement terms we don't model).

**Pacing bucket**:
One-hour aggregation slot for one campaign — planned `target` impressions vs running `actual` count. Drives the M6 rebalancer's "are we on track" loop.
_Avoid_: Pacing window, hour slot, bucket.

**H3 cell (r8 / r9)**:
Uber H3 hierarchical hexagon. r8 ≈ 150m edge (screen-cluster resolution); r9 ≈ 55m edge (single-screen resolution). Stored denormalized on `pop_event` so impressions keep their point-in-time location even if a screen later moves.
_Avoid_: Hex, tile, grid cell.

**Daypart**:
The hour-of-day window when a campaign is eligible to serve. Stored as `[start_hour, end_hour)` integers; end is exclusive.
_Avoid_: Schedule, time window, runtime.

**Eligibility**:
The decision "may this campaign serve on this screen at this moment?" — composed of state (active), flight window (today between start/end), daypart (current hour in window), and targeting (screen point inside polygon).
_Avoid_: Match, qualification, fit.
