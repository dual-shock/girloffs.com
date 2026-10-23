"""Command line tool for looking at and correcting the bracket (the admin panel does the same in a browser).

Run from the backend folder, e.g.:  python -m app.manage list
"""

import argparse
import random
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, db, edits
from .bracket import derive_state


def apply(fn, conn, target, value):
    """Make a change through edits.py (same checks and audit log as the admin panel); stop with an error if refused."""
    try:
        diff = fn(conn, target, value, "cli")
    except edits.EditError as e:
        sys.exit(f"ERROR: {e}. Nothing was changed.")
    print(f"ok: {diff}" if diff else "ok: it was already set like that, nothing changed")


def cmd_list(conn, args):
    players, matches, games = db.load(conn)
    names = {p["seed"]: p["display_name"] for p in players}
    state = derive_state(players, matches, games, config.now())
    for m in sorted(state["matches"], key=lambda m: m["number"]):
        p1, p2 = (f"{names[s]} ({s})" if s else src for s, src in zip(m["players"], m["sources"]))
        when = m["scheduled_at"] or "no time"
        winner = f"  winner: {names[m['winner']]}" if m["winner"] else ""
        print(f"#{m['number']:<3} {when}  {p1} {m['score'][0]}-{m['score'][1]} {p2}  [{m['status']}]{winner}")
        for g in games:
            if g["match_number"] == m["number"]:
                played = datetime.fromtimestamp(g["played_at"], timezone.utc).strftime("%H:%M")
                flag = "  EXCLUDED" if g["excluded"] else ""
                print(f"       game {g['mcsr_id']} at {played} UTC, winner uuid {g['winner_uuid']}{flag}")


def none_or(value):
    return None if value == "none" else value


def cmd_set_time(conn, args):
    apply(edits.edit_match, conn, args.match, {"scheduled_at": none_or(args.time)})


def cmd_set_winner(conn, args):
    apply(edits.edit_match, conn, args.match, {"winner_override": none_or(args.seed), "forfeit": args.forfeit})


def cmd_set_score(conn, args):
    apply(edits.edit_match, conn, args.match, {"score_override": none_or(args.score)})


def cmd_exclude_game(conn, args):
    apply(edits.set_game_excluded, conn, args.game, True)


def cmd_include_game(conn, args):
    apply(edits.set_game_excluded, conn, args.game, False)


def require_separate_db():
    if Path(config.DB_PATH).name == "girloffs.db":
        sys.exit("ERROR: demo commands overwrite results. Point DB_PATH at a separate file first, e.g. data/design.db")


# Fake results for designing: every look a match can have. Per match, the game winners by slot
# ("1" = slot 1, "2" = slot 2, "d" = draw), or "forfeit:N" = slot N wins by forfeit. Applied in match order,
# so later matches get the right players. Leaves 8 and 16 upcoming with known players, 12 live at 1-0,
# 13 live at 1-1, and 17-22 TBD (19 half known).
DESIGN_RESULTS = {
    1: "121", 2: "22", 3: "211", 4: "11", 5: "forfeit:2", 6: "1d22",
    7: "212", 9: "11", 10: "122", 11: "11", 12: "1", 13: "12", 14: "22",
    15: "121",
}


def cmd_demo_design(conn, args):
    """Fill a separate database with a believable mid-tournament bracket."""
    require_separate_db()
    uuids = dict(conn.execute("SELECT seed, uuid FROM players").fetchall())
    durations = random.Random(3)
    for number in sorted(DESIGN_RESULTS):
        plan = DESIGN_RESULTS[number]
        m = next(x for x in derive_state(*db.load(conn), config.now())["matches"] if x["number"] == number)
        pair = m["players"]
        if plan.startswith("forfeit:"):
            edits.edit_match(conn, number, {"winner_override": pair[int(plan[-1]) - 1], "forfeit": True}, "demo")
            continue
        start = datetime.fromisoformat(m["scheduled_at"])
        db.insert_games(conn, number, [{
            "mcsr_id": 900_000_000 + number * 10 + i,
            "played_at": int((start + timedelta(minutes=12 + 14 * i)).timestamp()),
            "player1_uuid": uuids[pair[0]],
            "player2_uuid": uuids[pair[1]],
            "winner_uuid": None if w == "d" else uuids[pair[int(w) - 1]],
            "duration_ms": durations.randint(8 * 60_000, 16 * 60_000),
            "forfeited": 0,
        } for i, w in enumerate(plan)])
    print("Design data loaded: finished, forfeit, live, upcoming and TBD matches are all on the bracket now.")


def cmd_demo_go2(conn, args):
    """Turn match 1 into Girloffs 2's rain_betwixt vs Dawn357x (2-1, Apr 11) for a replay test."""
    require_separate_db()
    conn.execute("UPDATE players SET uuid = ?, mc_name = ?, display_name = ? WHERE seed = 16",
                 ("93480920473541999c94b7dcd4075565", "rain_betwixt", "rain"))
    conn.execute("UPDATE players SET uuid = ?, mc_name = ?, display_name = ? WHERE seed = 17",
                 ("a321dc9a6c004adab3434379a72daba3", "Dawn357x", "dawn"))
    conn.execute("UPDATE matches SET scheduled_at = '2026-04-11T19:45:00Z' WHERE number = 1")
    print("Match 1 is now rain vs dawn at 2026-04-11 19:45 UTC.")
    print("Start the server with FAKE_NOW=2026-04-11T20:45:00Z and MCSR_SEASON=10 to replay it.")


def main():
    parser = argparse.ArgumentParser(prog="python -m app.manage")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show every match, its score and recorded games").set_defaults(fn=cmd_list)

    p = sub.add_parser("set-time", help="set a match's start time (UTC), or 'none'")
    p.add_argument("match", type=int)
    p.add_argument("time", help="e.g. 2026-10-24T17:00Z")
    p.set_defaults(fn=cmd_set_time)

    p = sub.add_parser("set-winner", help="force a match winner by seed, or 'none' to go back to automatic")
    p.add_argument("match", type=int)
    p.add_argument("seed")
    p.add_argument("--forfeit", action="store_true", help="mark it as a forfeit/no-show")
    p.set_defaults(fn=cmd_set_winner)

    p = sub.add_parser("set-score", help="force a score like 2-1 (slot 1 first), or 'none' to go back to automatic")
    p.add_argument("match", type=int)
    p.add_argument("score")
    p.set_defaults(fn=cmd_set_score)

    p = sub.add_parser("exclude-game", help="ignore a recorded game (crash, remake, friendly)")
    p.add_argument("game", type=int)
    p.set_defaults(fn=cmd_exclude_game)

    p = sub.add_parser("include-game", help="undo exclude-game")
    p.add_argument("game", type=int)
    p.set_defaults(fn=cmd_include_game)

    sub.add_parser("demo-go2", help="set up the Girloffs 2 replay test (use a separate DB_PATH!)").set_defaults(fn=cmd_demo_go2)
    sub.add_parser("demo-design", help="fake mid-tournament results for designing (use a separate DB_PATH!)").set_defaults(fn=cmd_demo_design)

    args = parser.parse_args()
    print(f"database: {Path(config.DB_PATH).resolve()}", flush=True)
    with closing(db.connect()) as conn:
        db.init(conn)
        args.fn(conn, args)
        conn.commit()


if __name__ == "__main__":
    main()
