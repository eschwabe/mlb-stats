"""Shared fixtures: canned Stats API payloads shaped like the real service,
plus a fixture that mocks ``urllib.request.urlopen`` so tests run offline."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest


class FakeHTTPResponse(io.BytesIO):
    """Stands in for the context manager returned by ``urllib.request.urlopen``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.close()
        return False


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock ``urllib.request.urlopen`` (as used by ``mlb_stats.api``).

    Returns a controller dict:
        http["queue"]    - items to return in order; dict payloads become 200
                           responses, Exception instances are raised
        http["requests"] - the ``urllib.request.Request`` objects received
    """
    queue: list[Any] = []
    requests: list[Any] = []

    def fake_urlopen(req: Any, timeout: float | None = None) -> Any:
        requests.append(req)
        item = queue.pop(0) if queue else {"ok": True}
        if isinstance(item, BaseException):
            raise item
        return FakeHTTPResponse(item)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return {"queue": queue, "requests": requests}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_game(
    game_pk: int,
    state: str,
    away: str,
    home: str,
    *,
    away_score: int | None = None,
    home_score: int | None = None,
    game_date: str = "2026-08-16T18:10:00Z",
) -> dict[str, Any]:
    """Build a schedule-entry shaped like the real Stats API."""
    return {
        "gamePk": game_pk,
        "gameDate": game_date,
        "officialDate": "2026-08-16",
        "status": {
            "detailedState": state,
            "abstractState": "END" if state == "Final" else "IN",
        },
        "teams": {
            "away": {"team": {"id": 157, "name": away}, "score": away_score, "isWinner": None},
            "home": {"team": {"id": 112, "name": home}, "score": home_score, "isWinner": None},
        },
    }


# ---------------------------------------------------------------------------
# Schedule fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def yankees_final() -> dict[str, Any]:
    return make_game(775001, "Final", "New York Yankees", "Boston Red Sox", away_score=5, home_score=3)


@pytest.fixture
def dodgers_live() -> dict[str, Any]:
    return make_game(
        775002, "In Progress 6th", "Los Angeles Dodgers", "San Francisco Giants",
        away_score=2, home_score=4, game_date="2026-08-16T19:05:00Z",
    )


@pytest.fixture
def mets_pre_game() -> dict[str, Any]:
    return make_game(775003, "Pre-Game", "New York Mets", "Philadelphia Phillies", game_date="2026-08-16T23:20:00Z")


@pytest.fixture
def schedule(
    yankees_final: dict[str, Any], dodgers_live: dict[str, Any], mets_pre_game: dict[str, Any]
) -> dict[str, Any]:
    return {"dates": [{"date": "2026-08-16", "games": [yankees_final, dodgers_live, mets_pre_game]}]}



# ---------------------------------------------------------------------------
# Boxscore fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def boxscore() -> dict[str, Any]:
    return {
        "gamePk": 775001,
        "teams": {
            "away": {
                "team": {"id": 157, "name": "New York Yankees"},
                "teamStats": {
                    "batting": {"runs": 5, "hits": 11, "avg": ".303", "ops": "1.020"},
                    "fielding": {"errors": 0},
                },
                "players": {
                    "ID111": {
                        "person": {"id": 111, "fullName": "Aaron Judge", "boxscoreName": "Judge, A."},
                        "stats": {
                            "batting": {
                                "atBats": 4, "runs": 2, "hits": 2, "doubles": 0, "triples": 0,
                                "homeRuns": 1, "rbi": 3, "baseOnBalls": 1, "strikeOuts": 1, "stolenBases": 0,
                            }
                        },
                    },
                    "ID222": {
                        "person": {"id": 222, "fullName": "Gerrit Cole", "boxscoreName": "Cole, G."},
                        "stats": {
                            "pitching": {
                                "inningsPitched": "6", "hits": 3, "runs": 2, "earnedRuns": 2,
                                "baseOnBalls": 1, "strikeOuts": 7, "homeRuns": 0,
                                "wins": 1, "losses": 0, "saves": 0, "era": "3.45", "outs": 18,
                            }
                        },
                    },
                },
            },
            "home": {
                "team": {"id": 112, "name": "Boston Red Sox"},
                "teamStats": {
                    "batting": {"runs": 3, "hits": 7, "avg": ".222", "ops": "0.750"},
                    "fielding": {"errors": 1},
                },
                "players": {
                    "ID333": {
                        "person": {"id": 333, "fullName": "Rafael Devers", "boxscoreName": "Devers, R."},
                        "stats": {
                            "batting": {
                                "atBats": 5, "runs": 1, "hits": 2, "doubles": 1, "triples": 0,
                                "homeRuns": 0, "rbi": 1, "baseOnBalls": 0, "strikeOuts": 2, "stolenBases": 1,
                            }
                        },
                    },
                },
            },
        },
        "topPerformers": [
            {"person": {"id": 111, "boxscoreName": "Judge, A."},
             "stats": {"batting": {"summary": "2 for 4, 1 HR, 3 RBI, 2 R"}}},
            {"person": {"id": 222, "boxscoreName": "Cole, G."},
             "stats": {"pitching": {"summary": "6 IP, 3 H, 2 ER, 7 K"}}},
        ],
        "info": [{"label": "Weather", "value": "78° and clear"}],
    }


# ---------------------------------------------------------------------------
# Play-by-play fixtures
# ---------------------------------------------------------------------------


def make_play(inning: int, half: str, description: str, *,
              scoring: bool = False, rbi: int = 0,
              away_score: int | None = None, home_score: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"description": description}
    if scoring:
        result["rbi"] = rbi
    if away_score is not None:
        result["awayScore"] = away_score
    if home_score is not None:
        result["homeScore"] = home_score
    return {
        "about": {"inning": inning, "halfInning": half, "isScoringPlay": scoring},
        "result": result,
        "matchup": {"batter": {"fullName": description.split()[0]}},
    }


@pytest.fixture
def play_by_play() -> dict[str, Any]:
    return {
        "gamePk": 775001,
        "currentPlay": None,
        "allPlays": [
            make_play(1, "Top", "Judge grounds out to short."),
            make_play(
                1, "Bottom", "Devers homers to right (402 ft).", scoring=True, rbi=2, away_score=0, home_score=2
            ),
            make_play(
                9, "Top", "Judge walks; mates score on a wild pitch.",
                scoring=True, rbi=3, away_score=5, home_score=3,
            ),
        ],
        "scoringPlays": [1, 2],
    }


@pytest.fixture
def live_play_by_play() -> dict[str, Any]:
    return {
        "gamePk": 775002,
        "currentPlay": {
            "about": {"inning": 6, "halfInning": "Top"},
            "count": {"balls": 2, "strikes": 1, "outs": 2},
            "matchup": {
                "batter": {"fullName": "Freddie Freeman"},
                "pitcher": {"fullName": "Logan Gilbert"},
            },
            "result": {"description": "Freeman strikes out swinging."},
            "runners": [
                {"runner": {"name": "Mookie Betts"}, "isOnBase": True},
                {"runner": {"name": "Will Smith"}, "isOnBase": False},
            ],
        },
        "allPlays": [
            make_play(6, "Top", "Freeman strikes out swinging.", away_score=2, home_score=4),
        ],
        "scoringPlays": [],
    }
