from app import event
from app.bracket import parse_source


def test_every_seed_appears_once():
    seeds = [parse_source(s)[1] for m in event.STRUCTURE for s in m[3:5] if s.startswith("seed:")]
    assert sorted(seeds) == list(range(1, 23))


def test_references_point_to_earlier_matches():
    numbers = {m[0] for m in event.STRUCTURE}
    assert numbers == set(range(1, 23))
    for m in event.STRUCTURE:
        for s in m[3:5]:
            kind, n = parse_source(s)
            if kind != "seed":
                assert n in numbers and n < m[0]


def test_each_result_is_used_once():
    refs = [s for m in event.STRUCTURE for s in m[3:5] if not s.startswith("seed:")]
    assert len(refs) == len(set(refs))


def test_every_match_is_scheduled_after_what_it_depends_on():
    assert set(event.SCHEDULE) == {m[0] for m in event.STRUCTURE}
    for m in event.STRUCTURE:
        for s in m[3:5]:
            kind, n = parse_source(s)
            if kind != "seed":
                assert event.SCHEDULE[n] < event.SCHEDULE[m[0]], f"match {m[0]} is before match {n}"


def test_players_are_unique():
    assert [p[0] for p in event.PLAYERS] == list(range(1, 23))
    uuids = [p[1] for p in event.PLAYERS]
    assert len(set(uuids)) == 22 and all(len(u) == 32 for u in uuids)
