import asyncio
import logging
from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import admin, config, db, devreload, poller
from .bracket import derive_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Cloudflare keeps /api/state for 5s, so the server sees a few requests per Cloudflare location no matter how
# many people watch. stale-if-error: if this server is down, Cloudflare keeps serving the last state for a day.
# The CORS header is always sent (not only when the request has an Origin), because the cached copy is shared.
STATE_HEADERS = {
    "Cache-Control": "public, max-age=5, stale-if-error=86400",
    "Access-Control-Allow-Origin": "*",
}


@asynccontextmanager
async def lifespan(app):
    with closing(db.connect()) as conn:
        db.init(conn)
    task = asyncio.create_task(poller.run()) if config.POLL_ENABLED else None
    yield
    if task:
        task.cancel()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/api/state")
def state():
    with closing(db.connect()) as conn:
        return JSONResponse(derive_state(*db.load(conn), config.now()), headers=STATE_HEADERS)


@app.get("/health")
def health():
    return {"ok": True, "polling": config.POLL_ENABLED, **poller.status}


app.include_router(admin.router)

if config.DEV_RELOAD:
    app.include_router(devreload.router)

    @app.middleware("http")
    async def always_fresh(request, call_next):
        # local design work: the browser must never reuse an old copy of a CSS/JS file
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response


# Local testing: serve the site from the same server. Mounted last so /api and /health win.
# On the server the site lives on Cloudflare Pages, so / just leads organizers on admin.girloffs.com to the panel.
if config.SERVE_FRONTEND:
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return RedirectResponse("/admin")
