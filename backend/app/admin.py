"""Admin panel: one page plus a small JSON API under /admin. Every route requires a valid Cloudflare Access
login (see access.py); every change goes through edits.py and lands in the audit log."""

from contextlib import closing
from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from . import config, db, edits, mcsr, poller
from .access import admin_email
from .bracket import derive_state

PAGE_DIR = Path(__file__).parent / "admin"
PAGE_FILES = {"admin.js", "admin.css"}
NO_STORE = {"Cache-Control": "no-store"}
PAGE_HEADERS = {
    **NO_STORE,
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_email)])


def run(fn, *args):
    try:
        return fn(*args)
    except edits.EditError as e:
        raise HTTPException(400, str(e))


@router.get("")
def page():
    return FileResponse(PAGE_DIR / "index.html", headers=PAGE_HEADERS)


@router.get("/api/state")
def admin_state(email: str = Depends(admin_email)):
    with closing(db.connect()) as conn:
        players, matches, games = db.load(conn)
        audit = [dict(r) for r in conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")]
    return JSONResponse({
        "email": email,
        "poller": poller.status,
        "state": derive_state(players, matches, games, config.now()),
        "matches": matches,
        "games": games,
        "audit": audit,
    }, headers=NO_STORE)


@router.post("/api/matches/{number}")
def edit_match(number: int, changes: dict = Body(...), email: str = Depends(admin_email)):
    with closing(db.connect()) as conn:
        return {"changed": run(edits.edit_match, conn, number, changes, email)}


@router.post("/api/games/{mcsr_id}")
def edit_game(mcsr_id: int, changes: dict = Body(...), email: str = Depends(admin_email)):
    with closing(db.connect()) as conn:
        return {"changed": run(edits.set_game_excluded, conn, mcsr_id, changes.get("excluded"), email)}


@router.post("/api/players/{seed}")
async def edit_player(seed: int, changes: dict = Body(...), email: str = Depends(admin_email)):
    if "uuid" in changes:
        raise HTTPException(400, "the UUID is looked up from the Minecraft name")
    with closing(db.connect()) as conn:
        row = conn.execute("SELECT mc_name FROM players WHERE seed = ?", (seed,)).fetchone()
    name = changes.get("mc_name")
    if row and name is not None and name != row["mc_name"]:
        run(edits.PLAYER_FIELDS["mc_name"], None, name)  # validate before it goes into a URL
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                found = await mcsr.lookup_user(client, name)
        except (mcsr.RateLimited, httpx.HTTPError):
            raise HTTPException(503, "couldn't reach MCSR to look up that name, try again in a minute")
        if not found:
            raise HTTPException(400, f"MCSR doesn't know a player called {name!r}")
        changes = {**changes, "uuid": found[0], "mc_name": found[1]}
    with closing(db.connect()) as conn:
        return {"changed": run(edits.edit_player, conn, seed, changes, email)}


@router.get("/{name}")
def page_file(name: str):
    if name not in PAGE_FILES:
        raise HTTPException(404)
    return FileResponse(PAGE_DIR / name, headers=PAGE_HEADERS)
