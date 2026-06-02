"""show_screen_map — first mcp-ui surface (MCP Apps pattern).

Two-part wiring per the MCP Apps standard (SEP-1724):
  1. A Resource registered at ui://dooh-control-tower/screen-map serves the
     HTML. Hosts that follow the standard (Claude Desktop, VSCode, Goose,
     Postman, etc.) fetch it via `resources/read`.
  2. The `show_screen_map` tool carries `_meta.ui.resourceUri` pointing at
     that resource. Claude Desktop reads this and knows the tool has a UI.

The tool ALSO returns the resource inline in `content[]` (dual-pattern
fallback) so older mcp-ui-only clients still render.

HTML is self-contained: Leaflet via CDN, CARTO Voyager Light tiles, screens
embedded as a JSON island in a <script type="application/json"> tag, color
encoding by market. A `ui-lifecycle-iframe-ready` postMessage tells the host
the surface is mounted (per MCP Apps lifecycle).
"""

import json

from mcp.types import TextContent
from sqlalchemy import func, select

from dooh_control_tower.db import async_session_factory
from dooh_control_tower.mcp.server import mcp
from dooh_control_tower.mcp.tools.screens import ScreenSummary
from dooh_control_tower.models import Screen

SCREEN_MAP_URI = "ui://dooh-control-tower/screen-map"

# Claude Desktop (and other MCP Apps hosts) only render resources whose MIME
# carries the `;profile=mcp-app` parameter — that's the signal "this is a UI
# surface, not a normal text/html attachment." The Python mcp-ui-server SDK
# (5.2.0) ships plain `text/html`, which renders nowhere. We override.
MCP_APP_HTML_MIME = "text/html;profile=mcp-app"

MARKET_COLORS = {
    "Manhattan": "#4f46e5",  # indigo-600
    "Brooklyn": "#10b981",   # emerald-500
    "Queens": "#f59e0b",     # amber-500
}

TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
TILE_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
)

LEAFLET_VERSION = "1.9.4"


async def _fetch_screen_summaries() -> list[ScreenSummary]:
    """Query the screen table for the map. Mirrors `list_screens` for M1.3 but
    kept separate so M2.3's filter parameters don't accidentally constrain
    the map projection."""
    async with async_session_factory() as session:
        stmt = select(
            Screen.id,
            Screen.external_id,
            Screen.name,
            func.ST_Y(Screen.geom).label("lat"),
            func.ST_X(Screen.geom).label("lon"),
            Screen.screen_type,
            Screen.market,
        ).order_by(Screen.external_id)
        result = await session.execute(stmt)
        return [ScreenSummary(**row._mapping) for row in result.all()]


