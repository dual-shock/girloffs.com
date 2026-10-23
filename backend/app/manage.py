"""Command line tool for looking at and correcting the bracket until the admin panel exists.

Run from the backend folder, e.g.:  python -m app.manage list
"""

import argparse
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from . import config, db
from .bracket import derive_state


def update(conn, sql, params, what):
    """Run an UPDATE and stop with an error if it didn't change anything (wrong ID or wrong database)."""
    if conn.execute(sql, params).rowcount == 0:
        sys.exit(f"ERROR: {what} not found in this database. Nothing was changed.")
    print(f"ok: {what} updated")


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


def cmd_set_time(conn, args):
    value = None if args.time == "none" else datetime.fromisoformat(args.time).strftime("%Y-%m-%dT%H:%M:%SZ")
    update(conn, "UPDATE matches SET scheduled_at = ? WHERE number = ?", (value, args.match), f"match {args.match}")


def cmd_set_winner(conn, args):
    seed = None if args.seed == "none" else int(args.seed)
    update(conn, "UPDATE matches SET winner_override = ?, forfeit = ? WHERE number = ?",
           (seed, int(args.forfeit), args.match), f"match {args.match}")


def cmd_set_score(conn, args):
    value = None if args.score == "none" else args.score
    update(conn, "UPDATE matches SET score_override = ? WHERE number = ?", (value, args.match), f"match {args.match}")


def cmd_exclude_game(conn, args):
    update(conn, "UPDATE games SET excluded = 1 WHERE mcsr_id = ?", (args.game,), f"game {args.game}")


def cmd_include_game(conn, args):
    update(conn, "UPDATE games SET excluded = 0 WHERE mcsr_id = ?", (args.game,), f"game {args.game}")


def cmd_demo_go2(conn, args):
    """Turn match 1 into Girloffs 2's rain_betwixt vs Dawn357x (2-1, Apr 11) for a replay test."""
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

    args = parser.parse_args()
    print(f"database: {Path(config.DB_PATH).resolve()}", flush=True)
    with closing(db.connect()) as conn:
        db.init(conn)
        args.fn(conn, args)
        conn.commit()


if __name__ == "__main__":
    main()
