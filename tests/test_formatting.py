"""Tests for ``mlb_stats.formatting`` — rendering helpers (no network)."""

from __future__ import annotations

from typing import Any

import pytest

from mlb_stats.formatting import (
    batting_row,
    fmt_inning,
    num,
    person_name,
    pitching_row,
    print_game_list,
    print_table,
    summarize_game,
)


class TestFmtInning:
    def test_top(self) -> None:
        assert fmt_inning(4, "top") == "Top 4"

    def test_bottom(self) -> None:
        assert fmt_inning(4, "Bottom") == "Bot 4"

    def test_unknown_half(self) -> None:
        assert fmt_inning(4, "weird") == "Inning 4"
        assert fmt_inning(4, "") == "Inning 4"
        assert fmt_inning(4, None) == "Inning 4"


class TestPersonName:
    def test_full_name(self) -> None:
        assert person_name({"fullName": "Aaron Judge"}) == "Aaron Judge"

    def test_display_name(self) -> None:
        assert person_name({"displayName": "Judge"}) == "Judge"

    def test_id_fallback(self) -> None:
        assert person_name({"id": 111}) == "#111"

    def test_empty(self) -> None:
        assert person_name({}) == "#None"


class TestNum:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(3, 3.0), ("2.5", 2.5), (None, None), ("abc", None), ([1], None)],
    )
    def test_coercion(self, value: Any, expected: float | None) -> None:
        assert num(value) == expected


