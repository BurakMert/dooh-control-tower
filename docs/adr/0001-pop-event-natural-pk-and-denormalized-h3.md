# pop_event: natural PK, denormalized h3, partitioned by day

**Context.** `pop_event` is the Proof-of-Play impression store — one row per creative render on one screen at one instant. At full portfolio load it's ~35M rows over 60 days; in real DOOH deployments it dominates write volume.

**Decision.** Three coupled choices, locked together in M1.5:

1. **Natural composite PK on `(event_ts, screen_id, creative_id, event_date)`** instead of a surrogate UUID. The four-column tuple already uniquely identifies an impression — adding a UUID would manufacture identity where the data has it. ON CONFLICT DO NOTHING on the natural PK gives free retry-idempotency for the M3.4 sync write path; the M3.5 simulator's bulk insert dedupes for the same reason. `event_date` is in the PK because Postgres requires the partition key in any UNIQUE/PK on a partitioned table.

2. **`h3_r8` and `h3_r9` denormalized onto `pop_event`** (also on `screen` per [[Screen]] glossary), not JOINed from `screen` at heatmap-query time. Two reasons: (a) **point-in-time correctness** — an impression's true location is where the screen was *when it played*; if a kiosk relocates later, historical pop_events must keep their original H3 cell, and JOINing to the current screen row would silently rewrite history. (b) The M4 heatmap hot path is `SELECT h3_r8, count(*) FROM pop_event WHERE event_date BETWEEN ... GROUP BY h3_r8` — denormalization keeps it JOIN-free at 35M-row scale.

3. **Daily `PARTITION BY RANGE (event_date)`**. Pre-PRD's documented intent. DOOH retention is conventionally 30/60/90 days; `DETACH PARTITION` per day is O(1) and the standard retention cadence. 60 child partitions is negligible catalog overhead at PG17. Hourly partitioning would explode catalog cost (1,440 children) without serving any hot-path query — hour resolution lives in the row's `event_ts`, not in the partition layer.

**Consequences worth flagging:**

- Schema change to the PK becomes painful once partitions hold real data. Recovering surrogate-UUID identity would require a full table rebuild. Accepted.
- Denormalized `h3_r8/r9` cost ~16 bytes/row × 35M = ~560 MB cumulative. Negligible.
- `pop_event_default` partition exists as a dev safety net but blocks attaching overlapping child partitions if events leak there. Production hardening (M7) would either DETACH it or alarm on any row landing there.
- M3.4 sync writes must call `ensure_pop_event_partition(date)` before insert (or accept rows landing in `_default`). The contract is one extra Python call per write batch; M3.5 simulator and M1.5 seed both observe it.

**Rejected alternatives:**

- *Surrogate UUID PK + UNIQUE on the natural key.* Two indexes per partition for no read benefit anything in the roadmap actually needs.
- *No PK / covering indexes only* (ClickHouse-style). Loses retry idempotency; SQLA ORM mapping needs *something* to be PK; small wins don't justify the discipline cost.
- *`h3` on `screen` only, JOIN at query time.* Cleaner schema, but breaks point-in-time correctness for relocated screens and adds a JOIN to the hottest read path.
- *Hourly or monthly partitioning.* Hourly explodes catalog with no read win; monthly loses the per-day retention cadence DOOH operations expect.
