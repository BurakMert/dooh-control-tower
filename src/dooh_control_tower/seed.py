"""Synthetic NYC DOOH dataset — screens, campaigns, creatives, targeting,
pop_events, pacing_buckets.

Run: ``uv run dooh-seed``

Idempotent: every seeder uses ON CONFLICT DO NOTHING against a natural or
external key. Re-running skips existing rows. To regenerate from scratch,
TRUNCATE the relevant tables first (no --reset flag yet).

Four seeders run in order:
  1. `seed_screens()`         — 100 screens around 12 NYC anchors (M1.2).
  2. `seed_campaigns()`       — 10 campaigns + creatives + targeting (M1.4).
  3. `seed_pop_events()`      — ~30 PoP impressions across 3 days (M1.5).
  4. `seed_pacing_buckets()`  — ~500 hourly slots, actuals from pop_events (M1.5).

pop_events depends on screens + campaigns + creatives + targeting. Pacing
buckets depend on pop_events (actuals are computed from them).

This is the dev-loop analogue of an ad-network CSV importer that would land
in this slot in production.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import random
from dataclasses import dataclass

from geoalchemy2 import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from dooh_control_tower.db import async_session_factory
from dooh_control_tower.models import (
    Campaign,
    Creative,
    PacingBucket,
    PopEvent,
    Screen,
    Targeting,
)

# Fixed seed → reproducible network. Same seed every M1.x run, every test.
SEED = 42
N_SCREENS = 100

# ~500m radius at NYC's latitude (0.005° ≈ 400-550m).
JITTER_DEG = 0.005


@dataclass(frozen=True)
class Anchor:
    market: str
    name: str
    lon: float  # WKT uses POINT(lon lat) — longitude first. Famous PostGIS footgun.
    lat: float


ANCHORS: tuple[Anchor, ...] = (
    # Manhattan (~60% of network)
    Anchor("Manhattan", "Times Square",     -73.9855, 40.7580),
    Anchor("Manhattan", "Penn Station",     -73.9935, 40.7506),
    Anchor("Manhattan", "Grand Central",    -73.9772, 40.7527),
    Anchor("Manhattan", "Union Square",     -73.9911, 40.7359),
    Anchor("Manhattan", "Columbus Circle",  -73.9817, 40.7681),
    Anchor("Manhattan", "Wall Street",      -74.0086, 40.7068),
    Anchor("Manhattan", "Herald Square",    -73.9876, 40.7505),
    # Brooklyn (~25%)
    Anchor("Brooklyn",  "Cadman Plaza",     -73.9969, 40.7061),
    Anchor("Brooklyn",  "DUMBO",            -73.9878, 40.7033),
    Anchor("Brooklyn",  "Williamsburg",     -73.9573, 40.7081),
    # Queens (~15%)
    Anchor("Queens",    "Long Island City", -73.9426, 40.7440),
    Anchor("Queens",    "Flushing",         -73.8326, 40.7596),
)

MARKET_SHARE = {"Manhattan": 0.60, "Brooklyn": 0.25, "Queens": 0.15}

SCREEN_TYPES = ("billboard", "street_furniture", "transit", "mall")
SCREEN_TYPE_WEIGHTS = (0.40, 0.30, 0.20, 0.10)

# Common DOOH formats: HD billboard, 4K, vertical street furniture, mall kiosk.
RESOLUTIONS: tuple[tuple[int, int], ...] = (
    (1920, 1080),
    (3840, 2160),
    (1080, 1920),
    (1366, 768),
)


def generate_screens(n: int = N_SCREENS, seed: int = SEED) -> list[dict]:
    """Generate `n` plausible screen rows deterministically from `seed`."""
    rng = random.Random(seed)

    # Each anchor's weight = (its market's share) ÷ (anchors in that market).
    # This balances the per-anchor probabilities so the per-market totals
    # converge to MARKET_SHARE over a large enough N.
    market_anchor_counts = {
        m: sum(1 for a in ANCHORS if a.market == m) for m in MARKET_SHARE
    }
    anchor_weights = [
        MARKET_SHARE[a.market] / market_anchor_counts[a.market] for a in ANCHORS
    ]

    rows: list[dict] = []
    for i in range(1, n + 1):
        anchor = rng.choices(ANCHORS, weights=anchor_weights, k=1)[0]
        lon = anchor.lon + rng.uniform(-JITTER_DEG, JITTER_DEG)
        lat = anchor.lat + rng.uniform(-JITTER_DEG, JITTER_DEG)
        screen_type = rng.choices(SCREEN_TYPES, weights=SCREEN_TYPE_WEIGHTS, k=1)[0]
        width, height = rng.choice(RESOLUTIONS)
        rows.append(
            {
                "external_id": f"screen_{i:03d}",
                "name": f"{anchor.name} Screen #{i:03d}",
                "geom": WKTElement(f"POINT({lon} {lat})", srid=4326),
                "screen_type": screen_type,
                "resolution_width": width,
                "resolution_height": height,
                "market": anchor.market,
                "is_active": True,
            }
        )
    return rows


async def seed_screens() -> dict[str, int]:
    """Insert the generated network. Idempotent. Returns market tally."""
    rows = generate_screens()
    async with async_session_factory() as session:
        stmt = pg_insert(Screen).on_conflict_do_nothing(
            index_elements=["external_id"]
        )
        await session.execute(stmt, rows)
        await session.commit()
    tally: dict[str, int] = {m: 0 for m in MARKET_SHARE}
    for r in rows:
        tally[r["market"]] += 1
    return tally


# ---------------------------------------------------------------------------
# M1.4 — campaigns, creatives, targeting
# ---------------------------------------------------------------------------

N_CAMPAIGNS = 10

# Targeting bbox padding (~500m at NYC's latitude). Wraps every campaign's
# sampled screens with a small buffer so screens near the bbox edge stay
# inside the polygon under ST_Contains.
BBOX_BUFFER_DEG = 0.005

# Recognizable brand fixtures — purely for screenshot/demo presence. Not
# affiliated; trademarks belong to their owners.
ADVERTISERS: tuple[str, ...] = (
    "Spotify",
    "Coca-Cola",
    "Nike",
    "MetLife",
    "Equinox",
    "Sweetgreen",
    "Peloton",
    "Warby Parker",
    "Casper",
    "Glossier",
)

# Hand-picked state distribution. 7 active + 1 draft + 1 paused + 1 completed.
# Order matches campaign index so re-runs are stable.
CAMPAIGN_STATES: tuple[str, ...] = (
    "active",
    "active",
    "active",
    "draft",
    "active",
    "paused",
    "active",
    "active",
    "completed",
    "active",
)
assert len(CAMPAIGN_STATES) == N_CAMPAIGNS

PACING_STRATEGIES = ("even", "asap")

CREATIVE_TYPES = ("image", "video")
CREATIVE_TYPE_WEIGHTS = (0.65, 0.35)

# Standard DOOH creative formats — same set as screen resolutions so the
# eligibility filter in M3 can match creative dims to screen dims if needed.
CREATIVE_FORMATS: tuple[tuple[int, int, str], ...] = (
    (1920, 1080, "16:9 HD"),
    (3840, 2160, "16:9 4K"),
    (1080, 1920, "9:16 portrait"),
    (1366, 768, "16:9 SD"),
)


def _bbox_multipolygon_wkt(lons: list[float], lats: list[float]) -> str:
    """Buffer-padded bounding box around (lon, lat) points → MULTIPOLYGON WKT.

    Single-polygon multipolygon: PostGIS-side ST_Contains works the same on
    MULTIPOLYGON((...)) as POLYGON((...)) so we keep the column type general
    (M5.4 polygon paste-in may produce true multi-polygons).
    """
    lon_min = min(lons) - BBOX_BUFFER_DEG
    lon_max = max(lons) + BBOX_BUFFER_DEG
    lat_min = min(lats) - BBOX_BUFFER_DEG
    lat_max = max(lats) + BBOX_BUFFER_DEG
    # CCW exterior ring (mathematical convention; PostGIS doesn't enforce
    # orientation for ST_Contains, but staying consistent helps debugging).
    return (
        f"MULTIPOLYGON((("
        f"{lon_min} {lat_min}, "
        f"{lon_max} {lat_min}, "
        f"{lon_max} {lat_max}, "
        f"{lon_min} {lat_max}, "
        f"{lon_min} {lat_min}"
        f")))"
    )


async def _fetch_screen_summary() -> list[dict]:
    """Pull (id, market, lon, lat) for every screen — campaign seeder uses
    these to sample subsets per primary market and bbox-bound them."""
    async with async_session_factory() as session:
        stmt = select(
            Screen.id,
            Screen.market,
            func.ST_X(Screen.geom).label("lon"),
            func.ST_Y(Screen.geom).label("lat"),
        ).order_by(Screen.external_id)
        result = await session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]


def _generate_campaign_rows(
    screens: list[dict],
    n: int = N_CAMPAIGNS,
    seed: int = SEED,
    today: dt.date | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Pure: given screens, produce campaigns + creatives + targeting rows.

    `today` defaults to `date.today()` at call time so flight windows stay
    current-feeling across re-runs. Already-seeded campaigns keep their
    original dates via ON CONFLICT DO NOTHING; only fresh inserts (new
    `external_id`s) pick up today's anchor.

    Creatives + targeting rows carry a placeholder `_campaign_external_id`
    field — the async seeder resolves it to a real `campaign_id` UUID after
    the campaigns are committed.
    """
    if today is None:
        today = dt.date.today()

    # Offset from the screen RNG so the two streams don't share state — bumping
    # N_SCREENS later won't reshuffle the campaign outputs.
    rng = random.Random(seed + 1000)

    screens_by_market: dict[str, list[dict]] = {}
    for s in screens:
        screens_by_market.setdefault(s["market"], []).append(s)

    campaigns: list[dict] = []
    creatives: list[dict] = []
    targetings: list[dict] = []

    for i in range(n):
        external_id = f"campaign_{i:03d}"
        advertiser = ADVERTISERS[i % len(ADVERTISERS)]
        primary_market = rng.choices(
            list(MARKET_SHARE.keys()),
            weights=list(MARKET_SHARE.values()),
            k=1,
        )[0]
        local = screens_by_market[primary_market]
        k = rng.randint(3, min(8, len(local)))
        sampled = rng.sample(local, k=k)

        state = CAMPAIGN_STATES[i]
        # Anchor flight window relative to `today` so demos always look current.
        if state == "completed":
            start = today - dt.timedelta(days=60)
            end = today - dt.timedelta(days=7)
        elif state == "draft":
            start = today + dt.timedelta(days=14)
            end = today + dt.timedelta(days=60)
        elif state == "paused":
            start = today - dt.timedelta(days=14)
            end = today + dt.timedelta(days=30)
        else:  # active
            start = today - dt.timedelta(days=rng.randint(1, 30))
            end = today + dt.timedelta(days=rng.randint(7, 60))

        # Daily budgets in cents: $100 / $250 / $500 / $1000 / $2500.
        daily_budget_cents = rng.choice([10_000, 25_000, 50_000, 100_000, 250_000])
        pacing = rng.choices(PACING_STRATEGIES, weights=(0.7, 0.3), k=1)[0]
        # Daypart end is exclusive — 0-24 = 24h, 6-22 = "daytime", 8-23 = biz+.
        daypart_start = rng.choice([0, 6, 7, 8])
        daypart_end = rng.choice([22, 23, 24])

        campaigns.append(
            {
                "external_id": external_id,
                "name": f"{advertiser} – {primary_market} #{i:03d}",
                "advertiser": advertiser,
                "state": state,
                "start_date": start,
                "end_date": end,
                "daily_budget_cents": daily_budget_cents,
                "pacing_strategy": pacing,
            }
        )

        lons = [s["lon"] for s in sampled]
        lats = [s["lat"] for s in sampled]
        targetings.append(
            {
                "_campaign_external_id": external_id,
                "geom": WKTElement(_bbox_multipolygon_wkt(lons, lats), srid=4326),
                "daypart_start_hour": daypart_start,
                "daypart_end_hour": daypart_end,
            }
        )

        n_creatives = rng.randint(1, 3)
        for j in range(n_creatives):
            width, height, fmt_label = rng.choice(CREATIVE_FORMATS)
            ctype = rng.choices(CREATIVE_TYPES, weights=CREATIVE_TYPE_WEIGHTS, k=1)[0]
            duration = 15 if ctype == "image" else rng.choice([15, 20, 30])
            ext = f"{external_id}_creative_{j:02d}"
            creatives.append(
                {
                    "_campaign_external_id": external_id,
                    "external_id": ext,
                    "name": f"{advertiser} {ctype} — {fmt_label}",
                    "creative_type": ctype,
                    "duration_seconds": duration,
                    "width": width,
                    "height": height,
                    "asset_url": (
                        f"https://placeholder.dooh.dev/{ext}."
                        f"{'mp4' if ctype == 'video' else 'jpg'}"
                    ),
                }
            )

    return campaigns, creatives, targetings


