"""HTTP access to MLB's public Stats API (https://statsapi.mlb.com).

Endpoints used:
    GET /api/v1/schedule?sportId=1&date=YYYY-MM-DD
    GET /api/v1/game/{gamePk}/boxscore
    GET /api/v1/game/{gamePk}/playByPlay
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, cast

BASE_URL = "https://statsapi.mlb.com/api/v1"
USER_AGENT = "mlb-game-stats/1.0 (personal script; python-urllib)"
TIMEOUT = 20


def get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """GET ``{BASE_URL}/{path}`` and parse the JSON body.

    Returns the parsed object, or ``None`` when the API answers 404.
    Raises ``SystemExit`` for other HTTP errors and network failures.
    """
    url = f"{BASE_URL}/{path.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return cast(dict[str, Any] | None, json.loads(resp.read().decode("utf-8")))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 404:
            return None
        raise SystemExit(f"HTTP {e.code} from {url}\n{body[:500]}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error contacting {url}: {e.reason}") from e


def fetch_schedule(day: str) -> list[dict[str, Any]]:
    """Return the list of games on a date (YYYY-MM-DD)."""
    data = get_json("schedule", {"sportId": 1, "date": day}) or {}
    games: list[dict[str, Any]] = []
    for d in data.get("dates", []):
        games.extend(d.get("games", []))
    return games


def fetch_boxscore(game_pk: int) -> dict[str, Any] | None:
    """Boxscore is a flat object: teams.{away,home} with teamStats/players, plus
    topPerformers, info, pitchingNotes."""
    return get_json(f"game/{game_pk}/boxscore")


def fetch_play_by_play(game_pk: int) -> dict[str, Any] | None:
    """Play-by-play: allPlays[], currentPlay, scoringPlays[], playsByInning[]."""
    return get_json(f"game/{game_pk}/playByPlay")
