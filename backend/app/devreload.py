"""Local design work only (DEV_RELOAD=1): tells every open browser tab when a file in frontend/ changed,
so previews update by themselves. Never enabled on the server."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from . import config

router = APIRouter()


def snapshot():
    root = Path(config.FRONTEND_DIR)
    return {p.relative_to(root).as_posix(): p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


@router.get("/dev/reload")
async def reload_events(request: Request):
    async def events():
        before = snapshot()
        while not await request.is_disconnected():
            await asyncio.sleep(0.3)
            now = snapshot()
            changed = sorted(p for p in now.keys() | before.keys() if now.get(p) != before.get(p))
            if changed:
                before = now
                yield f"data: {json.dumps(changed)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