def _attach_campaign_fk(rows: list[dict], id_by_external: dict) -> list[dict]:
    """Replace the placeholder `_campaign_external_id` on each row with the
    real `campaign_id` UUID."""
    out = []
    for row in rows:
        ext = row.pop("_campaign_external_id")
        row["campaign_id"] = id_by_external[ext]
        out.append(row)
    return out


async def seed_campaigns() -> dict[str, int]:
    """Insert synthetic campaigns + creatives + targeting. Idempotent.

    Depends on `seed_screens()` running first — campaigns reference screen
    geometries to compute their targeting bboxes.
    """
    screens = await _fetch_screen_summary()
    if not screens:
        raise RuntimeError(
            "No screens in DB — run `seed_screens()` (or `dooh-seed`) before "
            "seeding campaigns."
        )

    campaigns, creatives, targetings = _generate_campaign_rows(screens)

    async with async_session_factory() as session:
        await session.execute(
            pg_insert(Campaign).on_conflict_do_nothing(index_elements=["external_id"]),
            campaigns,
        )

        # Resolve campaign external_id → id for child FK wiring. Pulls back
        # both freshly-inserted and pre-existing campaigns.
        ext_ids = [c["external_id"] for c in campaigns]
        result = await session.execute(
            select(Campaign.id, Campaign.external_id).where(
                Campaign.external_id.in_(ext_ids)
            )
        )
        id_by_external = {row.external_id: row.id for row in result.all()}

        creative_rows = _attach_campaign_fk(creatives, id_by_external)
        targeting_rows = _attach_campaign_fk(targetings, id_by_external)

        if creative_rows:
            await session.execute(
                pg_insert(Creative).on_conflict_do_nothing(
                    index_elements=["external_id"]
                ),
                creative_rows,
            )
        if targeting_rows:
            await session.execute(
                pg_insert(Targeting).on_conflict_do_nothing(
                    index_elements=["campaign_id"]
                ),
                targeting_rows,
            )
        await session.commit()

    return {
        "campaigns": len(campaigns),
        "creatives": len(creatives),
        "targetings": len(targetings),
    }


