"""ESPN UFC fallback client.

Called only by build.py when the primary ufc.com scrape fails (whole-listing
network failure, or a specific event's per-event page is unparseable).

ESPN's undocumented site API at site.api.espn.com responds with clean JSON for
the UFC scoreboard, no auth required. The data is downstream of UFC's
announcements but recovers most of what we need to keep the widget functional:
event name, date, venue, and the main event (ESPN orders competitions with the
main event last in the array — verified across every event in the current
season's calendar).

What ESPN can fill:
  - name (event brand + headliner)
  - main_card_start_utc
  - venue, city
  - main event (1 fight) as main_card[0]

What ESPN can't fill (degraded mode):
  - Full main card with per-fight weight classes — ESPN's top-level scoreboard
    JSON has incomplete weight_class data for non-headliner fights.
  - Title fight flag — ESPN doesn't expose this structurally.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

BASE = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"


def _http_json(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _normalize(event: dict) -> dict | None:
    """Convert an ESPN event into our unified schema (best-effort)."""
    raw_date = event.get("date") or ""
    try:
        s = raw_date.replace("Z", "+00:00")
        # ESPN dates like "2026-06-20T21:00Z" — fromisoformat handles after replace.
        start = datetime.fromisoformat(s)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if start < datetime.now(timezone.utc) - timedelta(hours=12):
        return None

    comps = event.get("competitions") or []
    # Main event is the LAST competition in ESPN's array.
    main = comps[-1] if comps else None
    main_fight = None
    if main:
        competitors = main.get("competitors") or []
        names = [
            (c.get("athlete") or {}).get("displayName", "").strip()
            for c in competitors
        ]
        names = [n for n in names if n]
        if len(names) >= 2:
            wc_type = main.get("type") or {}
            weight = wc_type.get("text") or wc_type.get("abbreviation") or ""
            # Append " Bout" so the widget's stripBout() normalises the same as
            # ufc.com-sourced data ("Flyweight" -> "Flyweight Bout" -> "Flyweight").
            if weight and not weight.lower().endswith("bout"):
                weight = f"{weight} Bout"
            main_fight = {
                "red": names[0],
                "blue": names[1],
                # ESPN's scoreboard doesn't expose divisional ranks; emit empty
                # strings for schema parity so the widget treats both as unranked.
                "red_rank": "",
                "blue_rank": "",
                "weight_class": weight or "TBD",
                "title_fight": False,  # ESPN doesn't expose this
            }

    name = (event.get("name") or "UFC Event").replace(". ", " ").replace(".", "")
    # ESPN uses "vs." with a period; standardise to "vs" to match ufc.com.
    if " vs " not in name and " vs." in name.lower():
        name = name.replace(" vs.", " vs").replace(" Vs.", " vs")

    venues = event.get("venues") or []
    v = venues[0] if venues else {}
    venue_name = v.get("fullName") or ""
    addr = v.get("address") or {}
    city = addr.get("city") or ""

    record = {
        "name": name,
        "kind": "PPV" if "UFC " in name and any(c.isdigit() for c in name.split(":", 1)[0]) else "Fight Night",
        "venue": venue_name,
        "city": city,
        "country": addr.get("country") or "",
        "main_card_start_utc": start.isoformat().replace("+00:00", "Z"),
        "main_card": [main_fight] if main_fight else [],
        "url": (event.get("links") or [{}])[0].get("href") or "https://www.ufc.com/events",
        "_source": "espn",
    }
    return record


def fetch(window_days: int = 120) -> list[dict]:
    """Return up to 8 upcoming UFC events from ESPN, in chronological order."""
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=window_days)
    qs = urllib.parse.urlencode({
        "dates": f"{today.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    })
    data = _http_json(f"{BASE}?{qs}")
    out: list[dict] = []
    for ev in data.get("events") or []:
        norm = _normalize(ev)
        if norm:
            out.append(norm)
    out.sort(key=lambda x: x["main_card_start_utc"])
    return out[:8]


def fetch_one(start_utc: datetime, name_hint: str = "") -> dict | None:
    """Return the ESPN event closest to `start_utc` (within ±24h). Used as a
    per-event fallback when ufc.com returns broken data for a single event."""
    try:
        events = fetch()
    except Exception:
        return None
    best = None
    best_delta = timedelta(hours=24)
    for ev in events:
        try:
            ev_start = datetime.fromisoformat(
                ev["main_card_start_utc"].replace("Z", "+00:00")
            )
        except ValueError:
            continue
        delta = abs(ev_start - start_utc)
        if delta < best_delta:
            best, best_delta = ev, delta
    return best


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2))
