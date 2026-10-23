BASE_URL = "https://api.mcsrranked.com"
TOURNAMENT_TYPES = {3, 4}  # private room, event mode


class RateLimited(Exception):
    pass


async def versus_matches(client, uuid1, uuid2, season=None):
    """All recent games between two players (newest first). Public endpoint, no key needed."""
    params = {"count": 50}
    if season:
        params["season"] = season
    r = await client.get(f"{BASE_URL}/users/{uuid1}/versus/{uuid2}/matches", params=params)
    if r.status_code == 429:
        raise RateLimited()
    r.raise_for_status()
    body = r.json()
    if body.get("status") != "success":
        raise RuntimeError(f"MCSR error: {body.get('data')}")
    return body["data"]


async def lookup_user(client, name):
    """(uuid, current nickname) for a Minecraft name, or None if MCSR doesn't know it."""
    r = await client.get(f"{BASE_URL}/users/{name}")
    if r.status_code == 429:
        raise RateLimited()
    body = r.json()
    if body.get("status") != "success":
        return None
    return body["data"]["uuid"], body["data"]["nickname"]


def select_games(raw, uuid1, uuid2, since):
    """Keep only private-room/event games between exactly these two players, played after `since` (epoch seconds)."""
    games = []
    for m in raw:
        uuids = {p["uuid"] for p in m["players"]}
        if m["type"] not in TOURNAMENT_TYPES or uuids != {uuid1, uuid2}:
            continue
        if m["date"] < since or m.get("decayed"):
            continue
        result = m.get("result") or {}
        games.append({
            "mcsr_id": m["id"],
            "played_at": m["date"],
            "player1_uuid": uuid1,
            "player2_uuid": uuid2,
            "winner_uuid": result.get("uuid"),  # None = draw
            "duration_ms": result.get("time"),
            "forfeited": int(bool(m.get("forfeited"))),
        })
    return games
