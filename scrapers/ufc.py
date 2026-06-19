"""UFC scraper — ufc.com is the authoritative source.

Pipeline:
  1. Fetch ufc.com/events. Parse with BeautifulSoup to locate each event card,
     extract its slug, data-main-card-timestamp, and <h3> headliner text.
  2. For each event, GET ufc.com/event/<slug>. Parse the per-event page to
     extract: page <title>, hero divider (`e-divider__top` + `__bottom`,
     ufc.com's authoritative headliner), venue, and the Main Card lineup.
  3. Compose a display name and emit the unified event record.

Design choices:
  - `bs4.BeautifulSoup` is used over regex because ufc.com tweaks whitespace,
    class ordering, and attribute formats regularly. Tree traversal is
    resilient to those nuisance changes; regex isn't.
  - The hero divider text (e.g. "Kape vs Horiguchi", "TBD vs TBD") is the
    authoritative headliner per ufc.com's own UI. We don't fabricate headliners
    from `main_card[0]` — for events where UFC hasn't formally designated a
    headliner, we honestly report "Main event TBA".
  - Dates come from the listing's `data-main-card-timestamp` (named, per-card,
    no drift between scrapes). Per-event `<time datetime>` is used only as a
    last-resort fallback when the listing attribute is missing.

The scraper raises on hard failures (no event cards parseable, network error).
build.py catches and degrades to ESPN. Per-event soft failures (parse-empty
fields) are reported via the validation step in build.py.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

BASE = "https://www.ufc.com"


def _http(url: str, *, retries: int = 3) -> str:
    """GET with exponential-backoff retry. ufc.com occasionally times out for
    individual event pages; without retry, the per-event scrape fails and the
    event silently disappears from the feed for that hour. With three attempts
    (300ms, 1s backoff), transient failures become invisible."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(0.3 * (3 ** attempt))  # 0.3, 0.9, 2.7s
    raise last_err  # type: ignore[misc]


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _list_events() -> list[tuple[str, datetime | None, str]]:
    """Return [(path, main_card_start_utc, h3_headliner), ...]."""
    html = _http(f"{BASE}/events")
    soup = _soup(html)

    out: list[tuple[str, datetime | None, str]] = []
    seen: set[str] = set()

    for headline in soup.select("h3.c-card-event--result__headline"):
        a = headline.find("a", href=True)
        if not a or "/event/" not in a["href"]:
            continue
        slug = a["href"].rsplit("/", 1)[-1]
        if not slug or slug in seen:
            continue
        seen.add(slug)

        h3_text = a.get_text(strip=True)

        # Walk up to find the event card root. The wrapper element is named
        # `c-card-event--result` but its tag varies (article/div) across pages —
        # search by class only.
        card = headline.find_parent(class_="c-card-event--result")
        ts = None
        if card:
            date_div = card.select_one("[data-main-card-timestamp]")
            if date_div:
                raw = date_div.get("data-main-card-timestamp")
                if raw and raw.isdigit():
                    ts = datetime.fromtimestamp(int(raw), tz=timezone.utc)

        out.append((f"/event/{slug}", ts, h3_text))

    return out


def _extract_page_title(soup: BeautifulSoup) -> str:
    """Strip `<title>UFC Fight Night | Kape vs Horiguchi | UFC</title>` to its
    meaningful part. If the title already has a "vs" headliner we keep it;
    otherwise we return the brand alone for the caller to combine with hero.
    """
    title_tag = soup.find("title")
    if not title_tag:
        return "UFC Event"
    parts = [p.strip() for p in title_tag.get_text().split("|")]
    parts = [p for p in parts if p and p.lower() != "ufc"]
    if not parts:
        return "UFC Event"
    if len(parts) == 1:
        return parts[0]
    brand, head = parts[0], parts[1]
    if " vs " in head.lower() and "tbd" not in head.lower():
        return f"{brand}: {head}"
    return brand


