# girloffs.com

Website for Girloffs, an MCSR (Minecraft speedrun) tournament. Girloffs 3 runs Sat Oct 24 – Sun Oct 25 2026 (all times UTC): 22 players, single elimination, Bo3 everywhere except the grand final (Bo5), plus a 3rd place match.

## Layout
- `frontend/`: the public site. Vanilla JS ES modules, no build step, no framework. One file per tab: `bracket.js`, `schedule.js`, `players.js`; `nav.js` = tab switching; `main.js` = fetches `/api/state` every 10s (plus a localStorage copy for an instant first render, also when the API is down) and re-renders when it changed. Styling in `styles/` is unchanged from Girloffs 2 (the redesign is a later phase).
- `backend/app/`: Python FastAPI + stdlib `sqlite3`.
  - `event.py`: seed data (bracket structure, schedule, players). Only used to fill an empty DB; after that the DB is the source of truth.
  - `bracket.py`: `derive_state()`, a pure function that builds the whole bracket from players + matches + games + overrides.
  - `mcsr.py` + `poller.py`: every 10s, for matches inside their time window (start −15min to +4h), fetch `/users/{uuid1}/versus/{uuid2}/matches` and store new private-room games.
  - `main.py`: `GET /api/state` (always sends `Cache-Control: public, max-age=5, stale-if-error=86400` and `Access-Control-Allow-Origin: *`, because Cloudflare's cached copy is shared by everyone), `GET /health`; also serves `frontend/` when `SERVE_FRONTEND=1` (local only).
  - `edits.py`: the only place that changes matches/games/players. Validates every value, writes `audit_log`. Used by both the CLI and the admin panel.
  - `access.py`: admin login. It verifies Cloudflare Access's `Cf-Access-Jwt-Assertion` (PyJWT, RS256, `aud` = `ACCESS_AUD`, `iss` = `https://ACCESS_TEAM_DOMAIN`), with keys fetched through egress. `DEV_ADMIN_EMAIL` is for local use only and is ignored once either Access variable is set. Non-GET requests also need `Origin` to match `Host`.
  - `admin.py` + `admin/` (index.html, admin.js, admin.css): the panel at `/admin` plus its JSON API at `/admin/api/*`. All routes sit behind `access.admin_email`. The page has a strict CSP, so no inline scripts or styles.
  - `manage.py`: CLI for the same corrections (it goes through `edits.py`, and its audit entries show up as `cli`).
  - `config.py`: env vars (`DB_PATH`, `POLL_ENABLED`, `POLL_SECONDS`, `MCSR_SEASON`, `FAKE_NOW`, `SERVE_FRONTEND`). httpx also picks up `HTTPS_PROXY` (set in compose).
- `egress/`: tinyproxy image, the app's only way out to the internet. `allowlist` = hosts it may reach (one regex per line).
- `docker-compose.yml`: the production stack (app + egress + cloudflared). See Production below.
- `archive/girloffs2/bracket.json`: last event's data, kept for reference.

## Design rules (don't break these)
- **Never "move" players through the bracket.** Progression is always recomputed in `derive_state` from raw inputs. Corrections are made by changing inputs (exclude a game, set an override), never by editing a later match.
- Every change to the data goes through `edits.py` (validation + audit log). Never write UPDATEs anywhere else, because a malformed value (e.g. a score override like "2:1") would crash `derive_state` for every visitor.
- Players are identified by **seed** everywhere in the API and frontend. MCSR games are matched by **UUID**, never by name (names change).
- A game only counts for a match if its two players are exactly the two players currently in that match.
- Slots are `seed:N`, `winner:N` or `loser:N`; every reference points to a lower match number.
- Challonge is **not used** (decided: free API is capped at 500 req/month and the server has to run progression itself anyway).

## Commands (run from `backend/`, Windows venv)
- Tests (offline): `.venv/Scripts/python -m pytest`
- Real-API test: `.venv/Scripts/python -m pytest -m network`
- Run locally: `.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000` → http://localhost:8000
- Inspect/correct: `.venv/Scripts/python -m app.manage list` (also `set-time`, `set-winner`, `set-score`, `exclude-game`, `include-game`, `demo-go2`). It prints the DB path first and exits with an error if an ID matches nothing; `DB_PATH` must be set in every shell that should use a non-default DB.
- Replay test: separate `DB_PATH=data/demo.db`, run `manage demo-go2`, then start the server with `FAKE_NOW=2026-04-11T20:45:00Z MCSR_SEASON=10`.
- Docker/Unraid: see Production. The compose stack publishes no ports, so to click around locally use the venv server, not Docker. SQLite stays in the default rollback journal: WAL is avoided because Unraid's `/mnt/user` FUSE layer and SQLite WAL don't mix well.

## Production (decided 2026-10-23: Unraid origin, everything public goes through Cloudflare)
- **girloffs.com**: Cloudflare Pages project, Git-connected, production branch `girloffs3`, build output `frontend`, no build command. `API_BASE` in `main.js` points girloffs.com and `*.pages.dev` at `https://api.girloffs.com`.
- **api.girloffs.com**: Cloudflare Tunnel `girloffs` (its own tunnel, separate from the owner's existing Unraid tunnel) → `http://girloffs:8000`. Zone settings it relies on:
  - Cache Rule: `/api/state` eligible for cache; Edge TTL = origin header; Browser TTL = respect origin.
  - Zone Browser Cache TTL = "Respect Existing Headers". It was 4h, which would override `max-age=5`.
  - Always Online off. It disables stale-if-error.
  - WAF custom rule: block everything on api.girloffs.com except GET/HEAD of `/api/state` and `/health` with no query string. This stops cache-busting.
- **admin.girloffs.com**: a second route on the same tunnel to the same app. A Cloudflare Access self-hosted application covers the whole hostname (organizer emails, one-time PIN). `.env` on the server holds `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD`. `egress/allowlist` allows `*.cloudflareaccess.com` so the app can fetch the signing keys.
- **Why cached polling, not SSE**: every viewer gets identical data, so Cloudflare serves it from the edge and the home uplink only carries a few requests per Cloudflare location. SSE would hold one open connection per viewer to the home server.
- **Unraid stack** (`/mnt/user/appdata/girloffs`, Compose Manager stack `girloffs`). No published ports. `TUNNEL_TOKEN` lives in `.env` on the server (gitignored and dockerignored).
  - `girloffs`: runs as 99:100, read-only, `cap_drop: ALL`, only on the `internal: true` network (no LAN, no internet).
  - `girloffs-egress` (tinyproxy): the app's only way out; only allows `egress/allowlist`.
  - `girloffs-cloudflared`: carries visitors in.
  - Verified 2026-10-23: from the app container, example.com, the LAN, the router and 1.1.1.1 are all unreachable; MCSR via the proxy works.
- Code reaches the server as a tar on `Z:\REPO_EXPORTS` (= `/mnt/user/drive/REPO_EXPORTS` on the server), the owner's transfer share (see the NIXIDIGITAL repo next to this one). The owner runs all server commands.
- The owner's NIXIDIGITAL export script can dump `docker inspect` env vars, so `TUNNEL_TOKEN` must stay redacted in anything committed there.

## MCSR Ranked API facts
- Docs: https://docs.mcsrranked.com/ (full spec at `/openapi.yaml`). Base `https://api.mcsrranked.com`, 5s cache, 500 requests / 10 min per IP.
- Match types: 1 casual, 2 ranked, 3 private room, 4 event mode. `result.uuid` null = draw. Versus endpoints default to the current season (`season=` for older).
- Girloffs 2 games are reusable fixtures (season 10), e.g. rain_betwixt vs Dawn357x on 2026-04-11 (2–1).
- `mc-heads.net/avatar/<uuid>` returns Steve for some players; use the name.

## Dependencies (security policy)
- `backend/requirements.txt` pins **every** package including transitive deps (`requirements-dev.txt` adds pytest + its deps). The venv must match the pins exactly (`pip list --format=freeze` vs the files).
- Before adding/upgrading anything: check OSV (`https://api.osv.dev/v1/query`) and the PyPI upload date. Don't adopt releases younger than ~7 days unless they're a security fix (e.g. certifi 2026.10.19 and pip 26.2.2 were adopted at 2 days old because they remove compromised emSign CAs).
- pip is pinned to 26.2.2 in the venv and the Dockerfile; base image is `python:3.13.13-slim`. Installs use `--only-binary=:all:` (wheels only, so no package build scripts run).
- The admin login packages were added 2026-10-23 (all OSV-clean): PyJWT 2.15.1, cryptography 50.0.2, cffi 2.1.1, pycparser 3.11. pycparser 3.12 was 1 day old at the time, so it was skipped.
- Other images are pinned by tag + digest:
  - `cloudflare/cloudflared:2026.10.3`: adopted at 2 days old because it carries Go 1.27.3's crypto/x509 security fixes.
  - `alpine:3.24.3`: a security release (OpenSSL, musl and zlib CVEs, eMudhra CA).
  - `egress/Dockerfile` pins `tinyproxy=1.11.3-r0`. If Alpine ships a newer -rN, a fresh build fails on purpose: check the new version, then bump.
- The owner wants control over infrastructure (venvs, Docker, installs, server setup): explain and ask before creating or changing it.

## Conventions
- Match the surrounding code: frontend uses `var`/`function` style like the original site; keep comments sparse.
- Keep changes minimal and incremental; the owner tests each phase before the next.
- `main` still deploys the old site to GitHub Pages from the repo root until girloffs.com is switched to Cloudflare Pages. After that, GitHub Pages gets disabled and `frontend/CNAME` can go. Work happens on the `girloffs3` branch.

## Roadmap
1. ~~Backend core + poller + frontend reading the API (same styling)~~ (done)
2. Deploy: Unraid origin behind Cloudflare Tunnel at `api.girloffs.com`, frontend on Cloudflare Pages, Web Analytics (in progress)
3. ~~Admin panel behind Cloudflare Access (players, match times, overrides, exclude games, audit log)~~ (built 2026-10-23; needs the Access app + `.env` on the server)
4. ~~Server-Sent Events~~ replaced by edge-cached polling (done: 10s poller, 5s edge cache, 10s browser refresh)
5. Redesign: Girloffs 3 branding, video background (webm + mp4 fallback), woff2 fonts, credits/results pages
