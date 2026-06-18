"""UFC scraper — sources every field from ufc.com directly.

Pipeline:
  1. Fetch ufc.com/events — extract per-event (slug, data-main-card-timestamp, h3).
  2. For each event page extract: page <title>, hero divider (top/bottom big text),
     venue, and the Main Card lineup.
  3. Compose a display name from <title> + hero divider, and use the listing
     data-main-card-timestamp as the authoritative main-card UTC time.

Why these specific sources:
  - `data-main-card-timestamp` is the named, per-card timestamp attached to the
    listing card's `__date` div. It does NOT drift between scrapes (unlike the
    per-event page's `<time datetime>` tag, which sometimes reflects broadcast
    window start rather than main-card start).
  - The hero divider (`e-divider__top` + `e-divider__bottom`) is ufc.com's
    authoritative "this is the main event" branding. If it says "TBD / TBD",
    UFC has not yet promoted any fight to the headliner slot — we report TBD
    honestly rather than fabricating one from the top of the fight list.
  - The first fight in the per-event page's c-listing-fight list is NOT a
    reliable main-event source: for events where the headliner hasn't been
    formally designated, the top fight may simply be the highest-profile
    booked fight while the actual headliner slot is still open.
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


def _list_events() -> list[tuple[str, datetime | None, str]]:
    """Return [(path, main_card_start_utc, h3_headliner), ...] from ufc.com/events.

    Reads the per-card `data-main-card-timestamp` (authoritative main-card UTC
    start, per ufc.com itself) and the `<h3>` headliner string for each event.
    """
    try:
        html = _http(f"{BASE}/events")
    except Exception:
        return []

    out: list[tuple[str, datetime | None, str]] = []
    seen: set[str] = set()
    for block in re.split(r'class="c-card-event--result__headline"', html)[1:]:
        head = block[:6000]
        slug_m = re.search(r'/event/([a-z][a-z0-9\-]+)', head)
        if not slug_m or slug_m.group(1) in seen:
            continue
        seen.add(slug_m.group(1))

        ts_m = re.search(r'data-main-card-timestamp="(\d+)"', head)
        start = datetime.fromtimestamp(int(ts_m.group(1)), tz=timezone.utc) if ts_m else None

        # `<h3>` headliner — the first text inside the anchor in this block.
        h3_m = re.search(r'/event/[a-z][a-z0-9\-]+">([^<]+)</a>', head)
        h3 = unescape(h3_m.group(1)).strip() if h3_m else ""

        out.append((f"/event/{slug_m.group(1)}", start, h3))
    return out


def _extract_page_title(html: str) -> str:
    """Strip `<title>UFC Fight Night | Kape vs Horiguchi | UFC</title>` to its
    meaningful brand prefix (e.g. 'UFC Fight Night', 'UFC 329: McGregor vs Holloway 2',
    'UFC Abu Dhabi'). When the title already contains a 'vs' headliner we keep
    it; otherwise we return just the brand to be combined with the hero divider.
    """
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    if not m:
        return "UFC Event"
    parts = [p.strip() for p in unescape(m.group(1)).split("|")]
    parts = [p for p in parts if p and p.lower() != "ufc"]
    if not parts:
        return "UFC Event"
    if len(parts) == 1:
        return parts[0]
    # Title has both brand and headliner segments: "UFC Fight Night | Kape vs Horiguchi"
    # If the headliner segment is real fighters (has " vs " and isn't TBD), join.
    brand, head = parts[0], parts[1]
    if " vs " in head.lower() and "tbd" not in head.lower():
        return f"{brand}: {head}"
    return brand  # brand only; caller will append hero divider headliner


def _extract_hero_divider(html: str) -> str:
    """Return ufc.com's officially-branded headliner from the per-event page hero,
    e.g. 'Kape vs Horiguchi', 'TBD vs TBD', or '' when the hero is missing.
    """
    top = re.search(r'class="e-divider__top">([^<]+)<', html)
    bot = re.search(r'class="e-divider__bottom">([^<]+)<', html)
    if not top or not bot:
        return ""
    t = unescape(top.group(1)).strip()
    b = unescape(bot.group(1)).strip()
    if not t or not b:
        return ""
    return f"{t} vs {b}"


def _compose_name(title: str, hero: str, listing_h3: str) -> str:
    """Build the display name from page title + hero divider + listing h3.

    Rules:
      - If the title already contains a 'vs' (e.g. 'UFC 329: McGregor vs Holloway 2'),
        use it verbatim.
      - Else if hero is real fighters (contains ' vs ', not 'TBD vs TBD'),
        join: '<title>: <hero>'.
      - Else if listing h3 is real fighters, join: '<title>: <h3>'.
      - Else label honestly: '<title>: Main event TBA'.
    """
    if " vs " in title.lower() and "tbd" not in title.lower():
        return title

    def usable(s: str) -> bool:
        return bool(s) and " vs " in s.lower() and "tbd" not in s.lower()

    if usable(hero):
        return f"{title}: {hero}"
    if usable(listing_h3):
        return f"{title}: {listing_h3}"
    return f"{title}: Main event TBA"


def _extract_per_event_time(html: str) -> datetime | None:
    """Fallback time source from the per-event page's <time datetime="...">.
    Used only if the listing lacks a `data-main-card-timestamp` value.
    """
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

    Note: the fight at position 0 is NOT guaranteed to be the official main
    event — it's only the first booked fight on the card. The hero divider on
    the per-event page is the authoritative source for the headliner.
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


def _fetch_event(path: str, listing_start: datetime | None,
                 listing_h3: str) -> dict | None:
    try:
        html = _http(f"{BASE}{path}")
    except Exception:
        return None

    # Date: listing's data-main-card-timestamp > per-event <time> fallback.
    start = listing_start or _extract_per_event_time(html)
    if not start:
        return None
    if start < datetime.now(timezone.utc) - timedelta(hours=12):
        return None

    title = _extract_page_title(html)
    hero = _extract_hero_divider(html)
    name = _compose_name(title, hero, listing_h3)
    venue, city = _extract_venue(html)
    main_card = _parse_main_card(html)

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
    out: list[dict] = []
    for path, start, h3 in _list_events():
        ev = _fetch_event(path, start, h3)
        if ev:
            out.append(ev)
        if len(out) >= 10:
            break
    out.sort(key=lambda x: x["main_card_start_utc"])
    return out[:8]


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2))