def _extract_hero_divider(soup: BeautifulSoup) -> str:
    """Return ufc.com's officially-branded headliner from the page hero."""
    top = soup.select_one("[class*='e-divider__top']")
    bot = soup.select_one("[class*='e-divider__bottom']")
    if not top or not bot:
        return ""
    t = top.get_text(strip=True)
    b = bot.get_text(strip=True)
    if not t or not b:
        return ""
    return f"{t} vs {b}"


def _last_name(full: str) -> str:
    """Return the final family-name token from a fighter's full name. Strips
    generational suffixes ("Jr.", "Sr.", "II"-"IV") so 'Khalil Rountree Jr.'
    yields 'Rountree' rather than 'Jr.'. Mirrors the lastName() helper in
    SportsWidget.js."""
    parts = (full or "").strip().split()
    if not parts:
        return ""
    last = parts[-1]
    if re.fullmatch(r"(Jr\.?|Sr\.?|II|III|IV)", last, re.IGNORECASE) and len(parts) >= 2:
        last = parts[-2]
    return last


def _compose_name(title: str, hero: str, listing_h3: str,
                  main_card: list[dict] | None = None) -> str:
    """Build display name from the strongest available signal.

    Precedence:
      1. <title> already contains a real "X vs Y" -> use verbatim.
      2. Hero divider has real fighters -> "<title>: <hero>".
      3. Listing <h3> has real fighters -> "<title>: <h3>".
      4. main_card has at least one announced fight -> "<title>: <last(red)>
         vs <last(blue)>" using main_card[0]. The first fight on a ufc.com
         event page is the top-of-card bout by convention; when nothing else
         is branded, it is the de facto main event.
      5. Nothing announced anywhere -> "<title>: Main event TBA".
    """
    if " vs " in title.lower() and "tbd" not in title.lower():
        return title

    def usable(s: str) -> bool:
        return bool(s) and " vs " in s.lower() and "tbd" not in s.lower()

    if usable(hero):
        return f"{title}: {hero}"
    if usable(listing_h3):
        return f"{title}: {listing_h3}"
    if main_card:
        first = main_card[0]
        red = _last_name(first.get("red", ""))
        blue = _last_name(first.get("blue", ""))
        if red and blue:
            return f"{title}: {red} vs {blue}"
    return f"{title}: Main event TBA"


def _extract_per_event_time(soup: BeautifulSoup) -> datetime | None:
    tag = soup.find("time", attrs={"datetime": True})
    if not tag:
        return None
    s = tag["datetime"].replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _extract_venue(soup: BeautifulSoup) -> tuple[str, str]:
    venue_div = soup.select_one(".field--name-venue")
    if not venue_div:
        return "", ""
    raw = " ".join(venue_div.get_text(separator=" ", strip=True).split())
    if "," in raw:
        venue, rest = raw.split(",", 1)
        return venue.strip(), rest.strip()
    return raw, ""


def _classify(name: str) -> str:
    if "UFC " in name and any(c.isdigit() for c in name.split(":", 1)[0]):
        return "PPV"
    if "fight night" in name.lower():
        return "Fight Night"
    return "Event"


def _parse_main_card(soup: BeautifulSoup) -> list[dict]:
    """Extract main-card fights from the per-event page.

    ufc.com renders each fight twice (mobile + desktop layouts). Each
    `c-listing-fight` block contains the corner names and one
    `c-listing-fight__class-text` element with the weight class. With
    BeautifulSoup we can iterate over fight containers directly instead of
    splitting on text markers.
    """
    fights: list[dict] = []
    for fight in soup.select("div.c-listing-fight"):
        # Weight class.
        wt_el = fight.select_one(".c-listing-fight__class-text")
        weight = wt_el.get_text(strip=True) if wt_el else ""

        # Red / blue corner names — fighter name <a> inside corner-name divs.
        red_a = fight.select_one(".c-listing-fight__corner-name--red a")
        blue_a = fight.select_one(".c-listing-fight__corner-name--blue a")
        if not red_a or not blue_a:
            continue

        def anchor_to_name(a) -> str:
            spans = a.find_all("span")
            if spans:
                return " ".join(s.get_text(strip=True) for s in spans if s.get_text(strip=True))
            return a.get_text(strip=True)

        red = anchor_to_name(red_a)
        blue = anchor_to_name(blue_a)
        if not red or not blue:
            continue

        text = fight.get_text(" ", strip=True).lower()
        title_fight = "title bout" in text or "championship" in text

        fights.append({
            "red": red,
            "blue": blue,
            "weight_class": weight or "TBD",
            "title_fight": title_fight,
        })

    return fights[:5]


