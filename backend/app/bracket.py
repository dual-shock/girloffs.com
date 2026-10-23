"""Builds the full bracket from raw data. Nothing here writes anything: the bracket is
recomputed from players + matches + games + overrides every time, so fixing any input
(excluding a game, overriding a winner) automatically fixes everything after it."""

from datetime import datetime, timedelta

# Matches before 06:00 UTC count as the previous day's session (Saturday's 00:30 match).
DAY_CUTOFF = timedelta(hours=6)


def parse_source(source):
    kind, number = source.split(":")
    return kind, int(number)


def resolve(source, seeds, results):
    """Turn "seed:16" / "winner:9" / "loser:19" into a seed number, or None if not known yet."""
    kind, n = parse_source(source)
    if kind == "seed":
        return n if n in seeds else None
    winner, loser = results.get(n, (None, None))
    return winner if kind == "winner" else loser


def next_matches(matches):
    """match number -> number of the match its winner moves on to"""
    nxt = {}
    for m in matches:
        for source in (m["slot1"], m["slot2"]):
            kind, n = parse_source(source)
            if kind == "winner":
                nxt[n] = m["number"]
    return nxt


def derive_state(players, matches, games, now):
    seeds = {p["seed"] for p in players}
    seed_by_uuid = {p["uuid"]: p["seed"] for p in players if p["uuid"]}
    nxt = next_matches(matches)
    games_by_match = {}
    for g in games:
        games_by_match.setdefault(g["match_number"], []).append(g)

    results = {}  # match number -> (winner seed, loser seed)
    out = []
    # Every winner/loser reference points to a lower match number, so number order works.
    for m in sorted(matches, key=lambda m: m["number"]):
        sources = [m["slot1"], m["slot2"]]
        pair = [resolve(s, seeds, results) for s in sources]
        known = None not in pair

        # A game only counts if it was played between exactly the two players now in this match.
        valid = [
            g for g in games_by_match.get(m["number"], [])
            if known and not g["excluded"]
            and {seed_by_uuid.get(g["player1_uuid"]), seed_by_uuid.get(g["player2_uuid"])} == set(pair)
        ]

        score = [sum(1 for g in valid if seed_by_uuid.get(g["winner_uuid"]) == s) for s in pair]
        if m["score_override"]:
            score = [int(x) for x in m["score_override"].split("-")]

        winner = None
        if known:
            if m["winner_override"] in pair:
                winner = m["winner_override"]
            else:
                wins_needed = m["best_of"] // 2 + 1
                for s, wins in zip(pair, score):
                    if wins >= wins_needed:
                        winner = s
        loser = None
        if winner is not None:
            loser = pair[1] if winner == pair[0] else pair[0]
        results[m["number"]] = (winner, loser)

        start = datetime.fromisoformat(m["scheduled_at"]) if m["scheduled_at"] else None
        if winner is not None:
            status = "finished"
        elif valid or (start and now >= start):
            status = "live"
        else:
            status = "upcoming"

        out.append({
            "number": m["number"],
            "round": m["round"],
            "position": m["position"],
            "third_place": bool(m["third_place"]),
            "best_of": m["best_of"],
            "scheduled_at": m["scheduled_at"],
            "day": (start - DAY_CUTOFF).date().isoformat() if start else None,
            "sources": sources,
            "players": pair,
            "score": score,
            "winner": winner,
            "loser": loser,
            "status": status,
            "forfeit": bool(m["forfeit"]),
            "next": nxt.get(m["number"]),
            "games": [
                {
                    "id": g["mcsr_id"],
                    "winner": seed_by_uuid.get(g["winner_uuid"]),
                    "duration_ms": g["duration_ms"],
                    "played_at": g["played_at"],
                }
                for g in valid
            ],
        })

    out.sort(key=lambda m: (m["third_place"], m["round"], m["position"]))
    return {
        "updated_at": now.isoformat(),
        "players": [
            {k: p[k] for k in ("seed", "uuid", "mc_name", "display_name", "pronouns", "twitch")}
            for p in players
        ],
        "matches": out,
    }
