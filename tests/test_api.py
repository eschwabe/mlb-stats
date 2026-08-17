"""Tests for ``mlb_stats.api`` — the Stats API client (urlopen is mocked)."""

from __future__ import annotations

import io
import socket
import urllib.error
from typing import Any

import pytest

from mlb_stats.api import (
    BASE_URL,
    USER_AGENT,
    fetch_boxscore,
    fetch_play_by_play,
    fetch_schedule,
    get_json,
)


def make_http_error(code: int, body: str = "boom") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://statsapi.mlb.com/api/v1/x", code, "error", None, io.BytesIO(body.encode("utf-8"))
    )


class TestGetJson:
    def test_success_parses_json_and_sets_headers(self, http: dict[str, Any]) -> None:
        http["queue"].append({"hello": "world"})
        data = get_json("schedule", {"sportId": 1, "date": "2026-08-16"})
        assert data == {"hello": "world"}
        req = http["requests"][0]
        assert req.full_url == f"{BASE_URL}/schedule?sportId=1&date=2026-08-16"
        assert req.get_header("User-agent") == USER_AGENT
        assert req.get_header("Accept") == "application/json"

    def test_none_params_are_dropped(self, http: dict[str, Any]) -> None:
        http["queue"].append({})
        get_json("game/775001/boxscore", {"a": "1", "b": None})
        url = http["requests"][0].full_url
        assert url.endswith("?a=1")
        assert "b=" not in url

    def test_leading_slash_is_stripped(self, http: dict[str, Any]) -> None:
        http["queue"].append({})
        get_json("/schedule", {"sportId": 1})
        assert http["requests"][0].full_url.startswith(f"{BASE_URL}/schedule?")

    def test_404_returns_none(self, http: dict[str, Any]) -> None:
        http["queue"].append(make_http_error(404))
        assert get_json("game/1/boxscore") is None

    def test_http_error_exits_with_message(self, http: dict[str, Any]) -> None:
        http["queue"].append(make_http_error(500, "server exploded"))
        with pytest.raises(SystemExit) as exc:
            get_json("schedule", {"sportId": 1, "date": "2026-08-16"})
        assert "HTTP 500" in str(exc.value)
        assert "server exploded" in str(exc.value)

    def test_network_error_exits_with_message(self, http: dict[str, Any]) -> None:
        http["queue"].append(urllib.error.URLError(socket.gaierror("name resolution failed")))
        with pytest.raises(SystemExit) as exc:
            get_json("schedule")
        assert "Network error contacting" in str(exc.value)
        assert "name resolution failed" in str(exc.value)


class TestFetchers:
    def test_fetch_schedule_flattens_games(self, http: dict[str, Any], schedule: dict[str, Any]) -> None:
        http["queue"].append(schedule)
        games = fetch_schedule("2026-08-16")
        assert [g["gamePk"] for g in games] == [775001, 775002, 775003]
        url = http["requests"][0].full_url
        assert "sportId=1" in url
        assert "date=2026-08-16" in url

    def test_fetch_schedule_404_yields_empty_list(self, http: dict[str, Any]) -> None:
        http["queue"].append(make_http_error(404))
        assert fetch_schedule("1901-01-01") == []

    def test_fetch_schedule_without_dates(self, http: dict[str, Any]) -> None:
        http["queue"].append({"dates": []})
        assert fetch_schedule("2026-08-16") == []

    def test_fetch_boxscore_hits_game_path(self, http: dict[str, Any], boxscore: dict[str, Any]) -> None:
        http["queue"].append(boxscore)
        assert fetch_boxscore(775001) == boxscore
        assert http["requests"][0].full_url == f"{BASE_URL}/game/775001/boxscore"

    def test_fetch_boxscore_404_returns_none(self, http: dict[str, Any]) -> None:
        http["queue"].append(make_http_error(404))
        assert fetch_boxscore(775001) is None

    def test_fetch_play_by_play_hits_game_path(self, http: dict[str, Any], play_by_play: dict[str, Any]) -> None:
        http["queue"].append(play_by_play)
        assert fetch_play_by_play(775001) == play_by_play
        assert http["requests"][0].full_url == f"{BASE_URL}/game/775001/playByPlay"