def _build_html(screens_json: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DOOH Control Tower — Screen Network</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/leaflet.js"></script>
<style>
  /* Use 100vh (viewport-relative) instead of 100% so we don't depend on
     the iframe parent having an explicit height. Belt-and-suspenders with
     min-height in case the host gives us a tiny iframe. */
  html, body {{
    margin: 0;
    padding: 0;
    height: 100vh;
    min-height: 560px;
    width: 100%;
    background: #f8fafc;
  }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }}
  #map {{ height: 100vh; min-height: 560px; width: 100%; }}
  .leaflet-popup-content {{ font-size: 13px; line-height: 1.45; margin: 10px 12px; }}
  .popup-name {{ font-weight: 600; margin-bottom: 4px; color: #0f172a; }}
  .popup-meta {{ color: #64748b; }}
  .legend {{
    background: white;
    padding: 8px 12px;
    border-radius: 6px;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.15);
    font-size: 12px;
    line-height: 1.6;
    color: #334155;
  }}
  .legend-title {{ font-weight: 600; margin-bottom: 4px; color: #0f172a; }}
  .legend-row {{ display: flex; align-items: center; gap: 8px; }}
  .legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.15);
  }}
</style>
</head>
<body>
<div id="map"></div>
<script type="application/json" id="screens-data">{screens_json}</script>
<script>
  const COLORS = {json.dumps(MARKET_COLORS)};
  const screens = JSON.parse(document.getElementById('screens-data').textContent);

  const map = L.map('map', {{ zoomControl: true, scrollWheelZoom: true }});
  L.tileLayer({json.dumps(TILE_URL)}, {{
    attribution: {json.dumps(TILE_ATTR)},
    maxZoom: 19,
  }}).addTo(map);

  const markers = screens.map(s => {{
    const color = COLORS[s.market] || '#64748b';
    return L.circleMarker([s.lat, s.lon], {{
      radius: 6,
      fillColor: color,
      color: 'white',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.92,
    }}).bindPopup(
      '<div class="popup-name">' + s.name + '</div>' +
      '<div class="popup-meta">' + s.market + ' · ' + s.screen_type + '</div>' +
      '<div class="popup-meta">' + s.external_id + '</div>'
    );
  }});

  const group = L.featureGroup(markers).addTo(map);
  map.fitBounds(group.getBounds(), {{ padding: [24, 24] }});

  // Leaflet caches container dimensions at init. If the iframe size was
  // still settling when init ran, the tile layer can be misaligned or
  // invisible. Recompute after the next animation frame, and again after
  // resize events (host may resize the iframe based on preferred-frame-size).
  requestAnimationFrame(() => map.invalidateSize());
  setTimeout(() => map.invalidateSize(), 200);
  window.addEventListener('resize', () => map.invalidateSize());

  const legend = L.control({{ position: 'bottomright' }});
  legend.onAdd = function() {{
    const div = L.DomUtil.create('div', 'legend');
    div.innerHTML =
      '<div class="legend-title">Market</div>' +
      Object.entries(COLORS).map(([market, color]) =>
        '<div class="legend-row">' +
          '<span class="legend-dot" style="background:' + color + '"></span>' +
          market +
        '</div>'
      ).join('');
    return div;
  }};
  legend.addTo(map);

  // MCP Apps SEP-1724 handshake. Without this, hosts that follow the spec
  // (Claude Desktop) iframe the HTML but show it as code text because the
  // expected client-side connect() never fires. `strict: true` surfaces any
  // handshake-ordering issues as errors in the iframe console instead of
  // silent failures.
  (async () => {{
    try {{
      const mod = await import('https://esm.sh/@modelcontextprotocol/ext-apps@^1.7.0');
      const app = new mod.App({{ name: 'screen-map', version: '0.1.0' }});
      await app.connect({{ strict: true }});
    }} catch (e) {{
      console.warn('MCP Apps connect failed (likely older host):', e);
      // Fallback to older mcp-ui lifecycle ping for legacy hosts.
      try {{ window.parent.postMessage({{ type: 'ui-lifecycle-iframe-ready' }}, '*'); }} catch (_) {{}}
    }}
  }})();
</script>
</body>
</html>"""


async def _build_screen_map_html() -> str:
    """Async helper: fetch screens + render HTML. Shared between the Resource
    handler and the inline-fallback path in the tool."""
    screens = await _fetch_screen_summaries()
    payload = json.dumps([s.model_dump(mode="json") for s in screens])
    return _build_html(payload)


# Resource handler — MCP Apps hosts (Claude Desktop, VSCode, …) fetch this
# directly via resources/read when they see the tool's _meta.ui.resourceUri.
@mcp.resource(
    SCREEN_MAP_URI,
    name="screen_map_ui",
    title="DOOH Control Tower — Screen Network Map",
    description="Leaflet map of the seeded screen network, color-coded by market.",
    mime_type=MCP_APP_HTML_MIME,
    # Tell the host how big to render the iframe. Without this, hosts that
    # respect MCP Apps render the iframe at 0px (invisible) — explains
    # "widget rendered" system messages with no visible map. Width 100% so
    # it fills the chat column; height 560px is enough for a NYC-bbox
    # Leaflet map with room for the legend.
    meta={"mcpui.dev/ui-preferred-frame-size": ["100%", "560px"]},
)
async def screen_map_resource() -> str:
    return await _build_screen_map_html()


# Tool — the agent's entry point. _meta.ui.resourceUri tells MCP Apps hosts
# where to fetch the UI. The inline UIResource in `content` is the older
# mcp-ui fallback for hosts that don't speak MCP Apps yet.
@mcp.tool(
    meta={"ui": {"resourceUri": SCREEN_MAP_URI}},
)
async def show_screen_map() -> list[TextContent]:
    """Render the screen network on a Leaflet map, inline in the chat.

    First mcp-ui surface for DOOH Control Tower. The host fetches the UI via
    `_meta.ui.resourceUri` (MCP Apps SEP-1724) and renders it in a sandboxed
    iframe. Markers are color-coded by market (Manhattan / Brooklyn / Queens);
    click any marker for name, screen_type, and external_id. Map auto-fits
    to the network's current bounds.
    """
    # Pure MCP Apps path: text content tells the agent what's happening;
    # the actual HTML is served by the registered @mcp.resource() handler at
    # SCREEN_MAP_URI, fetched separately by the host via resources/read.
    # No embedded UIResource — that path competes with the resources/read
    # path and some hosts (Claude Desktop, observed) prefer the embedded
    # path and then show it as text instead of rendering.
    return [
        TextContent(
            type="text",
            text="Rendering the screen network map (100 screens across Manhattan, "
            "Brooklyn, and Queens).",
        ),
    ]
