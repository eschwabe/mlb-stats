"""Tests for ``mlb_stats.games`` — status helpers and game picking (pure)."""

from __future__ import annotations

from typing import Any

import pytest

from mlb_stats.games import (
    FINAL_STATES,
    NOT_STARTED_STATES,
    game_in_progress,
    game_is_live,
    game_not_started,
    game_state_of,
    pick_game,
    team_name_of,
)


def game(
    state: str,
    away: str = "Alpha A's",
    home: str = "Beta B's",
    game_date: str = "2026-08-16T18:00:00Z",
) -> dict[str, Any]:
    return {
        "gamePk": 1,
        "gameDate": game_date,
        "officialDate": "2026-08-16",
        "status": {"detailedState": state},
        "teams": {"away": {"team": {"name": away}}, "home": {"team": {"name": home}}},
    }


class TestStateHelpers:
    def test_game_state_of_reads_detailed_state(self) -> None:
        assert game_state_of(game("In Progress 4th")) == "In Progress 4th"

    def test_game_state_of_missing_status(self) -> None:
        assert game_state_of({}) == ""
        assert game_state_of({"status": {}}) == ""

    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            ("Final", False),
            ("Final/Doubleheader", False),
            ("Pre-Game", False),
            ("In Progress 4th", True),
            ("In Progress 7th", True),
            ("Warmup", True),
            ("Delayed", True),
            ("Suspended", True),
        ],
    )
    def test_game_is_live(self, state: str, expected: bool) -> None:
        assert game_is_live(game(state)) is expected

    @pytest.mark.parametrize(
        ("state", "expected"),
        [("In Progress 4th", True), ("Warmup", False), ("Final", False), ("Pre-Game", False)],
    )
    def test_game_in_progress(self, state: str, expected: bool) -> None:
        assert game_in_progress(game(state)) is expected

    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            ("Pre-Game", True),
            ("TBD", True),
            ("Scheduled", True),
            ("Delayed - TBD", True),
            ("Final", False),
            ("In Progress 1st", False),
        ],
    )
    def test_game_not_started(self, state: str, expected: bool) -> None:
        assert game_not_started(game(state)) is expected

    def test_state_constants_are_disjoint(self) -> None:
        assert FINAL_STATES.isdisjoint(NOT_STARTED_STATES)


class TestTeamNameOf:
    def test_flat_name(self) -> None:
        assert team_name_of({"name": "Yankees"}) == "Yankees"

    def test_nested_team_name(self) -> None:
        assert team_name_of({"team": {"name": "Yankees"}}) == "Yankees"

    def test_missing(self) -> None:
        assert team_name_of({}) == ""
        assert team_name_of({"team": {}}) == ""


class TestPickGame:
    def test_empty_list(self) -> None:
        assert pick_game([]) is None

    def test_prefers_in_progress(self, schedule: dict[str, Any]) -> None:
        assert pick_game(schedule["dates"][0]["games"])["gamePk"] == 775002

    def test_prefers_warmup_over_final(self, yankees_final: dict[str, Any]) -> None:
        warm = game("Warmup", "Cubs", "Brewers")
        assert pick_game([yankees_final, warm]) is warm

    def test_prefers_final_over_pre_game(self, schedule: dict[str, Any]) -> None:
        games = [g for g in schedule["dates"][0]["games"] if g["gamePk"] in (775001, 775003)]
        assert pick_game(games)["gamePk"] == 775001

    def test_falls_back_to_unstarted(self, mets_pre_game: dict[str, Any]) -> None:
        assert pick_game([mets_pre_game]) is mets_pre_game

    def test_prefers_latest_game_date(self) -> None:
        early = game("In Progress 3rd", "A", "B", "2026-08-16T17:00:00Z")
        late = game("In Progress 7th", "C", "D", "2026-08-16T20:00:00Z")
        assert pick_game([early, late]) is late

    def test_team_filter_matches(self, schedule: dict[str, Any]) -> None:
        games = schedule["dates"][0]["games"]
        assert pick_game(games, "yankees")["gamePk"] == 775001
        assert pick_game(games, "dodgers")["gamePk"] == 775002
        assert pick_game(games, "phillies")["gamePk"] == 775003

    def test_team_filter_no_match(self, schedule: dict[str, Any]) -> None:
        assert pick_game(schedule["dates"][0]["games"], "braves") is None

    def test_team_name_normalization(self, schedule: dict[str, Any]) -> None:
        games = schedule["dates"][0]["games"]
        assert pick_game(games, "RED  SOX")["gamePk"] == 775001
        assert pick_game(games, "PHILLIES.")["gamePk"] == 775003
        # matching is a substring match, so unrelated teams do not match
        assert pick_game(games, "brewers") is None

    def test_team_filter_prefers_in_progress(self) -> None:
        final = game("Final", "New York Yankees", "Red Sox", "2026-08-16T16:00:00Z")
        live = game("In Progress 2nd", "New York Yankees", "Brewers", "2026-08-16T18:00:00Z")
        assert pick_game([final, live], "yankees") is live
