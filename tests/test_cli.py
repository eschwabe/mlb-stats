"""Tests for ``mlb_stats.cli`` — argument handling and orchestration.

All network calls are stubbed; no test touches the real Stats API.
"""

from __future__ import annotations

import json
import signal
from typing import Any

import pytest

import mlb_stats.cli as cli
from mlb_stats.cli import build_parser, main


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub the network calls used by the CLI.

    Returns a controller:
        stubs["state"]["schedule"]     - games returned by fetch_schedule
        stubs["state"]["boxscore"]     - returned by fetch_boxscore
        stubs["state"]["play_by_play"] - returned by fetch_play_by_play
        stubs["calls"]                 - ordered log of network calls made
    """
    calls: list[str] = []
    state: dict[str, Any] = {"schedule": [], "boxscore": None, "play_by_play": None}

    def schedule_stub(day: str) -> list[dict[str, Any]]:
        calls.append(f"schedule:{day}")
        return state["schedule"]

    def box_stub(pk: int) -> dict[str, Any] | None:
        calls.append(f"box:{pk}")
        return state["boxscore"]

    def pbp_stub(pk: int) -> dict[str, Any] | None:
        calls.append(f"pbp:{pk}")
        return state["play_by_play"]

    monkeypatch.setattr(cli, "fetch_schedule", schedule_stub)
    monkeypatch.setattr(cli, "fetch_boxscore", box_stub)
    monkeypatch.setattr(cli, "fetch_play_by_play", pbp_stub)
    monkeypatch.setattr(cli.time, "sleep", lambda _s: None)  # keep tests instant
    monkeypatch.setattr(cli.os, "system", lambda _cmd: 0)  # no terminal clearing
    return {"calls": calls, "state": state}


def set_argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr("sys.argv", ["mlb-stats", *args])


class TestParser:
    def test_defaults(self) -> None:
        from datetime import date

        args = build_parser().parse_args([])
        assert args.date == date.today().isoformat()
        assert args.list is False
        assert args.as_json is False
        assert args.follow is None
        assert args.team is None
        assert args.game_pk is None

    def test_all_options(self) -> None:
        args = build_parser().parse_args(
            ["--date", "2026-08-16", "--team", "yankees", "--list", "--json", "--follow", "10", "--game-pk", "775001"]
        )
        assert args.date == "2026-08-16"
        assert args.team == "yankees"
        assert args.list is True
        assert args.as_json is True
        assert args.follow == 10.0
        assert args.game_pk == 775001


class TestMain:
    def test_list_prints_games(self, monkeypatch, capsys, stubs, schedule: dict[str, Any]) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        set_argv(monkeypatch, "--date", "2026-08-16", "--list")
        main()
        out = capsys.readouterr().out
        assert "775001" in out and "775002" in out and "775003" in out
        assert "New York Yankees" in out
        assert stubs["calls"] == ["schedule:2026-08-16"]  # no boxscore/pbp fetched

    def test_list_without_games(self, monkeypatch, capsys, stubs) -> None:
        set_argv(monkeypatch, "--date", "2026-08-16", "--list")
        main()
        assert "No games found for that date." in capsys.readouterr().out

    def test_default_pick_prefers_live_game(
        self, monkeypatch, capsys, stubs, schedule: dict[str, Any], boxscore: dict, play_by_play: dict
    ) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        set_argv(monkeypatch, "--date", "2026-08-16")
        main()
        assert stubs["calls"] == ["schedule:2026-08-16", "box:775002", "pbp:775002"]
        assert capsys.readouterr().out  # summary printed

    def test_team_pick(
        self, monkeypatch, capsys, stubs, schedule: dict[str, Any], boxscore: dict, play_by_play: dict
    ) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "yankees")
        main()
        assert stubs["calls"] == ["schedule:2026-08-16", "box:775001", "pbp:775001"]
        assert "Judge, A." in capsys.readouterr().out

    def test_team_without_match(self, monkeypatch, capsys, stubs, schedule: dict[str, Any]) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "braves")
        main()
        out = capsys.readouterr().out
        assert "No game found for 2026-08-16 involving team matching 'braves'." in out
        assert "Try --list" in out

    def test_game_pk_direct(
        self, monkeypatch, capsys, stubs, schedule: dict[str, Any], boxscore: dict, play_by_play: dict
    ) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        set_argv(monkeypatch, "--date", "2026-08-16", "--game-pk", "775001")
        main()
        assert "box:775001" in stubs["calls"] and "pbp:775001" in stubs["calls"]

    def test_game_pk_survives_schedule_outage(
        self, monkeypatch, capsys, stubs, boxscore: dict, play_by_play: dict
    ) -> None:
        def schedule_boom(day: str) -> list[dict[str, Any]]:
            raise SystemExit("HTTP 500 from https://statsapi.mlb.com/api/v1/schedule")

        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        monkeypatch.setattr(cli, "fetch_schedule", schedule_boom)
        set_argv(monkeypatch, "--date", "2026-08-16", "--game-pk", "775001")
        main()
        assert "New York Yankees" in capsys.readouterr().out

    def test_json_output(
        self, monkeypatch, capsys, stubs, schedule: dict[str, Any], boxscore: dict, play_by_play: dict
    ) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "yankees", "--json")
        main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["boxscore"]["gamePk"] == 775001
        assert payload["playByPlay"]["gamePk"] == 775001

    def test_not_started_game_exits_early(self, monkeypatch, capsys, stubs, schedule: dict[str, Any]) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "phillies")
        main()
        out = capsys.readouterr().out
        assert "hasn't started yet (Pre-Game)" in out
        assert stubs["calls"] == ["schedule:2026-08-16"]

    def test_no_stats_yields_helpful_error(self, monkeypatch, stubs, schedule: dict[str, Any]) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "yankees")
        with pytest.raises(SystemExit) as exc:
            main()
        assert "No stats available for game 775001" in str(exc.value)


class TestFollow:
    def test_stops_when_game_is_final(
        self, monkeypatch, capsys, stubs, schedule: dict[str, Any], boxscore: dict, play_by_play: dict
    ) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "yankees", "--follow", "5")
        main()
        out = capsys.readouterr().out
        assert "Following game 775001 every 5s" in out
        assert "Game is over. Stopping." in out
        assert stubs["calls"] == ["schedule:2026-08-16", "box:775001", "pbp:775001"]

    def test_stops_on_interrupt(
        self, monkeypatch, capsys, stubs, schedule: dict[str, Any], boxscore: dict, play_by_play: dict
    ) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        stubs["state"]["boxscore"] = boxscore
        stubs["state"]["play_by_play"] = play_by_play
        n = {"box": 0}

        def flaky_box(pk: int) -> dict[str, Any] | None:
            n["box"] += 1
            if n["box"] > 1:
                raise KeyboardInterrupt
            return boxscore

        monkeypatch.setattr(cli, "fetch_boxscore", flaky_box)
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "dodgers", "--follow", "5")
        main()
        out = capsys.readouterr().out
        assert "Following game 775002 every 5s" in out
        assert "Stopped." in out
        assert n["box"] == 2  # second poll interrupted

    def test_retries_when_stats_not_ready(self, monkeypatch, capsys, stubs, schedule: dict[str, Any]) -> None:
        stubs["state"]["schedule"] = schedule["dates"][0]["games"]
        n = {"pbp": 0}

        def flaky_pbp(pk: int) -> dict[str, Any] | None:
            n["pbp"] += 1
            if n["pbp"] > 1:
                raise KeyboardInterrupt
            return None

        monkeypatch.setattr(cli, "fetch_play_by_play", flaky_pbp)
        set_argv(monkeypatch, "--date", "2026-08-16", "--team", "dodgers", "--follow", "5")
        main()
        out = capsys.readouterr().out
        assert "No stats available yet. Retrying..." in out
        assert "Stopped." in out


class TestRun:
    def test_run_restores_default_sigpipe(self, monkeypatch, capsys, stubs) -> None:
        prev = signal.getsignal(signal.SIGPIPE)
        try:
            monkeypatch.setattr("sys.argv", ["mlb-stats", "--date", "2026-08-16", "--list"])
            cli.run()
            assert signal.getsignal(signal.SIGPIPE) is signal.SIG_DFL
            assert "No games found for that date." in capsys.readouterr().out
        finally:
            signal.signal(signal.SIGPIPE, prev)
