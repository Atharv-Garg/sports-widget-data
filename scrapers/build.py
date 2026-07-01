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


def _fetch_ufc(warnings: list[str]) -> list[dict]:
    """Try ufc.com first; degrade to ESPN on whole-listing failure. Per-event
    failures (validation, degraded stubs) trigger ESPN per-event recovery."""
    sys.path.insert(0, str(ROOT / "scrapers"))
    import ufc, ufc_espn  # noqa: E402

    try:
        ufc_events = ufc.fetch()
    except Exception as e:
        msg = f"ufc.com whole-listing fetch failed ({e}); using ESPN fallback"
        print(f"[warn] {msg}", file=sys.stderr)
        warnings.append(msg)
        try:
            return ufc_espn.fetch()
        except Exception as e2:
            err = f"ESPN whole-listing fallback also failed: {e2}"
            print(f"[error] {err}", file=sys.stderr)
            warnings.append(err)
            return []

    cleaned: list[dict] = []
    for ev in ufc_events:
        # Stubs from ufc.py (per-event fetch failed but listing data present):
        # try ESPN by date; if ESPN has the event, prefer it; otherwise keep
        # the stub so the event remains visible.
        if ev.get("_degraded"):
            warnings.append(
                f"ufc.com per-event fetch failed for {ev.get('name')} "
                f"({ev.get('_degraded')}); attempting ESPN recovery"
            )
            try:
                raw = ev.get("main_card_start_utc") or ""
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                recovered = ufc_espn.fetch_one(dt, name_hint=ev.get("name", ""))
                if recovered and _validate_ufc_event(recovered):
                    cleaned.append(recovered)
                    continue
            except Exception as e:
                warnings.append(f"ESPN recovery failed for {ev.get('name')}: {e}")
            # ESPN didn't have it either — keep the stub.
            cleaned.append(ev)
            continue

        if _validate_ufc_event(ev):
            cleaned.append(ev)
            continue

        warnings.append(
            f"ufc.com event failed validation: {ev.get('name')!r} "
            f"on {ev.get('main_card_start_utc')}; attempting ESPN recovery"
        )
        try:
            raw = ev.get("main_card_start_utc") or ""
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            recovered = ufc_espn.fetch_one(dt, name_hint=ev.get("name", ""))
            if recovered and _validate_ufc_event(recovered):
                cleaned.append(recovered)
        except Exception as e:
            warnings.append(f"ESPN recovery failed: {e}")

    return cleaned


def _ufc_start(ev: dict):
    raw = ev.get("main_card_start_utc") or ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _future_ufc(events: list[dict]) -> list[dict]:
    """Keep only events that haven't finished (start >= now - 12h), soonest first.

    Guards against past events and degraded ufc.com listing stubs (which bypass
    per-event validation) ever becoming 'next'.
    """
    now = datetime.now(timezone.utc)
    dated = [
        (dt, ev)
        for ev in events
        if (dt := _ufc_start(ev)) is not None and dt >= now - timedelta(hours=12)
    ]
    dated.sort(key=lambda x: x[0])
    return [ev for _, ev in dated]


def main() -> int:
    sys.path.insert(0, str(ROOT / "scrapers"))
    import f1  # noqa: E402

    warnings: list[str] = []

    try:
        f1_events = _enrich_f1(f1.fetch())
    except Exception as e:
        msg = f"F1 fetch failed: {e}"
        print(f"[warn] {msg}", file=sys.stderr)
        warnings.append(msg)
        f1_events = []

    try:
        f1_standings = f1.fetch_standings()
    except Exception as e:
        msg = f"F1 standings fetch failed: {e}"
        print(f"[warn] {msg}", file=sys.stderr)
        warnings.append(msg)
        f1_standings = None

    ufc_events = _future_ufc(_enrich_ufc(_fetch_ufc(warnings)))

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "generated_at_ist": datetime.now(IST).isoformat(),
        "f1": {
            "next": f1_events[0] if f1_events else None,
            "upcoming": f1_events[1:],
            "standings": f1_standings,
        },
        "ufc": {
            "next": ufc_events[0] if ufc_events else None,
            "upcoming": ufc_events[1:],
        },
        "_warnings": warnings,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(warnings)} warnings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
