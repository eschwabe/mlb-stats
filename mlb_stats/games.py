"""Game status helpers and game picking.

All functions here are pure (no I/O) and operate on the JSON dicts returned
by the Stats API, which makes them easy to unit test.
"""

from __future__ import annotations

from typing import Any

#: detailedState values that mean the game is over for good.
FINAL_STATES = {
    "Final",
    "Final/Doubleheader",
    "Game over",
    "Game Over",
    "Game over - Walkoff",
    "Game Over - Walkoff",
    "Suspended",
}

#: detailedState values that mean the game hasn't begun.
NOT_STARTED_STATES = {"Pre-Game", "TBD", "Delayed - TBD", "Scheduled"}


def game_state_of(game: dict[str, Any]) -> str:
    """The game's ``status.detailedState`` ("" when absent)."""
    return str(game.get("status", {}).get("detailedState") or "")


def game_is_live(game: dict[str, Any]) -> bool:
    """True when stats may still change (in progress, warmup, delayed, suspended)."""
    state = game_state_of(game)
    return state.startswith("In Progress") or state in {"Warmup", "Delayed", "Suspended"}


def game_in_progress(game: dict[str, Any]) -> bool:
    """True when the game is actively in progress."""
    return game_state_of(game).startswith("In Progress")


def game_not_started(game: dict[str, Any]) -> bool:
    """True when the game is still pre-game / scheduled."""
    return game.get("status", {}).get("detailedState", "") in NOT_STARTED_STATES


def team_name_of(side: dict[str, Any]) -> str:
    """Team name from a schedule/boxscore side (name is nested under 'team')."""
    name = side.get("name") or (side.get("team") or {}).get("name")
    return str(name or "")


def pick_game(
    games: list[dict[str, Any]], team: str | None = None
) -> dict[str, Any] | None:
    """Pick the 'latest' game: prefer live games, then finished, then anything.

    When ``team`` is given, only games involving a team whose normalized name
    contains the (normalized) ``team`` string are considered.
    """
    if not games:
        return None
    if team:
        needle = team.lower().replace(" ", "").replace(".", "")
        matches = [
            g
            for g in games
            if any(
                needle in team_name_of(side).lower().replace(" ", "").replace(".", "")
                for side in g.get("teams", {}).values()
            )
        ]
        games = matches
        if not games:
            return None
    in_progress = [g for g in games if game_in_progress(g)]
    live = [g for g in games if game_is_live(g)]
    finished = [g for g in games if not game_is_live(g) and not game_not_started(g)]
    pool = in_progress or live or finished or games
    return sorted(pool, key=lambda g: g.get("gameDate", g.get("officialDate", "")))[-1]
