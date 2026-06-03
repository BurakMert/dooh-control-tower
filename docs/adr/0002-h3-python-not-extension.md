# H3 computation in Python, not in the database

**Context.** M1.6 needs to populate `pop_event.h3_r8` / `h3_r9` with Uber H3 cell IDs. Two paths existed: the Python `h3` 4.x library (compute Python-side, write via SQL INSERT/UPDATE) or the `h3-pg` Postgres extension (compute via SQL functions like `h3_latlng_to_cell()`). The Postgres extension is NOT bundled with the `postgis/postgis:17-3.5` image we run — adopting it would require a custom-built image (cmake source build from upstream `zachasme/h3-pg`).

**Decision.** Use Python `h3` 4.x. Compute h3 cells at every write site (seed at seed time; M3.4 sync ad-server inserts at impression time; M3.5 simulator at bulk-insert time). The DB stores the BIGINT cell values; it does not compute them.

The principle this defends: **the database stays a database.** Indexes, declarative constraints, partitioning, and pure value-type extensions (PostGIS for geometry types) are appropriate DB-side concerns. Compute, derived values, business transformations live in application code. h3-pg would put a transformation engine inside Postgres for a payoff (SQL-native h3 queries) we don't need yet — the schema only requires the *result* of the computation as a stored value.

**Two adjacent decisions made in the same spirit:**

1. **No h3 columns on `screen`.** Screens already have `geom` (point, SRID 4326) as the source of truth. Caching `screen.h3_r8` would denormalize derivable data for a microsecond-scale write-path optimization that doesn't matter at our scale. Each pop_event INSERT computes h3 fresh from the loaded screen's coordinates — cost is ~µs per row, ~6 seconds total over a 60-day full-load simulation.

2. **No new Postgres btree indexes on `(h3_r8, event_date)` or similar in M1.6.** The chunk title "H3 indexing job" refers to *computing H3 cell indices*, not adding Postgres btree indexes. Adding a btree index speculatively risks the wrong leading column — the M4 heatmap shape isn't built yet, and at ~10K-distinct-cardinality h3_r8 values the planner will likely pick HashAggregate regardless. M4.1 will EXPLAIN the actual query and add the right index after measurement.

**Consequences worth flagging:**

- M3.4 sync write path: one `h3.latlng_to_cell()` call per impression. Trivial overhead; isolated to one Python call site.
- The h3-pg escape hatch remains open. The columns are already BIGINT, and h3-pg's `h3index` type casts to/from bigint. If M5/M6 ever needs server-side h3 operations (grid_disk for neighbors, polygon_to_cells for geo-targeting subdivision), we can adopt h3-pg incrementally — no data migration needed.
- `screen.geom` stays the single source of truth for screen location. Future "screen relocated" flows update one column; pop_event keeps its frozen historical h3 per ADR-0001.

**Rejected alternatives:**

- *h3-pg extension via custom Dockerfile.* Buys SQL-native h3 functions (`h3_latlng_to_cell`, `h3_cell_to_boundary_geometry`, etc.) at the cost of a custom-built Postgres image and ongoing version-tracking discipline. Worth it only when we need server-side h3 operations that the application can't cleanly express.
- *Add `h3_r8` / `h3_r9` to `screen` as cached columns.* Cleaner write-path attribute copy; introduces drift surface area (column derived from `geom` but stored separately). Recoverable later — `ALTER TABLE screen ADD COLUMN` is cheap on a 100-row table.
- *Add `(h3_r8, event_date)` btree index in M1.6.* Speculative; the actual M4 heatmap query shape isn't built. HashAggregate likely wins regardless at expected cardinality. Add it in M4.1 after EXPLAIN measurement.
- *Generated column or trigger to auto-populate h3 on INSERT.* Embeds business logic in the data layer — explicitly the pattern this ADR rejects.
