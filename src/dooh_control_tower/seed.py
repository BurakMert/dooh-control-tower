"""Synthetic NYC DOOH network — 100 screens clustered around 12 real-world anchors.

Run: ``uv run dooh-seed``

Idempotent: keyed on external_id (screen_001..screen_100). Re-running skips
existing rows via ON CONFLICT DO NOTHING. To regenerate from scratch, TRUNCATE
the screen table first (no --reset flag yet; not needed until M1.3+).

This is the dev-loop analogue of an ad-network CSV importer that would land
in this slot in production. The anchors and weights are hand-curated for
visual plausibility on a map — real DOOH networks under-index Staten Island
and the Bronx, which is why this generator skips them.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

from geoalchemy2 import WKTElement
from sqlalchemy.dialects.postgresql import insert as pg_insert

from dooh_control_tower.db import async_session_factory
from dooh_control_tower.models import Screen

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


def main() -> None:
    tally = asyncio.run(seed_screens())
    total = sum(tally.values())
    print(f"Seeded synthetic network: {total} screens.")
    for market, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {market:10s} {n:3d}")


if __name__ == "__main__":
    main()
