from conftest import add_game, match, state


def test_initial_bracket(conn):
    st = state(conn)
    assert len(st["matches"]) == 22 and len(st["players"]) == 22
    m1 = match(st, 1)
    assert m1["players"] == [16, 17] and m1["score"] == [0, 0] and m1["status"] == "upcoming"
    assert m1["next"] == 9
    assert match(st, 9)["players"] == [1, None]
    assert match(st, 7)["players"] == [8, 9]
    assert match(st, 22)["players"] == [None, None] and match(st, 22)["third_place"]


def test_winner_moves_on(conn):
    add_game(conn, 1, 16, 17, 16)
    assert match(state(conn), 1)["winner"] is None  # 1 win isn't enough in a Bo3
    add_game(conn, 1, 16, 17, 16)
    st = state(conn)
    assert match(st, 1)["winner"] == 16 and match(st, 1)["loser"] == 17
    assert match(st, 1)["status"] == "finished"
    assert match(st, 9)["players"] == [1, 16]


def test_draw_does_not_count(conn):
    add_game(conn, 1, 16, 17, None)
    add_game(conn, 1, 16, 17, 17)
    m1 = match(state(conn), 1)
    assert m1["score"] == [0, 1] and m1["winner"] is None and m1["status"] == "live"


def test_excluded_game_does_not_count(conn):
    add_game(conn, 1, 16, 17, 16)
    add_game(conn, 1, 16, 17, 16, excluded=1)
    assert match(state(conn), 1)["score"] == [1, 0]


def test_correction_propagates(conn):
    add_game(conn, 1, 16, 17, 16)
    add_game(conn, 1, 16, 17, 16)
    add_game(conn, 9, 1, 16, 16)
    assert match(state(conn), 9)["score"] == [0, 1]

    # Admin decides 17 actually won match 1: 17 moves on, and the 1-vs-16 game in match 9 no longer counts.
    conn.execute("UPDATE matches SET winner_override = 17 WHERE number = 1")
    st = state(conn)
    assert match(st, 1)["winner"] == 17
    assert match(st, 9)["players"] == [1, 17] and match(st, 9)["score"] == [0, 0]


def test_score_override(conn):
    conn.execute("UPDATE matches SET score_override = '2-0' WHERE number = 7")
    st = state(conn)
    assert match(st, 7)["score"] == [2, 0] and match(st, 7)["winner"] == 8
    assert match(st, 15)["players"] == [None, 8]


def test_stale_winner_override_is_ignored(conn):
    conn.execute("UPDATE matches SET winner_override = 5 WHERE number = 1")  # seed 5 isn't in match 1
    assert match(state(conn), 1)["winner"] is None


def test_override_needs_both_players_known(conn):
    conn.execute("UPDATE matches SET winner_override = 1 WHERE number = 9")  # match 1 not played yet
    assert match(state(conn), 9)["winner"] is None


def test_losers_go_to_third_place(conn):
    winners = [(1, 16), (2, 13), (3, 12), (4, 15), (5, 14), (6, 11),
               (9, 1), (7, 8), (10, 4), (11, 5), (12, 2), (8, 7), (13, 3), (14, 6),
               (15, 1), (16, 4), (17, 2), (18, 3), (19, 1), (20, 3)]
    for number, seed in winners:
        conn.execute("UPDATE matches SET winner_override = ? WHERE number = ?", (seed, number))
    st = state(conn)
    assert match(st, 19)["players"] == [1, 4] and match(st, 20)["players"] == [2, 3]
    assert match(st, 21)["players"] == [1, 3]
    assert match(st, 22)["players"] == [4, 2]


def test_final_is_best_of_five(conn):
    assert match(state(conn), 21)["best_of"] == 5


def test_status_and_days(conn):
    st = state(conn, now="2026-10-24T17:05:00Z")
    assert match(st, 1)["status"] == "live"
    assert match(st, 2)["status"] == "upcoming"
    assert match(st, 1)["day"] == "2026-10-24"
    assert match(st, 8)["day"] == "2026-10-24"  # 00:30 UTC Sunday still belongs to Saturday's session
    assert match(st, 9)["day"] == "2026-10-25"
