"""UFC scraper — sources every field from ufc.com directly.

Pipeline:
  1. Fetch ufc.com/events  → list of /event/<slug> paths for upcoming events.
  2. For each event page extract: event name, start time (multi-source), venue,
     and the Main Card lineup.
  3. Return the next N events with full detail.

Date precedence (most to least authoritative):
  a) Per-event page `<time datetime="...">` — the broadcast main-card start.
  b) Date encoded in the slug (`ufc-fight-night-<month>-<day>-<year>`) —
     rock-solid for date-based slugs even when the page lacks `<time>`.
  c) Shifted listing-page timestamp — the events index embeds a "How to
     Watch the next UFC event" CTA on each card; those `data-timestamp`
     values describe event N+1, NOT event N. So for slugs without dates
     (e.g. `ufc-329`), we look up the PREVIOUS card's listing timestamp.

Event name normalization:
  When the page <title> contains "TBD vs TBD" (ufc.com placeholder for an
  unannounced headliner), but the main card is already populated, rewrite
  the headline from main_card[0] so the widget shows real fighters. Done
  at build time so any future change to main_card[0] flows through on the
  next hourly scrape.
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

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def _http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def _list_events() -> list[tuple[str, int | None]]:
    """Return (path, shifted_listing_ts) for each upcoming event on ufc.com/events.

    `shifted_listing_ts` is the largest `data-timestamp` value found in the
    PREVIOUS card's HTML block — because ufc.com's per-card "How to Watch"
    CTA describes the next upcoming event, not the event the card belongs to.
    For the very first event (no previous card) we return None and rely on
    the per-event `<time>` tag or the slug date.
    """
    try:
        html = _http(f"{BASE}/events")
    except Exception:
        return []

    parts = re.split(r'class="c-card-event--result__headline"', html)[1:]
    paths: list[str] = []
    ts_per_block: list[int | None] = []
    seen: set[str] = set()
    for block in parts:
        m = re.search(r'/event/([a-z][a-z0-9\-]+)', block[:6000])
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        ts_strs = re.findall(r'data-timestamp="(\d+)"', block[:6000])
        block_max = max((int(t) for t in ts_strs), default=None)
        paths.append(f"/event/{m.group(1)}")
        ts_per_block.append(block_max)

    # Shift: path[i] gets timestamp from block i-1 (the previous card's
    # "next event" CTA describes this card's event).
    results: list[tuple[str, int | None]] = []
    for i, p in enumerate(paths):
        shifted = ts_per_block[i - 1] if i > 0 else None
        results.append((p, shifted))
    return results


def _slug_date(slug: str) -> datetime | None:
    """Parse a date out of a ufc-fight-night-<month>-<day>-<year> slug."""
    m = re.match(r"ufc-fight-night-([a-z]+)-(\d{1,2})-(\d{4})", slug)
    if not m:
        return None
    month = MONTHS.get(m.group(1).lower())
    if not month:
        return None
    try:
        # No time of day in the slug — set to 00:00 UTC as a sentinel; the
        # per-event `<time>` tag (when present) overrides this anyway. We use
        # 00:00 so events sort correctly relative to events with real times.
        return datetime(int(m.group(3)), month, int(m.group(2)),
                        tzinfo=timezone.utc)
    except ValueError:
        return None


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
    return f"{parts[0]}: {parts[1]}"


def _rewrite_tbd_name(name: str, main_card: list[dict]) -> str:
    """If <title> still says 'TBD vs TBD' but main_card is announced, use the
    actual main-event fighters' last names. Re-runs on every scrape so any
    future change to main_card[0] propagates automatically."""
    if not main_card:
        return name
    if not re.search(r"\bTBD\b", name, re.IGNORECASE):
        return name
    main = main_card[0]
    red_last = (main.get("red") or "").strip().split()[-1:] or [""]
    blue_last = (main.get("blue") or "").strip().split()[-1:] or [""]
    if not red_last[0] or not blue_last[0]:
        return name
    headliner = f"{red_last[0]} vs {blue_last[0]}"
    # Preserve the prefix ("UFC Fight Night:", "UFC <n>:", etc.).
    if ":" in name:
        prefix = name.split(":", 1)[0].strip()
        return f"{prefix}: {headliner}"
    return f"UFC Fight Night: {headliner}"


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
    contains the full fight markup with linked athletes. The weight class is
    the first text node of the preceding chunk.
    """

    def name_from_anchor(raw: str) -> str:
        spans = re.findall(r"<span[^>]*>([^<]+)</span>", raw)
        if spans:
            return unescape(" ".join(s.strip() for s in spans if s.strip())).strip()
        return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw))).strip()

    parts = re.split(r"c-listing-fight__class-text", html)[1:]
    fights: list[dict] = []
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


def _fetch_event(path: str, shifted_listing_ts: int | None) -> dict | None:
    try:
        html = _http(f"{BASE}{path}")
    except Exception:
        return None

    slug = path.rsplit("/", 1)[-1]
    main_card = _parse_main_card(html)

    # Date: page <time> > slug-encoded date > previous-card's listing timestamp.
    start = _extract_start_utc(html)
    if not start:
        start = _slug_date(slug)
    if not start and shifted_listing_ts is not None:
        start = datetime.fromtimestamp(shifted_listing_ts, tz=timezone.utc)
    if not start:
        return None
    if start < datetime.now(timezone.utc) - timedelta(hours=12):
        return None

    name = _rewrite_tbd_name(_extract_event_name(html), main_card)
    venue, city = _extract_venue(html)
    return {
        "name": name,
        "kind": _classify(name),
        "venue": venue,
        "city": city,
        "country": "",
        "main_card_start_utc": start.isoformat().replace("+00:00", "Z"),
        "main_card": main_card,
        "url": f"{BASE}{path}",
    }


def fetch() -> list[dict]:
    listings = _list_events()
    out: list[dict] = []
    for path, ts in listings:
        ev = _fetch_event(path, ts)
        if ev:
            out.append(ev)
        if len(out) >= 10:
            break
    out.sort(key=lambda x: x["main_card_start_utc"])
    return out[:8]


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2))
