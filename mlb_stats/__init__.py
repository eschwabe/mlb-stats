"""mlb_stats — read the latest stats for an MLB game from MLB's public Stats API.

Uses only the Python standard library (Python 3.9+).

Modules:
    api         — HTTP client for statsapi.mlb.com
    games       — game status helpers and game picking
    formatting  — human-readable rendering (tables, summaries)
    cli         — command-line interface
"""

from .api import fetch_boxscore, fetch_play_by_play, fetch_schedule, get_json
from .cli import main, run
from .formatting import batting_row, person_name, pitching_row, print_game_list, summarize_game
from .games import game_is_live, game_not_started, game_state_of, pick_game, team_name_of

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "batting_row",
    "fetch_boxscore",
    "fetch_play_by_play",
    "fetch_schedule",
    "game_in_progress",
    "game_is_live",
    "game_not_started",
    "game_state_of",
    "get_json",
    "main",
    "person_name",
    "pick_game",
    "pitching_row",
    "print_game_list",
    "run",
    "summarize_game",
    "team_name_of",
]