# ---------------------------------------------------------------------------
# M1.5 — pop_event partition helper + seeders
# ---------------------------------------------------------------------------

N_POP_EVENTS = 30
POP_EVENT_DAYS_BACK = 3

# Placeholder "cents per impression" so we can convert daily_budget_cents
# → target impressions. M6.1 (pacing rebalancer) owns the real formula.
# Real DOOH CPM is $5-20/mille; 1¢/imp = $10 CPM, a plausible midpoint.
CPM_CENTS_PER_IMPRESSION = 1


async def ensure_pop_event_partition(session, day: dt.date) -> None:
    """Idempotently create a daily child partition for `day`.

    Postgres requires the partition range bounds to be literal SQL — we can't
    parameterize them. The dates come from a trusted internal source (a
    Python `date`), so f-string interpolation is safe here.

    M3.4 sync writes and the M3.5 bulk simulator both call this before
    inserting rows for a given date. Calling for an existing partition is
    a no-op thanks to `IF NOT EXISTS`.
    """
    next_day = day + dt.timedelta(days=1)
    partition_name = f"pop_event_{day:%Y_%m_%d}"
    await session.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {partition_name} "
            f"PARTITION OF pop_event "
            f"FOR VALUES FROM ('{day.isoformat()}') TO ('{next_day.isoformat()}')"
        )
    )


