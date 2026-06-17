"""UFC scraper — sources every field from ufc.com directly.

Pipeline:
  1. Fetch ufc.com/events  → list of /event/<slug> paths for upcoming events.
  2. For each event page extract: event name, start time (from <time datetime>),
     venue, and the Main Card lineup.
  3. Return the next N events with full detail.

ufc.com is the canonical source — TheSportsDB lags it by weeks for fight cards
and weight classes, so going straight to ufc.com gives the freshest data and
also yields a much longer upcoming list (5+ events typically).
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

BASE = "https://www.ufc.com"


def _http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def _list_events() -> list[tuple[str, int | None]]:
    """Scrape ufc.com/events for (path, main_card_unix_ts).

    Each event card on the listing exposes one or more `data-timestamp` Unix
    seconds values — early prelims, prelims, main card. The largest is the main
    card start. Returning the timestamp here means we don't depend on the
    per-event page having a `<time datetime>` tag (which it lacks for events
    further out, e.g. UFC 329).
    """
    try:
        html = _http(f"{BASE}/events")
    except Exception:
        return []

    results: list[tuple[str, int | None]] = []
    seen: set[str] = set()
    for block in re.split(r'class="c-card-event--result__headline"', html)[1:]:
        m = re.search(r'/event/([a-z][a-z0-9\-]+)', block[:6000])
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        ts_strs = re.findall(r'data-timestamp="(\d+)"', block[:6000])
        ts = max((int(t) for t in ts_strs), default=None)
        results.append((f"/event/{m.group(1)}", ts))
    return results


def _extract_event_name(html: str) -> str:
    # <title>UFC Fight Night | Kape vs Horiguchi | UFC</title>
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    if not m:
        return "UFC Event"
    parts = [p.strip() for p in unescape(m.group(1)).split("|")]
    parts = [p for p in parts if p and p.lower() != "ufc"]
    if not parts:
        return "UFC Event"
    if len(parts) == 1:
        return parts[0]
    # "UFC Fight Night | Kape vs Horiguchi" -> "UFC Fight Night: Kape vs Horiguchi"
    return f"{parts[0]}: {parts[1]}"


def _extract_start_utc(html: str) -> datetime | None:
    # <time datetime="2026-06-20T20:00:00Z">...</time> — main card start.
    m = re.search(r'<time[^>]*datetime="([^"]+)"', html)
    if not m:
        return None
    s = m.group(1).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _extract_venue(html: str) -> tuple[str, str]:
    """Return (venue_name, city_country)."""
    m = re.search(r'field--name-venue[^>]*>\s*([^<]+?)\s*<', html)
    if not m:
        return "", ""
    raw = unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    # ufc.com format: "Meta APEX,      Las Vegas United States"
    if "," in raw:
        venue, rest = raw.split(",", 1)
        return venue.strip(), rest.strip()
    return raw, ""


def _classify(name: str) -> str:
    if re.search(r"UFC\s+\d+", name):
        return "PPV"
    if "fight night" in name.lower():
        return "Fight Night"
    return "Event"


def _parse_main_card(html: str) -> list[dict]:
    """Extract main-card fights from a ufc.com event page.

    ufc.com renders each fight twice (mobile + desktop layouts), and each layout
    has its own `c-listing-fight__class-text` weight-class label. Splitting on
    that label yields two chunks per fight; the *second* chunk of each pair
    contains the full fight markup with linked athletes, so we walk chunks[1::2].
    Chunk[0] of each fight pair starts immediately after the weight-class label,
    so the weight class is the first text node in chunk[0] — we read it from the
    preceding chunk via paired iteration.
    """

    def name_from_anchor(raw: str) -> str:
        spans = re.findall(r"<span[^>]*>([^<]+)</span>", raw)
        if spans:
            return unescape(" ".join(s.strip() for s in spans if s.strip())).strip()
        return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw))).strip()

    parts = re.split(r"c-listing-fight__class-text", html)[1:]
    fights: list[dict] = []
    # Pair consecutive chunks: even index = mobile (weight class lives at top of
    # the chunk and the anchors are empty), odd index = desktop (anchors live in
    # this chunk, weight class is at the top of its preceding chunk).
    for i in range(0, len(parts) - 1, 2):
        mobile_ch = parts[i]
        desktop_ch = parts[i + 1]

        wt_m = re.match(r"[^>]*>\s*([^<]+?)\s*<", mobile_ch[:400])
        weight = unescape(wt_m.group(1)).strip() if wt_m else ""

        anchors = re.findall(r'/athlete/[a-z0-9\-]+">(.*?)</a>',
                             desktop_ch[:8000], re.DOTALL)
        if len(anchors) < 2:
            continue
        red = name_from_anchor(anchors[0])
        blue = name_from_anchor(anchors[1])
        if not red or not blue:
            continue

        title = bool(re.search(r"title\s+bout|championship",
                               mobile_ch[:1000] + desktop_ch[:2000],
                               re.IGNORECASE))

        fights.append({
            "red": red,
            "blue": blue,
            "weight_class": weight or "TBD",
            "title_fight": title,
        })

    return fights[:5]


def _fetch_event(path: str, listing_ts: int | None) -> dict | None:
    try:
        html = _http(f"{BASE}{path}")
    except Exception:
        return None

    # Prefer the per-event page's <time datetime="..."> (most precise — includes
    # adjustments). Fall back to the listing-page Unix timestamp.
    start = _extract_start_utc(html)
    if not start and listing_ts is not None:
        start = datetime.fromtimestamp(listing_ts, tz=timezone.utc)
    if not start:
        return None
    if start < datetime.now(timezone.utc) - timedelta(hours=12):
        return None

    name = _extract_event_name(html)
    venue, city = _extract_venue(html)
    return {
        "name": name,
        "kind": _classify(name),
        "venue": venue,
        "city": city,
        "country": "",
        "main_card_start_utc": start.isoformat().replace("+00:00", "Z"),
        "main_card": _parse_main_card(html),
        "url": f"{BASE}{path}",
    }


def fetch() -> list[dict]:
    listings = _list_events()
    out: list[dict] = []
    for path, ts in listings:
        ev = _fetch_event(path, ts)
        if ev:
            out.append(ev)
        if len(out) >= 8:
            break
    out.sort(key=lambda x: x["main_card_start_utc"])
    return out[:5]


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2))
