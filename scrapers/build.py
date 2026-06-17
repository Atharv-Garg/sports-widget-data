"""Merge F1 + UFC into the unified widget feed.

Output: docs/feed.json (served by GitHub Pages).

All UTC timestamps from the scrapers are augmented with pre-converted IST
strings so the Scriptable widget doesn't need timezone logic.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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


def main() -> int:
    sys.path.insert(0, str(ROOT / "scrapers"))
    import f1, ufc  # noqa: E402

    try:
        f1_events = _enrich_f1(f1.fetch())
    except Exception as e:
        print(f"[warn] F1 fetch failed: {e}", file=sys.stderr)
        f1_events = []

    try:
        ufc_events = _enrich_ufc(ufc.fetch())
    except Exception as e:
        print(f"[warn] UFC fetch failed: {e}", file=sys.stderr)
        ufc_events = []

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