async def _eligible_screens_for(
    session, campaign_id, targeting_id
) -> list[dict]:
    """Screens inside this campaign's targeting polygon — same query M3.3
    will use at ad-request time."""
    stmt = (
        select(Screen.id, Screen.market)
        .join(Targeting, func.ST_Contains(Targeting.geom, Screen.geom))
        .where(Targeting.id == targeting_id)
    )
    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result.all()]


async def seed_pop_events() -> dict[str, int]:
    """Insert ~30 synthetic PoP impressions across last 3 days for active
    campaigns. Idempotent via natural-PK ON CONFLICT DO NOTHING."""
    rng = random.Random(SEED + 2000)
    today = dt.date.today()

    # Two-query flow: (1) active campaigns + targeting, (2) per campaign,
    # fetch creatives + eligible screens. Avoids a Cartesian join across
    # creatives × screens.
    async with async_session_factory() as session:
        cstmt = select(
            Campaign.id,
            Campaign.external_id,
            Targeting.id.label("targeting_id"),
            Targeting.daypart_start_hour,
            Targeting.daypart_end_hour,
        ).join(Targeting, Targeting.campaign_id == Campaign.id).where(
            Campaign.state == "active"
        )
        active = [dict(r._mapping) for r in (await session.execute(cstmt)).all()]

        # Pre-fetch creatives per campaign + eligible screens per campaign.
        per_campaign: dict = {}
        for c in active:
            creatives = (
                await session.execute(
                    select(Creative.id, Creative.duration_seconds).where(
                        Creative.campaign_id == c["id"]
                    )
                )
            ).all()
            screens = await _eligible_screens_for(
                session, c["id"], c["targeting_id"]
            )
            per_campaign[c["id"]] = {
                "creatives": [dict(row._mapping) for row in creatives],
                "screens": screens,
                "daypart_start": c["daypart_start_hour"],
                "daypart_end": c["daypart_end_hour"],
            }

        # Build event rows.
        active_ids = list(per_campaign.keys())
        if not active_ids:
            return {"events": 0, "partitions": 0}

        rows: list[dict] = []
        partition_days: set[dt.date] = set()
        for _ in range(N_POP_EVENTS):
            cid = rng.choice(active_ids)
            ctx = per_campaign[cid]
            if not ctx["creatives"] or not ctx["screens"]:
                continue
            creative = rng.choice(ctx["creatives"])
            screen = rng.choice(ctx["screens"])

            days_ago = rng.randint(0, POP_EVENT_DAYS_BACK - 1)
            day = today - dt.timedelta(days=days_ago)
            # Clamp the hour into the campaign's daypart (end is exclusive).
            start_h = ctx["daypart_start"]
            end_h = max(start_h + 1, ctx["daypart_end"])
            hour = rng.randint(start_h, end_h - 1)
            minute = rng.randint(0, 59)
            second = rng.randint(0, 59)
            event_ts = dt.datetime(
                day.year, day.month, day.day,
                hour, minute, second,
                tzinfo=dt.timezone.utc,
            )
            partition_days.add(day)
            rows.append(
                {
                    "event_ts": event_ts,
                    "event_date": day,
                    "campaign_id": cid,
                    "creative_id": creative["id"],
                    "screen_id": screen["id"],
                    "duration_seconds": creative["duration_seconds"],
                }
            )

        # Ensure a daily partition exists for every distinct event date BEFORE
        # we insert — otherwise rows land in pop_event_default (still valid,
        # but leaks the dev-safety-net contract from ADR-0001).
        for day in sorted(partition_days):
            await ensure_pop_event_partition(session, day)

        if rows:
            await session.execute(
                pg_insert(PopEvent).on_conflict_do_nothing(),
                rows,
            )
        await session.commit()

    return {"events": len(rows), "partitions": len(partition_days)}


