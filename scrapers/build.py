"""Merge F1 + UFC into the unified widget feed.

Output: docs/feed.json (served by GitHub Pages).

UFC source policy:
  - Primary: ufc.com via scrapers/ufc.py (BeautifulSoup, authoritative source).
  - Fallback: scrapers/ufc_espn.py (ESPN's undocumented JSON API). Used ONLY
    when ufc.com fails — either the whole listing (network/parse failure) or
    individual events that fail self-validation.
  - No comparison/reconciliation: when ufc.com works, ESPN is never called.

Self-validation runs on every ufc.com event before it's published. If an event
fails (e.g., empty name, far-past date, unparseable timestamp), it's dropped
from the output and we attempt to fill its date slot from ESPN as a recovery.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "feed.json"

IST = ZoneInfo("Asia/Kolkata")


def _to_ist(utc_iso: str | None) -> str | None:
    if not utc_iso:
        return None
    s = utc_iso.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).isoformat()


def _enrich_f1(events: list[dict]) -> list[dict]:
    for ev in events:
        for s in ev.get("sessions", []):
            s["start_ist"] = _to_ist(s.get("start_utc"))
            s["end_ist"] = _to_ist(s.get("end_utc"))
    return events


def _enrich_ufc(events: list[dict]) -> list[dict]:
    for ev in events:
        ev["main_card_start_ist"] = _to_ist(ev.get("main_card_start_utc"))
    return events


def _validate_ufc_event(ev: dict) -> bool:
    """Cheap sanity checks. Reject events whose data is obviously broken
    (HTML in name, empty name, date outside [now-12h, now+12mo], etc.)."""
    name = (ev.get("name") or "").strip()
    if not name or "<" in name or "undefined" in name.lower() or "null" in name.lower():
        return False

    raw = ev.get("main_card_start_utc") or ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if not (now - timedelta(hours=12) <= dt <= now + timedelta(days=365)):
        return False

    for f in ev.get("main_card") or []:
        if not (f.get("red") or "").strip() or not (f.get("blue") or "").strip():
            return False

    return True


def _fetch_ufc() -> list[dict]:
    """Try ufc.com first; degrade to ESPN on whole-listing failure. Per-event
    failures (self-validation fails) are individually filled from ESPN."""
    sys.path.insert(0, str(ROOT / "scrapers"))
    import ufc, ufc_espn  # noqa: E402

    try:
        ufc_events = ufc.fetch()
    except Exception as e:
        print(f"[warn] ufc.com fetch failed ({e}); falling back to ESPN whole list",
              file=sys.stderr)
        try:
            return ufc_espn.fetch()
        except Exception as e2:
            print(f"[error] ESPN fallback also failed: {e2}", file=sys.stderr)
            return []

    cleaned: list[dict] = []
    for ev in ufc_events:
        if _validate_ufc_event(ev):
            cleaned.append(ev)
            continue
        # Per-event recovery: try ESPN for an event near this date.
        print(f"[warn] ufc.com event failed validation: {ev.get('name')!r} "
              f"on {ev.get('main_card_start_utc')} — trying ESPN", file=sys.stderr)
        try:
            raw = ev.get("main_card_start_utc") or ""
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            recovered = ufc_espn.fetch_one(dt, name_hint=ev.get("name", ""))
            if recovered and _validate_ufc_event(recovered):
                cleaned.append(recovered)
        except Exception as e:
            print(f"[warn] ESPN per-event recovery failed: {e}", file=sys.stderr)

    return cleaned


def main() -> int:
    sys.path.insert(0, str(ROOT / "scrapers"))
    import f1  # noqa: E402

    try:
        f1_events = _enrich_f1(f1.fetch())
    except Exception as e:
        print(f"[warn] F1 fetch failed: {e}", file=sys.stderr)
        f1_events = []

    ufc_events = _enrich_ufc(_fetch_ufc())

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "generated_at_ist": datetime.now(IST).isoformat(),
        "f1": {
            "next": f1_events[0] if f1_events else None,
            "upcoming": f1_events[1:],
        },
        "ufc": {
            "next": ufc_events[0] if ufc_events else None,
            "upcoming": ufc_events[1:],
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
