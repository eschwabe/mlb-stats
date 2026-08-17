"""Human-readable rendering of schedules, boxscores and play-by-play."""

from __future__ import annotations

from typing import Any

from .games import FINAL_STATES, game_is_live, team_name_of


def fmt_inning(inning: int, half: str) -> str:
    """Format an inning like 'Top 4' / 'Bot 4' / 'Inning 4'."""
    half = (half or "").capitalize()
    if half == "Top":
        return f"Top {inning}"
    if half == "Bottom":
        return f"Bot {inning}"
    return f"Inning {inning}"


def person_name(person: dict[str, Any]) -> str:
    """Best-effort display name for a person object."""
    return person.get("fullName") or person.get("displayName") or f"#{person.get('id')}"


def num(v: Any) -> float | None:
    """Coerce to float, or None when not numeric."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def print_table(
    title: str, rows: list[dict[str, Any]], sort_key: str | None = None, reverse: bool = True
) -> None:
    """Print a fixed-width table of single-level dicts.

    When ``sort_key`` is given, rows are sorted by that column numerically
    (non-numeric values sort last).
    """
    if not rows:
        return
    if sort_key is not None:

        def _key(r: dict[str, Any]) -> tuple[int, float]:
            v = num(r[sort_key])
            return (1, 0) if v is None else (0, -v if reverse else v)

        rows = sorted(rows, key=_key)
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print(f"\n  {title}\n  " + "  ".join(c.ljust(widths[c]) for c in cols))
    print("  " + "  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in cols))


def batting_row(entry: dict[str, Any]) -> dict[str, Any]:
    """Reduce a boxscore player entry to a single batting table row."""
    s = (entry.get("stats") or {}).get("batting") or {}
    person = entry.get("person", {})
    return {
        "Name": person.get("boxscoreName") or person_name(person),
        "AB": s.get("atBats", 0), "R": s.get("runs", 0), "H": s.get("hits", 0),
        "2B": s.get("doubles", 0), "3B": s.get("triples", 0), "HR": s.get("homeRuns", 0),
        "RBI": s.get("rbi", 0), "BB": s.get("baseOnBalls", 0), "SO": s.get("strikeOuts", 0),
        "SB": s.get("stolenBases", 0),
    }


def pitching_row(entry: dict[str, Any]) -> dict[str, Any]:
    """Reduce a boxscore player entry to a single pitching table row.

    The API sometimes omits ``era``; when it is missing it is derived from
    earned runs and innings pitched.
    """
    s = (entry.get("stats") or {}).get("pitching") or {}
    person = entry.get("person", {})
    era = s.get("era")
    if era in (None, "", "-"):
        ip, er = num(s.get("inningsPitched")), num(s.get("earnedRuns"))
        era = f"{(er or 0) / ip * 9:.2f}" if ip else "-"
    return {
        "Name": person.get("boxscoreName") or person_name(person),
        "IP": s.get("inningsPitched", 0), "H": s.get("hits", 0), "R": s.get("runs", 0),
        "ER": s.get("earnedRuns", 0), "BB": s.get("baseOnBalls", 0), "SO": s.get("strikeOuts", 0),
        "HR": s.get("homeRuns", 0), "W": s.get("wins", 0), "L": s.get("losses", 0),
        "SV": s.get("saves", 0), "ERA": era,
    }


def summarize_game(
    game: dict[str, Any], box: dict[str, Any] | None, pbp: dict[str, Any] | None
) -> None:
    """Print a full human-readable summary of one game."""
    box = box or {}
    pbp = pbp or {}
    teams = box.get("teams") or {}
    away_side, home_side = teams.get("away", {}), teams.get("home", {})
    game_teams = game.get("teams") or {}
    away_name = team_name_of(away_side)
    if not away_name and (game_teams.get("away") or {}).get("score") is not None:
        away_name = team_name_of(game_teams["away"])
    away_name = away_name or "AWAY"
    home_name = team_name_of(home_side)
    if not home_name and (game_teams.get("home") or {}).get("score") is not None:
        home_name = team_name_of(game_teams["home"])
    home_name = home_name or "HOME"

    state = game.get("status", {}).get("detailedState") or "Unknown"

    # Scores: schedule payload has them; play-by-play results carry running totals
    away_score = (game.get("teams", {}).get("away", {}) or {}).get("score")
    home_score = (game.get("teams", {}).get("home", {}) or {}).get("score")
    if away_score is None or home_score is None:
        all_plays = pbp.get("allPlays") or []
        if all_plays:
            result = all_plays[-1].get("result", {})
            away_score = away_score if away_score is not None else result.get("awayScore")
            home_score = home_score if home_score is not None else result.get("homeScore")

    official = game.get("officialDate") or game.get("gameDate", "")
    print("=" * 72)
    score_str = ""
    if away_score is not None and home_score is not None:
        if state in FINAL_STATES:
            score_str = f"   Final: {away_score} - {home_score}"
        else:
            score_str = f"   Score: {away_score} - {home_score}"
    print(f"  {away_name} @ {home_name}")
    print(f"  Date: {official}   State: {state}{score_str}")
    print("=" * 72)

    # Current situation from the latest play
    current = pbp.get("currentPlay")
    if current and state not in FINAL_STATES:
        about = current.get("about", {})
        count = current.get("count", {})
        matchup = current.get("matchup", {})
        result = current.get("result", {})
        runners = current.get("runners") or []
        on_base = [r.get("runner", {}).get("name", "?") for r in runners if (r.get("isOnBase") or r.get("runner"))]
        print(f"\n  Situation: {fmt_inning(about.get('inning', 1), about.get('halfInning', ''))}"
              f"  |  Count: {count.get('balls', 0)}/{count.get('strikes', 0)}"
              f"  |  Outs: {count.get('outs', 0)}"
              f"  |  Runners: {', '.join(on_base) if on_base else 'none'}")
        print(f"  Batter: {matchup.get('batter', {}).get('fullName', '?')}"
              f"   Pitcher: {matchup.get('pitcher', {}).get('fullName', '?')}")
        if result.get("description"):
            print(f"  Last play: {result['description']}")

    # Recent plays
    all_plays = pbp.get("allPlays") or []
    if all_plays:
        recent = all_plays[-8:]
        print(f"\n  Recent plays ({len(recent)}):")
        for pl in recent:
            about = pl.get("about", {})
            result = pl.get("result", {})
            batter = pl.get("matchup", {}).get("batter", {}).get("fullName", "")
            tag = " [SCORING]" if about.get("isScoringPlay") else ""
            print(f"    {fmt_inning(about.get('inning', 1), about.get('halfInning', '')):<8} "
                  f"{result.get('description', '?')}{tag}  ({batter})")

    # Scoring play summary — scoringPlays holds indexes into allPlays (or play objects)
    scoring = []
    for item in (pbp.get("scoringPlays") or []):
        if isinstance(item, int):
            if 0 <= item < len(all_plays):
                scoring.append(all_plays[item])
        elif isinstance(item, dict):
            scoring.append(item)
    if scoring:
        print(f"\n  Scoring plays ({len(scoring)}):")
        for pl in scoring:
            about = pl.get("about", {})
            result = pl.get("result", {})
            print(f"    {fmt_inning(about.get('inning', 1), about.get('halfInning', '')):<8} "
                  f"{result.get('description', '?')}  ({result.get('rbi', 0)} RBI)")

    # Team stats
    if teams:
        print("\n  Team stats:")
        print(f"    {'':<24} {'R':>3} {'H':>3} {'E':>3} {'AVG':>6} {'OPS':>6}")
        for label, side in ((away_name, away_side), (home_name, home_side)):
            batting = (side.get("teamStats") or {}).get("batting") or {}
            fielding = (side.get("teamStats") or {}).get("fielding") or {}
            print(
                f"    {label:<24} {batting.get('runs', 0):>3} {batting.get('hits', 0):>3} "
                f"{fielding.get('errors', 0):>3} {batting.get('avg', '-')!s:>6} {batting.get('ops', '-')!s:>6}"
            )

    # Top performers
    for tp in (box.get("topPerformers") or [])[:6]:
        person = tp.get("person", {})
        batting = (tp.get("stats") or {}).get("batting") or {}
        pitching = (tp.get("stats") or {}).get("pitching") or {}
        line = batting.get("summary") or pitching.get("summary") or ""
        if line:
            print(f"\n  Top performer: {person.get('boxscoreName', person_name(person))} — {line}")
            break
    more = (box.get("topPerformers") or [])[1:6]
    for tp in more:
        person = tp.get("person", {})
        batting = (tp.get("stats") or {}).get("batting") or {}
        pitching = (tp.get("stats") or {}).get("pitching") or {}
        line = batting.get("summary") or pitching.get("summary") or ""
        if line:
            print(f"    {person.get('boxscoreName', person_name(person))} — {line}")

    # Per-player tables (players is a dict keyed by 'ID<personId>' in this API)
    for side in ("away", "home"):
        side_data = teams.get(side, {})
        label = team_name_of(side_data)
        players = side_data.get("players") or {}
        entries = list(players.values()) if isinstance(players, dict) else (players or [])
        batters = [batting_row(e) for e in entries if ((e.get("stats") or {}).get("batting") or {}).get("atBats")]
        pitchers = [pitching_row(e) for e in entries if ((e.get("stats") or {}).get("pitching") or {}).get("outs")]
        if batters:
            print_table(f"{label} — batting", batters, sort_key="AB")
        if pitchers:
            print_table(f"{label} — pitching", pitchers, sort_key="IP")

    # Game notes
    notes = box.get("info") or []
    if notes:
        print("\n  Notes:")
        for n in notes[:4]:
            print(f"    {n.get('label', '')}: {n.get('value', '')}")
    print()


def print_game_list(games: list[dict[str, Any]]) -> None:
    """Print a one-line-per-game table with scores and live markers."""
    print(f"\n  {'State':<14} {'Score':<10} {'Away':<22} {'Home':<22} {'PK':<8}")
    print("  " + "-" * 84)
    for g in games:
        teams = g.get("teams", {})
        away = team_name_of(teams.get("away", {})) or "?"
        home = team_name_of(teams.get("home", {})) or "?"
        a, h = teams.get("away", {}).get("score"), teams.get("home", {}).get("score")
        score = f"{a}-{h}" if a is not None and h is not None else ""
        state = g.get("status", {}).get("detailedState", "?")
        marker = " *" if game_is_live(g) else ""
        print(f"  {state:<14} {score:<10} {away:<22} {home:<22} {g.get('gamePk', '?'):<8}{marker}")
    print("\n  (* = in progress)")