async def seed_pacing_buckets() -> dict[str, int]:
    """Insert pacing target rows for active campaigns × last 3 days × 24 hours.
    Computes `actual` from the just-seeded pop_events. Idempotent via PK."""
    today = dt.date.today()

    async with async_session_factory() as session:
        active = (
            await session.execute(
                select(Campaign.id, Campaign.daily_budget_cents).where(
                    Campaign.state == "active"
                )
            )
        ).all()

        # Aggregate pop_events into (campaign_id, hour_ts) counts, for our
        # window. The DATE_TRUNC matches M6.1's intended pacing read pattern.
        hour_floor = today - dt.timedelta(days=POP_EVENT_DAYS_BACK)
        actuals_result = await session.execute(
            select(
                PopEvent.campaign_id,
                func.date_trunc("hour", PopEvent.event_ts).label("hour_ts"),
                func.count().label("actual"),
            )
            .where(PopEvent.event_date >= hour_floor)
            .group_by(PopEvent.campaign_id, "hour_ts")
        )
        actual_by_key: dict[tuple, int] = {
            (row.campaign_id, row.hour_ts): row.actual
            for row in actuals_result.all()
        }

        rows: list[dict] = []
        for c in active:
            # target_per_hour = daily_budget / 24 / CPM (cents → impressions).
            # Placeholder formula — M6.1 owns the real one (daypart-aware,
            # priority-weighted, multi-day smoothed).
            target_per_hour = max(
                1, c.daily_budget_cents // (24 * CPM_CENTS_PER_IMPRESSION)
            )
            for days_ago in range(POP_EVENT_DAYS_BACK):
                day = today - dt.timedelta(days=days_ago)
                for hour in range(24):
                    hour_ts = dt.datetime(
                        day.year, day.month, day.day, hour,
                        tzinfo=dt.timezone.utc,
                    )
                    rows.append(
                        {
                            "campaign_id": c.id,
                            "hour_ts": hour_ts,
                            "target": target_per_hour,
                            "actual": actual_by_key.get((c.id, hour_ts), 0),
                        }
                    )

        if rows:
            await session.execute(
                pg_insert(PacingBucket).on_conflict_do_nothing(),
                rows,
            )
        await session.commit()

    nonzero_actuals = sum(1 for v in actual_by_key.values() if v > 0)
    return {"buckets": len(rows), "with_actuals": nonzero_actuals}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def _seed_all() -> tuple[dict, dict, dict, dict]:
    screen_tally = await seed_screens()
    campaign_tally = await seed_campaigns()
    pop_tally = await seed_pop_events()
    pacing_tally = await seed_pacing_buckets()
    return screen_tally, campaign_tally, pop_tally, pacing_tally


def main() -> None:
    screen_tally, campaign_tally, pop_tally, pacing_tally = asyncio.run(
        _seed_all()
    )

    total_screens = sum(screen_tally.values())
    print(f"Seeded synthetic network: {total_screens} screens.")
    for market, n in sorted(screen_tally.items(), key=lambda kv: -kv[1]):
        print(f"  {market:10s} {n:3d}")

    print()
    print(
        f"Seeded synthetic campaigns: {campaign_tally['campaigns']} campaigns, "
        f"{campaign_tally['creatives']} creatives, "
        f"{campaign_tally['targetings']} targeting rows."
    )

    print()
    print(
        f"Seeded PoP events: {pop_tally['events']} impressions "
        f"across {pop_tally['partitions']} daily partitions."
    )

    print()
    print(
        f"Seeded pacing buckets: {pacing_tally['buckets']} hourly slots "
        f"({pacing_tally['with_actuals']} with non-zero actuals)."
    )


if __name__ == "__main__":
    main()