def _make_stub(path: str, listing_start: datetime, listing_h3: str,
               reason: str) -> dict:
    """Build a minimal event record from listing data alone — used when the
    per-event page is unreachable. The widget will show the event with a real
    date and headliner; only the main_card detail is missing until next run."""
    slug = path.rsplit("/", 1)[-1]
    # Derive a brand from the slug.
    if slug.startswith("ufc-fight-night"):
        brand = "UFC Fight Night"
    elif slug.startswith("ufc-") and slug[4:].split("-", 1)[0].isdigit():
        brand = f"UFC {slug[4:].split('-', 1)[0]}"
    else:
        brand = "UFC Event"
    if listing_h3 and " vs " in listing_h3.lower() and "tbd" not in listing_h3.lower():
        name = f"{brand}: {listing_h3}"
    else:
        name = f"{brand}: Main event TBA"
    return {
        "name": name,
        "kind": _classify(name),
        "venue": "",
        "city": "",
        "country": "",
        "main_card_start_utc": listing_start.isoformat().replace("+00:00", "Z"),
        "main_card": [],
        "url": f"{BASE}{path}",
        "_source": "ufc.com-listing",
        "_degraded": reason,
    }


def _fetch_event(path: str, listing_start: datetime | None,
                 listing_h3: str) -> dict | None:
    try:
        html = _http(f"{BASE}{path}")
    except Exception as e:
        # Per-event page unreachable after retries. If we have listing data
        # (slug + date + h3 from /events), surface a stub so the event doesn't
        # silently disappear from the feed. build.py may further upgrade this
        # via ESPN per-event recovery.
        if listing_start is not None:
            return _make_stub(path, listing_start, listing_h3,
                              f"per-event fetch failed: {type(e).__name__}")
        return None

    soup = _soup(html)
    start = listing_start or _extract_per_event_time(soup)
    if not start:
        return None
    if start < datetime.now(timezone.utc) - timedelta(hours=12):
        return None

    title = _extract_page_title(soup)
    hero = _extract_hero_divider(soup)
    venue, city = _extract_venue(soup)
    main_card = _parse_main_card(soup)
    # Compose name AFTER parsing main_card so the position-based fallback
    # (use main_card[0] when hero/h3/title are all TBD) can see the fights.
    name = _compose_name(title, hero, listing_h3, main_card)

    return {
        "name": name,
        "kind": _classify(name),
        "venue": venue,
        "city": city,
        "country": "",
        "main_card_start_utc": start.isoformat().replace("+00:00", "Z"),
        "main_card": main_card,
        "url": f"{BASE}{path}",
        "_source": "ufc.com",
    }


def fetch() -> list[dict]:
    """Fetch upcoming UFC events from ufc.com. Raises on listing failure."""
    listings = _list_events()
    if not listings:
        raise RuntimeError("ufc.com listing returned 0 events")

    out: list[dict] = []
    for path, start, h3 in listings:
        ev = _fetch_event(path, start, h3)
        if ev:
            out.append(ev)
        if len(out) >= 10:
            break
    out.sort(key=lambda x: x["main_card_start_utc"])
    return out[:8]


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2))
