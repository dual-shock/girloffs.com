"""Talks to the real MCSR API. Skipped by default; run with: pytest -m network"""

import asyncio

import httpx
import pytest

from app import config, poller
from conftest import DAWN, RAIN, at, match, set_players, state


@pytest.mark.network
def test_real_api_replays_girloffs2_match(conn, monkeypatch):
    monkeypatch.setattr(config, "MCSR_SEASON", "10")
    set_players(conn, 16, RAIN, "rain")
    set_players(conn, 17, DAWN, "dawn")
    conn.execute("UPDATE matches SET scheduled_at = '2026-04-11T19:45:00Z' WHERE number = 1")

    async def go():
        async with httpx.AsyncClient(timeout=10) as client:
            return await poller.poll_once(conn, client, at("2026-04-11T20:45:00Z"))

    assert asyncio.run(go()) == 3
    assert match(state(conn, now="2026-04-11T20:45:00Z"), 1)["score"] == [2, 1]
