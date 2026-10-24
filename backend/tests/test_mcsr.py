import asyncio

import httpx

from app import mcsr, poller
from conftest import DAWN, OXIDIOT, RAIN, WAGASUNER, at, fixture, match, set_players, state


def epoch(iso):
    return int(at(iso).timestamp())


def test_select_games_girloffs2_round1():
    # Girloffs 2 match 5: rain_betwixt vs Dawn357x, scheduled 19:45, rain won 2-1
    games = mcsr.select_games(fixture("rain_vs_dawn_s10"), RAIN, DAWN, epoch("2026-04-11T19:30:00Z"))
    assert len(games) == 3
    assert sum(g["winner_uuid"] == RAIN for g in games) == 2
    assert sum(g["winner_uuid"] == DAWN for g in games) == 1


def test_select_games_skips_ranked_and_old_games():
    # Bronze final: 6 private games (incl. one draw) + 2 older ranked games that must be ignored
    games = mcsr.select_games(fixture("oxidiot_vs_wagasuner_s10"), OXIDIOT, WAGASUNER, epoch("2026-04-19T18:05:00Z"))
    assert len(games) == 6
    assert [g["winner_uuid"] for g in games].count(None) == 1
    assert len(mcsr.select_games(fixture("oxidiot_vs_wagasuner_s10"), OXIDIOT, WAGASUNER, epoch("2026-04-19T19:00:00Z"))) == 3


def test_select_games_allows_room_host_in_players():
    # Girloffs 3 rooms list the host (ponyashyc) as a third player
    raw = [{"id": 1, "type": 3, "date": 100, "players": [{"uuid": "host"}, {"uuid": "a"}, {"uuid": "b"}],
            "result": {"uuid": "a", "time": 1000}, "forfeited": False, "decayed": False}]
    assert [g["winner_uuid"] for g in mcsr.select_games(raw, "a", "b", 0)] == ["a"]


def fake_client(name, calls):
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"status": "success", "data": fixture(name)})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def replay(conn, fixture_name, uuid1, name1, uuid2, name2, scheduled, now, best_of=3):
    """Put two Girloffs 2 players into match 1 and run the poller once against the saved API response."""
    set_players(conn, 16, uuid1, name1)
    set_players(conn, 17, uuid2, name2)
    conn.execute("UPDATE matches SET scheduled_at = ?, best_of = ? WHERE number = 1", (scheduled, best_of))
    calls = []

    async def go():
        async with fake_client(fixture_name, calls) as client:
            return await poller.poll_once(conn, client, at(now))

    return asyncio.run(go()), calls


def test_poller_replays_a_bo3(conn):
    new, calls = replay(conn, "rain_vs_dawn_s10", RAIN, "rain", DAWN, "dawn", "2026-04-11T19:45:00Z", "2026-04-11T20:45:00Z")
    assert new == 3 and len(calls) == 1
    st = state(conn, now="2026-04-11T20:45:00Z")
    assert match(st, 1)["score"] == [2, 1] and match(st, 1)["winner"] == 16
    assert match(st, 9)["players"] == [1, 16]


def test_poller_replays_a_bo5_with_a_draw(conn):
    new, _ = replay(conn, "oxidiot_vs_wagasuner_s10", OXIDIOT, "oxidiot", WAGASUNER, "wagasuner",
                    "2026-04-19T18:20:00Z", "2026-04-19T19:30:00Z", best_of=5)
    assert new == 6
    m1 = match(state(conn, now="2026-04-19T19:30:00Z"), 1)
    assert m1["score"] == [2, 3] and m1["winner"] == 17


def test_poller_does_not_record_twice(conn):
    replay(conn, "rain_vs_dawn_s10", RAIN, "rain", DAWN, "dawn", "2026-04-11T19:45:00Z", "2026-04-11T20:45:00Z")
    new, calls = replay(conn, "rain_vs_dawn_s10", RAIN, "rain", DAWN, "dawn", "2026-04-11T19:45:00Z", "2026-04-11T20:45:00Z")
    assert new == 0 and calls == []  # match 1 is decided, so it isn't even asked about again


def test_poller_ignores_matches_outside_their_time_window(conn):
    _, calls = replay(conn, "rain_vs_dawn_s10", RAIN, "rain", DAWN, "dawn", "2026-04-11T19:45:00Z", "2026-04-11T19:00:00Z")
    assert calls == []
