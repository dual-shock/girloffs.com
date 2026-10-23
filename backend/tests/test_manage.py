import pytest

from app import config, manage

from conftest import match, state


def test_demo_commands_refuse_the_real_database(conn, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", "data/girloffs.db")
    for cmd in (manage.cmd_demo_design, manage.cmd_demo_go2):
        with pytest.raises(SystemExit):
            cmd(conn, None)


def test_demo_design_covers_every_match_look(conn, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", "data/design.db")
    manage.cmd_demo_design(conn, None)
    manage.cmd_demo_design(conn, None)  # running it twice changes nothing
    st = state(conn)
    looks = {n: (match(st, n)["status"], match(st, n)["score"]) for n in (1, 5, 6, 8, 12, 13, 16, 17)}
    assert looks[1] == ("finished", [2, 1])
    assert match(st, 5)["forfeit"] and looks[5][0] == "finished"
    assert looks[6] == ("finished", [1, 2])           # with a draw in between
    assert looks[8] == ("upcoming", [0, 0]) and None not in match(st, 8)["players"]
    assert looks[12] == ("live", [1, 0])
    assert looks[13] == ("live", [1, 1])
    assert looks[16][0] == "upcoming" and None not in match(st, 16)["players"]
    assert match(st, 17)["players"] == [None, None]
    assert match(st, 19)["players"][0] is not None and match(st, 19)["players"][1] is None
