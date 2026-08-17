# mlb-stats

Read the latest stats for an MLB game — boxscore, play-by-play, team stats,
top performers — straight from MLB's public
[Stats API](https://statsapi.mlb.com). No runtime dependencies: pure Python
standard library (3.9+).

```text
  New York Yankees @ Boston Red Sox
  Date: 2026-08-16   State: Final   Final: 5 - 3

  Recent plays (3):
    Top 1    Judge grounds out to SS.  (Aaron Judge)
    Bot 1    Devers homers to RF (402 ft). [SCORING]  (Rafael Devers)
    Top 9    Judge walks. Team mates score on wild pitch. [SCORING]  (Aaron Judge)

  Team stats:
                              R   H   E    AVG    OPS
    New York Yankees          5  11   0   .303  1.020
    Boston Red Sox            3   7   1   .222  0.750
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or run straight from a checkout without installing:

```bash
python3 -m mlb_stats --help
```

## Usage

```bash
# Auto-pick the most recent/interesting game today
mlb-stats

# List all games on a given date
mlb-stats --date 2026-08-16 --list

# A specific game by PK, or by team name (substring match)
mlb-stats --team yankees
mlb-stats --game-pk 775432

# Live: re-poll every 10 seconds (Ctrl-C to stop)
mlb-stats --team dodgers --follow 10

# Dump the raw JSON payloads
mlb-stats --team mets --json
```

The legacy single-file invocation still works: `python3 mlb_game_stats.py --help`.

## Development

```bash
make venv        # create .venv and install the package with dev extras
make check       # ruff + mypy + pytest
make test        # pytest only
make lint        # ruff check
make format      # ruff --fix + ruff format
```

### Project layout

```
mlb_stats/
├── __init__.py    # public API + __version__
├── __main__.py    # python -m mlb_stats
├── api.py         # Stats API HTTP client (urllib, stdlib only)
├── games.py       # game status helpers, team matching, game picking
├── formatting.py  # tables and human-readable summaries
└── cli.py         # argparse CLI, --follow loop
tests/             # pytest suite (network mocked, no live API calls)
```

### Testing

The test suite mocks `urllib.request.urlopen`, so it runs fully offline
against canned Stats API payloads that mirror the real response shapes.

## Known quirks

* Innings pitched arrive from the API in baseball notation (`"5.1"` = 5 1/3
  innings). The derived-ERA fallback path treats it as a plain decimal; the
  API's own `era` field (used when present) is always correct.
* `Suspended` games are treated as final for display purposes.