class TestPrintTable:
    def test_sorts_numeric_column_descending(self, capsys: pytest.CaptureFixture[str]) -> None:
        rows = [
            {"Name": "Bee", "AB": 4},
            {"Name": "Ace", "AB": 10},
            {"Name": "Cee", "AB": None},
        ]
        print_table("Title", rows, sort_key="AB")
        out = capsys.readouterr().out
        assert "Title" in out
        assert "----" in out
        assert out.index("Ace") < out.index("Bee") < out.index("Cee")

    def test_reverse_false_sorts_ascending(self, capsys: pytest.CaptureFixture[str]) -> None:
        rows = [{"Name": "Bee", "AB": 4}, {"Name": "Ace", "AB": 10}]
        print_table("T", rows, sort_key="AB", reverse=False)
        out = capsys.readouterr().out
        assert out.index("Bee") < out.index("Ace")

    def test_no_sort_key_preserves_order(self, capsys: pytest.CaptureFixture[str]) -> None:
        rows = [{"Name": "Bee", "AB": 4}, {"Name": "Ace", "AB": 10}]
        print_table("T", rows)
        out = capsys.readouterr().out
        assert out.index("Bee") < out.index("Ace")

    def test_empty_rows_prints_nothing(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_table("T", [])
        assert capsys.readouterr().out == ""

    def test_columns_are_padded_to_uniform_width(self, capsys: pytest.CaptureFixture[str]) -> None:
        rows = [{"Name": "Ab", "AB": 1}, {"Name": "Abelard", "AB": 10}]
        print_table("T", rows)
        lines = [line for line in capsys.readouterr().out.splitlines() if line.strip() and line.strip() != "T"]
        # every row (header, dashes, data) has exactly the same total width
        assert len({len(line) for line in lines}) == 1


class TestBattingRow:
    def test_full_entry(self) -> None:
        entry = {
            "person": {"boxscoreName": "Judge, A.", "fullName": "Aaron Judge"},
            "stats": {
                "batting": {
                    "atBats": 4, "runs": 2, "hits": 2, "doubles": 1, "triples": 0,
                    "homeRuns": 1, "rbi": 3, "baseOnBalls": 1, "strikeOuts": 1, "stolenBases": 0,
                }
            },
        }
        assert batting_row(entry) == {
            "Name": "Judge, A.", "AB": 4, "R": 2, "H": 2, "2B": 1, "3B": 0,
            "HR": 1, "RBI": 3, "BB": 1, "SO": 1, "SB": 0,
        }

    def test_missing_stats_default_to_zero(self) -> None:
        row = batting_row({"person": {"fullName": "Aaron Judge"}})
        assert row["Name"] == "Aaron Judge"
        assert row["AB"] == 0 and row["HR"] == 0

    def test_empty_entry(self) -> None:
        row = batting_row({})
        assert row["Name"] == "#None"
        assert all(v == 0 for k, v in row.items() if k != "Name")


def make_pitching(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "inningsPitched": "6", "hits": 3, "runs": 2, "earnedRuns": 2,
        "baseOnBalls": 1, "strikeOuts": 7, "homeRuns": 0,
        "wins": 1, "losses": 0, "saves": 0, "era": "3.45", "outs": 18,
    }
    base.update(overrides)
    return {"person": {"boxscoreName": "Cole, G."}, "stats": {"pitching": base}}


class TestPitchingRow:
    def test_era_passthrough(self) -> None:
        assert pitching_row(make_pitching())["ERA"] == "3.45"

    def test_era_computed_when_missing(self) -> None:
        assert pitching_row(make_pitching(era=None))["ERA"] == "3.00"  # 2 ER over 6 IP

    def test_era_computed_when_blank(self) -> None:
        assert pitching_row(make_pitching(era=""))["ERA"] == "3.00"

    def test_era_dash_without_innings(self) -> None:
        assert pitching_row(make_pitching(era=None, inningsPitched=None))["ERA"] == "-"

    def test_fields(self) -> None:
        row = pitching_row(make_pitching())
        assert row["Name"] == "Cole, G."
        assert row["IP"] == "6"
        assert row["SO"] == 7
        assert row["W"] == 1
        assert row["SV"] == 0


class TestSummarizeGame:
    def test_final_game_full_summary(
        self, capsys: pytest.CaptureFixture[str], yankees_final: dict, boxscore: dict, play_by_play: dict
    ) -> None:
        summarize_game(yankees_final, boxscore, play_by_play)
        out = capsys.readouterr().out
        assert "New York Yankees @ Boston Red Sox" in out
        assert "State: Final" in out
        assert "Final: 5 - 3" in out
        assert "Recent plays (3)" in out
        assert "[SCORING]" in out
        assert "Team stats" in out
        assert ".303" in out and "1.020" in out
        assert "Top performer: Judge, A." in out
        assert "Cole, G. — 6 IP, 3 H, 2 ER, 7 K" in out
        assert "Judge, A." in out  # batting table row
        assert "Weather: 78° and clear" in out

    def test_live_game_shows_situation(
        self, capsys: pytest.CaptureFixture[str], dodgers_live: dict, live_play_by_play: dict
    ) -> None:
        summarize_game(dodgers_live, None, live_play_by_play)
        out = capsys.readouterr().out
        assert "State: In Progress 6th" in out
        assert "Score: 2 - 4" in out
        assert "Situation: Top 6" in out
        assert "Count: 2/1" in out
        assert "Outs: 2" in out
        assert "Mookie Betts" in out
        assert "Batter: Freddie Freeman" in out
        assert "Pitcher: Logan Gilbert" in out
        assert "Last play: Freeman strikes out swinging." in out

    def test_scores_fall_back_to_last_play(
        self, capsys: pytest.CaptureFixture[str], schedule: dict, play_by_play: dict
    ) -> None:
        from conftest import make_game

        scoreless = make_game(775099, "Final", "Yankees", "Red Sox")
        summarize_game(scoreless, None, play_by_play)
        out = capsys.readouterr().out
        assert "Final: 5 - 3" in out  # from the last play's running totals

    def test_scoring_plays_accept_play_objects(
        self, capsys: pytest.CaptureFixture[str], yankees_final: dict, play_by_play: dict
    ) -> None:
        pbp = {**play_by_play, "scoringPlays": [play_by_play["allPlays"][1]]}
        summarize_game(yankees_final, None, pbp)
        out = capsys.readouterr().out
        assert "Scoring plays (1)" in out
        assert "Devers homers to right (402 ft)." in out

    def test_out_of_range_scoring_play_index_is_ignored(
        self, capsys: pytest.CaptureFixture[str], yankees_final: dict, play_by_play: dict
    ) -> None:
        pbp = {**play_by_play, "scoringPlays": [99]}
        summarize_game(yankees_final, None, pbp)
        assert "Scoring plays" not in capsys.readouterr().out

    def test_no_payloads_still_prints_header(
        self, capsys: pytest.CaptureFixture[str], yankees_final: dict
    ) -> None:
        summarize_game(yankees_final, None, None)
        out = capsys.readouterr().out
        assert "New York Yankees @ Boston Red Sox" in out
        assert "Final: 5 - 3" in out
        assert "Team stats" not in out

    def test_boxscore_team_names_win_over_game(
        self, capsys: pytest.CaptureFixture[str], dodgers_live: dict, boxscore: dict
    ) -> None:
        summarize_game(dodgers_live, boxscore, None)
        out = capsys.readouterr().out
        assert "New York Yankees @ Boston Red Sox" in out


class TestPrintGameList:
    def test_lists_games_with_scores_and_live_marker(
        self, capsys: pytest.CaptureFixture[str], schedule: dict
    ) -> None:
        print_game_list(schedule["dates"][0]["games"])
        out = capsys.readouterr().out
        assert "775001" in out and "775002" in out and "775003" in out
        assert "5-3" in out  # final score
        assert "2-4" in out  # live score
        assert "In Progress 6th" in out
        assert "* =" in out  # legend
