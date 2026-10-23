import json
from datetime import datetime
from pathlib import Path

import pytest

from app import db
from app.bracket import derive_state

FIXTURES = Path(__file__).parent / "fixtures"

RAIN = "93480920473541999c94b7dcd4075565"
DAWN = "a321dc9a6c004adab3434379a72daba3"
OXIDIOT = "562a308be86c4ec09438387860e792cc"
WAGASUNER = "e1923b76cb5e42abbff7e3f0122440c8"


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init(c)
    yield c
    c.close()


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())["data"]


def at(iso):
    return datetime.fromisoformat(iso)


def state(conn, now="2026-10-24T12:00:00Z"):
    return derive_state(*db.load(conn), at(now))


def match(st, number):
    return next(m for m in st["matches"] if m["number"] == number)


def uuid_of(conn, seed):
    return conn.execute("SELECT uuid FROM players WHERE seed = ?", (seed,)).fetchone()[0]


_next_id = iter(range(1, 10_000))


def add_game(conn, match_number, seed1, seed2, winner_seed, excluded=0):
    u1, u2 = uuid_of(conn, seed1), uuid_of(conn, seed2)
    winner = uuid_of(conn, winner_seed) if winner_seed else None
    game_id = next(_next_id)
    conn.execute(
        "INSERT INTO games (mcsr_id, match_number, played_at, player1_uuid, player2_uuid, winner_uuid, excluded)"
        " VALUES (?, ?, 0, ?, ?, ?, ?)",
        (game_id, match_number, u1, u2, winner, excluded),
    )
    return game_id


def set_players(conn, seed, uuid, name):
    conn.execute("UPDATE players SET uuid = ?, mc_name = ?, display_name = ? WHERE seed = ?", (uuid, name, name, seed))
