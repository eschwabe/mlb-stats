"""Offline smoke tests for the package entry points."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import mlb_stats

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_public_api() -> None:
    assert mlb_stats.__version__
    assert callable(mlb_stats.main)
    assert callable(mlb_stats.run)
    assert callable(mlb_stats.fetch_schedule)
    assert callable(mlb_stats.pick_game)


def test_python_m_ml_b_stats_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mlb_stats", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Read latest stats for an MLB game" in result.stdout
    for flag in ("--date", "--team", "--list", "--json", "--follow", "--game-pk"):
        assert flag in result.stdout


def test_legacy_script_still_runs() -> None:
    result = subprocess.run(
        [sys.executable, "mlb_game_stats.py", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--team" in result.stdout
