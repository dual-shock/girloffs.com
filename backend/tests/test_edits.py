import pytest

from app import edits

from conftest import add_game, match, state


def test_times_are_stored_as_utc(conn):
    edits.edit_match(conn, 1, {"scheduled_at": "2026-10-24 18:00"}, "t")
    assert match(state(conn), 1)["scheduled_at"] == "2026-10-24T18:00:00Z"
    edits.edit_match(conn, 1, {"scheduled_at": "2026-10-24T19:00+02:00"}, "t")
    assert match(state(conn), 1)["scheduled_at"] == "2026-10-24T17:00:00Z"
    edits.edit_match(conn, 1, {"scheduled_at": None}, "t")
    assert match(state(conn), 1)["scheduled_at"] is None


def test_no_op_changes_are_not_logged(conn):
    assert edits.edit_match(conn, 1, {"best_of": 3}, "t") == {}
    assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0


def test_every_change_is_logged(conn):
    game = add_game(conn, 1, 16, 17, 16)
    edits.set_game_excluded(conn, game, True, "a@example.com")
    edits.edit_match(conn, 1, {"score_override": "2-0"}, "b@example.com")
    rows = conn.execute("SELECT email, action, details FROM audit_log ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [
        ("a@example.com", f"game {game}", '{"excluded": [0, 1]}'),
        ("b@example.com", "match 1", '{"score_override": [null, "2-0"]}'),
    ]


def test_cli_style_string_values_work(conn):
    edits.edit_match(conn, 5, {"winner_override": "14", "forfeit": False}, "cli")
    assert conn.execute("SELECT winner_override FROM matches WHERE number = 5").fetchone()[0] == 14


@pytest.mark.parametrize("field,value", [("display_name", ""), ("display_name", "x" * 40), ("twitch", "a b"),
                                         ("mc_name", "a/b"), ("uuid", "not-a-uuid"), ("pronouns", 5)])
def test_player_values_are_checked(conn, field, value):
    with pytest.raises(edits.EditError):
        edits.edit_player(conn, 1, {field: value}, "t")
