"""Every change to matches, games and players goes through here, from the CLI and the admin panel alike:
the same checks apply everywhere, and every change is written to the audit log."""

import json
import re
from datetime import datetime, timezone


class EditError(ValueError):
    """A refused change. The message is shown to whoever tried it."""


def parse_time(conn, value):
    if value in (None, ""):
        return None
    try:
        t = datetime.fromisoformat(str(value).strip().replace(" ", "T"))
    except ValueError:
        raise EditError(f"not a time: {value!r} (use e.g. 2026-10-24 17:00, in UTC)")
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_seed(conn, value):
    if value in (None, ""):
        return None
    try:
        seed = int(value) if not isinstance(value, bool) else None
    except ValueError:
        seed = None
    if seed is None or not conn.execute("SELECT 1 FROM players WHERE seed = ?", (seed,)).fetchone():
        raise EditError(f"no player with seed {value!r}")
    return seed


def parse_score(conn, value):
    if value in (None, ""):
        return None
    if not re.fullmatch(r"\d{1,2}-\d{1,2}", str(value)):
        raise EditError(f"score must look like 2-1, got {value!r}")
    return value


def parse_best_of(conn, value):
    if value not in (1, 3, 5, 7):
        raise EditError(f"best of must be 1, 3, 5 or 7, got {value!r}")
    return value


def parse_flag(conn, value):
    if not isinstance(value, bool):
        raise EditError(f"expected true or false, got {value!r}")
    return int(value)


def text(pattern, what):
    def parse(conn, value):
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise EditError(f"invalid {what}: {value!r}")
        return value
    return parse


MATCH_FIELDS = {
    "scheduled_at": parse_time,
    "best_of": parse_best_of,
    "winner_override": parse_seed,
    "forfeit": parse_flag,
    "score_override": parse_score,
}

PLAYER_FIELDS = {
    "display_name": text(r"\S.{0,31}", "display name"),
    "pronouns": text(r".{0,32}", "pronouns"),
    "twitch": text(r"[A-Za-z0-9_]{0,25}", "twitch name"),
    "mc_name": text(r"[A-Za-z0-9_]{1,16}", "Minecraft name"),
    "uuid": text(r"[0-9a-f]{32}", "UUID"),
}


def audit(conn, email, action, details):
    conn.execute(
        "INSERT INTO audit_log (at, email, action, details) VALUES (?, ?, ?, ?)",
        (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), email, action, json.dumps(details)),
    )


def _apply(conn, table, key, key_value, fields, changes, email, action):
    row = conn.execute(f"SELECT * FROM {table} WHERE {key} = ?", (key_value,)).fetchone()
    if not row:
        raise EditError(f"{action} not found")
    new = {}
    for field, value in changes.items():
        if field not in fields:
            raise EditError(f"unknown field {field!r}")
        new[field] = fields[field](conn, value)
    diff = {f: [row[f], v] for f, v in new.items() if row[f] != v}
    if diff:
        # field names come from the whitelists above, values are parameters
        sets = ", ".join(f"{f} = ?" for f in diff)
        try:
            conn.execute(f"UPDATE {table} SET {sets} WHERE {key} = ?", (*(v for _, v in diff.values()), key_value))
        except Exception as e:
            conn.rollback()
            raise EditError(f"{action}: {e}")
        audit(conn, email, action, diff)
        conn.commit()
    return diff


def edit_match(conn, number, changes, email):
    return _apply(conn, "matches", "number", number, MATCH_FIELDS, changes, email, f"match {number}")


def edit_player(conn, seed, changes, email):
    if "uuid" in changes:
        other = conn.execute("SELECT seed FROM players WHERE uuid = ? AND seed != ?", (changes["uuid"], seed)).fetchone()
        if other:
            raise EditError(f"that Minecraft account is already seed {other['seed']}")
    return _apply(conn, "players", "seed", seed, PLAYER_FIELDS, changes, email, f"player {seed}")


def set_game_excluded(conn, mcsr_id, excluded, email):
    return _apply(conn, "games", "mcsr_id", mcsr_id, {"excluded": parse_flag}, {"excluded": excluded}, email,
                  f"game {mcsr_id}")
