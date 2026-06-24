"""F1 scraper — pulls upcoming Grand Prix sessions from OpenF1 (https://openf1.org).

OpenF1 is free, no key, returns session-level timing in UTC. We group sessions by
meeting (GP weekend) and return the next 4 meetings, each with its full session list.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

OPENF1 = "https://api.openf1.org/v1"
# Jolpica — free, keyless, Ergast-compatible. Used for championship standings.
JOLPICA = "https://api.jolpi.ca/ergast/f1"

# Constructor name -> team livery colour (for the widget's standings colour bars).
# Keys match Ergast/Jolpica constructor names; fallback handled at call site.
TEAM_COLOR = {
    "McLaren": "#FF8000",
    "Red Bull": "#3671C6",
    "Ferrari": "#E8002D",
    "Mercedes": "#27F4D2",
    "Aston Martin": "#229971",
    "Alpine F1 Team": "#0093CC",
    "Williams": "#64C4FF",
    "RB F1 Team": "#6692FF",
    "Racing Bulls": "#6692FF",
    "Sauber": "#52E252",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
    "Audi": "#009982",
    "Cadillac": "#C8A45C",
}

# OpenF1 uses internal session_name values. We map to clean display names.
SESSION_DISPLAY = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Sprint Qualifying": "Sprint Quali",
    "Sprint Shootout": "Sprint Shootout",
    "Sprint": "Sprint",
    "Qualifying": "Qualifying",
    "Race": "Race",
}

# Rough country -> flag emoji. Covers every 2024-2026 calendar country.
FLAG = {
    "Bahrain": "\U0001F1E7\U0001F1ED", "Saudi Arabia": "\U0001F1F8\U0001F1E6",
    "Australia": "\U0001F1E6\U0001F1FA", "Japan": "\U0001F1EF\U0001F1F5",
    "China": "\U0001F1E8\U0001F1F3", "United States": "\U0001F1FA\U0001F1F8",
    "USA": "\U0001F1FA\U0001F1F8", "Italy": "\U0001F1EE\U0001F1F9",
    "Monaco": "\U0001F1F2\U0001F1E8", "Canada": "\U0001F1E8\U0001F1E6",
    "Spain": "\U0001F1EA\U0001F1F8", "Austria": "\U0001F1E6\U0001F1F9",
    "United Kingdom": "\U0001F1EC\U0001F1E7", "UK": "\U0001F1EC\U0001F1E7",
    "Hungary": "\U0001F1ED\U0001F1FA", "Belgium": "\U0001F1E7\U0001F1EA",
    "Netherlands": "\U0001F1F3\U0001F1F1", "Azerbaijan": "\U0001F1E6\U0001F1FF",
    "Singapore": "\U0001F1F8\U0001F1EC", "Mexico": "\U0001F1F2\U0001F1FD",
    "Brazil": "\U0001F1E7\U0001F1F7", "Qatar": "\U0001F1F6\U0001F1E6",
    "United Arab Emirates": "\U0001F1E6\U0001F1EA", "UAE": "\U0001F1E6\U0001F1EA",
}


def _get(path: str, **params: Any) -> list[dict]:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{OPENF1}/{path}?{qs}" if qs else f"{OPENF1}/{path}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


def fetch() -> list[dict]:
    """Return list of upcoming F1 meetings, each with sessions[]."""
    now = datetime.now(timezone.utc)
    year = now.year

    meetings = _get("meetings", year=year)
    # If we're past mid-November, also pull next year for the early-season GPs.
    if now.month >= 11:
        try:
            meetings += _get("meetings", year=year + 1)
        except Exception:
            pass

    sessions = _get("sessions", year=year)
    if now.month >= 11:
        try:
            sessions += _get("sessions", year=year + 1)
        except Exception:
            pass

    by_meeting: dict[int, list[dict]] = {}
    for s in sessions:
        by_meeting.setdefault(s["meeting_key"], []).append(s)

    out: list[dict] = []
    for m in meetings:
        msessions = sorted(by_meeting.get(m["meeting_key"], []), key=lambda x: x["date_start"])
        if not msessions:
            continue
        # Skip meetings whose final session has already ended.
        last_end = msessions[-1].get("date_end") or msessions[-1]["date_start"]
        if datetime.fromisoformat(last_end.replace("Z", "+00:00")) < now:
            continue

        country = m.get("country_name") or ""
        season_year = msessions[0]["date_start"][:4]
        out.append({
            "name": m.get("meeting_official_name") or m.get("meeting_name"),
            "short_name": m.get("meeting_name"),
            "round": m.get("meeting_key"),  # OpenF1 has no round number; key is monotonic
            "circuit": m.get("circuit_short_name"),
            "location": m.get("location"),
            "country": country,
            "flag_emoji": FLAG.get(country, ""),
            "external_url": f"https://www.formula1.com/en/racing/{season_year}.html",
            "sessions": [
                {
                    "type": SESSION_DISPLAY.get(s["session_name"], s["session_name"]),
                    "start_utc": s["date_start"],
                    "end_utc": s.get("date_end"),
                }
                for s in msessions
            ],
        })

    out.sort(key=lambda x: x["sessions"][0]["start_utc"])
    return out[:4]


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


def fetch_standings(top: int = 5) -> dict:
    """Return current-season championship standings: top-N drivers and constructors.

    Source: Jolpica (Ergast-compatible). Shape:
      {"drivers": [{"position", "code", "name", "points", "team", "color"}],
       "constructors": [{"position", "name", "points", "color"}]}
    Raises on network/parse failure so the caller can decide to omit standings.
    """
    d = _get_json(f"{JOLPICA}/current/driverstandings/?limit={top}")
    dlists = d["MRData"]["StandingsTable"]["StandingsLists"]
    drivers: list[dict] = []
    if dlists:
        for row in dlists[0].get("DriverStandings", [])[:top]:
            drv = row.get("Driver", {})
            cons = (row.get("Constructors") or [{}])[-1]
            team = cons.get("name", "")
            drivers.append({
                "position": int(row.get("position", 0)),
                "code": drv.get("code") or (drv.get("familyName", "")[:3].upper()),
                "name": drv.get("familyName", ""),
                "points": _as_num(row.get("points")),
                "team": team,
                "color": TEAM_COLOR.get(team, "#9b9b9f"),
            })

    c = _get_json(f"{JOLPICA}/current/constructorstandings/?limit={top}")
    clists = c["MRData"]["StandingsTable"]["StandingsLists"]
    constructors: list[dict] = []
    if clists:
        for row in clists[0].get("ConstructorStandings", [])[:top]:
            cons = row.get("Constructor", {})
            name = cons.get("name", "")
            constructors.append({
                "position": int(row.get("position", 0)),
                "name": name,
                "points": _as_num(row.get("points")),
                "color": TEAM_COLOR.get(name, "#9b9b9f"),
            })

    return {"drivers": drivers, "constructors": constructors}


def _as_num(v: Any) -> float | int:
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    print(json.dumps({"meetings": fetch(), "standings": fetch_standings()}, indent=2))
