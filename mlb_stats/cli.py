"""Command-line interface for mlb_stats."""

from __future__ import annotations

import argparse
import json
import os
import signal
import time
from datetime import date
from typing import Any

from .api import fetch_boxscore, fetch_play_by_play, fetch_schedule
from .formatting import print_game_list, summarize_game
from .games import FINAL_STATES, NOT_STARTED_STATES, pick_game


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlb-stats", description="Read latest stats for an MLB game via MLB's Stats API."
    )
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Date in YYYY-MM-DD (default: today)")
    parser.add_argument("--game-pk", type=int, help="Direct game PK, skips schedule lookup")
    parser.add_argument("--team", help="Pick the game involving a team (name substring, e.g. 'yankees')")
    parser.add_argument("--list", action="store_true", help="List all games for the date and exit")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print raw JSON payloads")
    parser.add_argument("--follow", type=float, metavar="SECONDS", help="Re-poll every N seconds (Ctrl-C to stop)")
    return parser


def follow_game(
    game: dict[str, Any], pk: int, interval: float, as_json: bool
) -> None:
    """Re-poll boxscore/play-by-play every ``interval`` seconds until the game
    is final (or the user hits Ctrl-C)."""
    print(f"Following game {pk} every {interval:.0f}s — Ctrl-C to stop.")
    try:
        while True:
            box = fetch_boxscore(pk)
            pbp = fetch_play_by_play(pk)
            if box is None and pbp is None:
                print("\n  No stats available yet. Retrying...")
                time.sleep(interval)
                continue
            os.system("clear" if os.name != "nt" else "cls")
            if as_json:
                print(json.dumps({"boxscore": box, "playByPlay": pbp}, indent=2))
            else:
                summarize_game(game, box, pbp)
            state = game.get("status", {}).get("detailedState", "")
            if state in FINAL_STATES:
                print("  Game is over. Stopping.")
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def main() -> None:
    """Parse arguments and run the CLI. Returns normally on success."""
    args = build_parser().parse_args()

    if args.game_pk:
        # Try to recover schedule metadata (status/scores) for this game
        game: dict[str, Any] | None = {"gamePk": args.game_pk}
        try:
            for g in fetch_schedule(args.date):
                if g.get("gamePk") == args.game_pk:
                    game = g
                    break
        except SystemExit:
            pass
    else:
        games = fetch_schedule(args.date)
        if args.list:
            print_game_list(games) if games else print("No games found for that date.")
            return
        game = pick_game(games, args.team)

    if not game:
        why = f" involving team matching '{args.team}'" if args.team else ""
        print(f"No game found for {args.date}{why}. Try --list to see available games.")
        return

    pk = game.get("gamePk")
    if not pk:
        raise SystemExit("Selected game has no gamePk.")

    state = game.get("status", {}).get("detailedState", "")
    if state in NOT_STARTED_STATES:
        print(f"  Game {pk} hasn't started yet ({state}). No stats available.\n  Try again after first pitch.")
        return

    if args.follow:
        follow_game(game, pk, args.follow, args.as_json)
        return

    box = fetch_boxscore(pk)
    pbp = fetch_play_by_play(pk)
    if box is None and pbp is None:
        raise SystemExit(
            f"No stats available for game {pk} yet — it likely hasn't started.\n"
            f"Try again later, or pick a different game with --list / --team."
        )
    if args.as_json:
        print(json.dumps({"boxscore": box, "playByPlay": pbp}, indent=2))
    else:
        summarize_game(game, box, pbp)


def run() -> None:
    """Console entry point: restores default SIGPIPE behaviour, then runs ``main``."""
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
