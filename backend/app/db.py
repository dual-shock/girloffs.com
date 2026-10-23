import sqlite3
from pathlib import Path

from . import config, event

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    seed INTEGER PRIMARY KEY,
    uuid TEXT UNIQUE,
    mc_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    pronouns TEXT NOT NULL DEFAULT '',
    twitch TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS matches (
    number INTEGER PRIMARY KEY,
    round INTEGER NOT NULL,
    position INTEGER NOT NULL,
    slot1 TEXT NOT NULL,
    slot2 TEXT NOT NULL,
    best_of INTEGER NOT NULL,
    third_place INTEGER NOT NULL DEFAULT 0,
    scheduled_at TEXT,
    winner_override INTEGER,
    score_override TEXT,
    forfeit INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS games (
    mcsr_id INTEGER PRIMARY KEY,
    match_number INTEGER NOT NULL,
    played_at INTEGER NOT NULL,
    player1_uuid TEXT NOT NULL,
    player2_uuid TEXT NOT NULL,
    winner_uuid TEXT,
    duration_ms INTEGER,
    forfeited INTEGER NOT NULL DEFAULT 0,
    excluded INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    email TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL
);
"""


def connect(path=None):
    path = path or config.DB_PATH
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init(conn):
    """Create tables and fill them from event.py if they are empty."""
    conn.executescript(SCHEMA)
    if not conn.execute("SELECT 1 FROM players").fetchone():
        conn.executemany("INSERT INTO players VALUES (?, ?, ?, ?, ?, ?)", event.PLAYERS)
    if not conn.execute("SELECT 1 FROM matches").fetchone():
        conn.executemany(
            "INSERT INTO matches (number, round, position, slot1, slot2, best_of, third_place, scheduled_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(*m, event.SCHEDULE.get(m[0])) for m in event.STRUCTURE],
        )
    conn.commit()


def load(conn):
    players = [dict(r) for r in conn.execute("SELECT * FROM players ORDER BY seed")]
    matches = [dict(r) for r in conn.execute("SELECT * FROM matches ORDER BY number")]
    games = [dict(r) for r in conn.execute("SELECT * FROM games ORDER BY played_at")]
    return players, matches, games


def insert_games(conn, match_number, games):
    """Insert games not seen before. Returns how many were new."""
    if not games:
        return 0
    cur = conn.executemany(
        "INSERT OR IGNORE INTO games (mcsr_id, match_number, played_at, player1_uuid, player2_uuid,"
        " winner_uuid, duration_ms, forfeited)"
        " VALUES (:mcsr_id, :match_number, :played_at, :player1_uuid, :player2_uuid,"
        " :winner_uuid, :duration_ms, :forfeited)",
        [{**g, "match_number": match_number} for g in games],
    )
    conn.commit()
    return cur.rowcount
