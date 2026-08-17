#!/usr/bin/env python3
"""Backwards-compatible entry point for the old single-file script.

The implementation now lives in the ``mlb_stats`` package; this file only
delegates to it so existing invocations keep working:

    python3 mlb_game_stats.py --team yankees
"""

from mlb_stats.cli import run

if __name__ == "__main__":
    run()
