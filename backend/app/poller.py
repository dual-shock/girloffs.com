import asyncio
import logging
from contextlib import closing
from datetime import datetime, timedelta, timezone

import httpx

from . import config, db, mcsr
from .bracket import derive_state

log = logging.getLogger("poller")

EARLY = timedelta(minutes=15)  # start looking for games this long before the scheduled time
LATE = timedelta(hours=4)      # give up looking this long after it

status = {"last_ok": None, "last_error": None}


def active_matches(state, now):
    """Matches that could be getting played right now: both players known, no winner yet, inside the time window."""
    for m in state["matches"]:
        if m["winner"] is not None or None in m["players"] or not m["scheduled_at"]:
            continue
        start = datetime.fromisoformat(m["scheduled_at"])
        if start - EARLY <= now <= start + LATE:
            yield m, start


async def poll_once(conn, client, now):
    players, matches, games = db.load(conn)
    uuid_by_seed = {p["seed"]: p["uuid"] for p in players}
    new = 0
    for m, start in active_matches(derive_state(players, matches, games, now), now):
        uuid1, uuid2 = (uuid_by_seed.get(s) for s in m["players"])
        if not uuid1 or not uuid2:
            continue
        raw = await mcsr.versus_matches(client, uuid1, uuid2, config.MCSR_SEASON)
        found = mcsr.select_games(raw, uuid1, uuid2, int((start - EARLY).timestamp()))
        added = db.insert_games(conn, m["number"], found)
        if added:
            log.info("match %s: %d new game(s)", m["number"], added)
        new += added
    return new


async def run():
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            delay = config.POLL_SECONDS
            try:
                with closing(db.connect()) as conn:
                    await poll_once(conn, client, config.now())
                status["last_ok"] = datetime.now(timezone.utc).isoformat()
                status["last_error"] = None
            except mcsr.RateLimited:
                log.warning("MCSR rate limit hit, waiting 60s")
                status["last_error"] = "rate limited"
                delay = 60
            except Exception as e:
                log.exception("poll failed")
                status["last_error"] = repr(e)
            await asyncio.sleep(delay)
