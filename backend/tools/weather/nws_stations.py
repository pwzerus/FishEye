"""The National Weather Service's airport weather stations, for weather on
catches (services/catch_weather.py), 2026-11-19.

    cd backend && .venv/Scripts/python -I tools/weather/nws_stations.py

Lists every state's stations from api.weather.gov (public domain, "open
data, free to use for any purpose"), keeps the airport stations (ICAO ids:
K... in the lower 48, PA/PF/PO/PP... in Alaska, PH... in Hawaii), which
report sky cover and pressure every hour, and writes
app/data/nws_stations.json. The server finds the station nearest a catch
from this list, so the catch's spot never leaves FishEye: only the station's
id goes to the weather service. One request at a time, 1 s apart.
"""
import json
import re
import sys
import time
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from app.data_import.provenance import USER_AGENT  # noqa: E402
from app.knowledge.jurisdictions import STATE_NAMES  # noqa: E402

OUT = BACKEND / "app" / "data" / "nws_stations.json"
AIRPORT = re.compile(r"^(K[A-Z0-9]{3}|P[AFHOP][A-Z0-9]{2})$")

client = httpx.Client(
    headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"}, timeout=60, follow_redirects=True
)


def get(url: str) -> dict:
    for attempt in range(4):
        time.sleep(1)
        r = client.get(url)
        if r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
            return r.json()
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    return r.json()


stations: dict[str, dict] = {}
for state in sorted(STATE_NAMES):
    url: str | None = f"https://api.weather.gov/stations?state={state}&limit=500"
    seen = 0
    while url:
        page = get(url)
        features = page.get("features", [])
        if not features:
            break
        seen += len(features)
        for f in features:
            p = f["properties"]
            sid = p["stationIdentifier"]
            if not AIRPORT.match(sid) or not f.get("geometry"):
                continue
            lng, lat = f["geometry"]["coordinates"][:2]
            stations[sid] = {"id": sid, "lat": round(lat, 4), "lng": round(lng, 4), "state": state}
        url = (page.get("pagination") or {}).get("next")
    print(f"{state}: {seen} stations listed, {sum(1 for s in stations.values() if s['state'] == state)} airports", flush=True)

# One station a line: the id and where it is, nothing else.
rows = [json.dumps({"id": s["id"], "lat": s["lat"], "lng": s["lng"]}, separators=(",", ":")) for s in sorted(stations.values(), key=lambda s: s["id"])]
OUT.write_text("[\n" + ",\n".join(rows) + "\n]\n", encoding="utf-8")
print("STATIONS_DONE", len(stations), OUT, flush=True)
