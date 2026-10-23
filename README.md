# girloffs.com

Tournament site for Girloffs. `frontend/` is the website, `backend/` is a small Python server that builds the bracket and pulls game results from the MCSR Ranked API. Architecture notes: `.claude/CLAUDE.md`.

## Run it on Windows (PowerShell)

One-time setup:
```powershell
cd X:\repos\girloffs.com\backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Start the server, then open http://localhost:8000:
```powershell
cd X:\repos\girloffs.com\backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
The first start creates `backend/data/girloffs.db` from `backend/app/event.py`. Delete that file to start over from scratch.

## Tests
```powershell
.venv\Scripts\python -m pytest              # offline tests, uses saved API responses
.venv\Scripts\python -m pytest -m network   # one extra test against the real MCSR API
```

## Replay test (a real Girloffs 2 match, on a separate database)
Open a **new** PowerShell window (the env vars below stay set until you close it):
```powershell
cd X:\repos\girloffs.com\backend
$env:DB_PATH = "data/demo.db"; $env:FAKE_NOW = "2026-04-11T20:45:00Z"; $env:MCSR_SEASON = "10"
.venv\Scripts\python -m app.manage demo-go2
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```
Within ~10 seconds match 1 should show rain 2–1 dawn and rain should appear in round 2 against Casual.

To run commands against the demo while the server is running, open a **second** PowerShell window and point it at the same database first:
```powershell
cd X:\repos\girloffs.com\backend
$env:DB_PATH = "data/demo.db"
.venv\Scripts\python -m app.manage exclude-game 9136496   # match 1 becomes 1-1, rain leaves round 2
.venv\Scripts\python -m app.manage include-game 9136496   # back to 2-1
```
Every command prints `database: ...` first. If it doesn't say `demo.db`, you're editing the wrong one.

## Fixing results (until the admin panel exists)
Run from `backend/` (on Unraid: prefix with `docker exec girloffs`, e.g. `docker exec girloffs python -m app.manage list`):

| Command | What it does |
|---|---|
| `python -m app.manage list` | every match, score, status and recorded game IDs |
| `python -m app.manage exclude-game 9136496` | ignore a game (crash, remake, friendly) |
| `python -m app.manage include-game 9136496` | undo that |
| `python -m app.manage set-winner 5 14` | force seed 14 as winner of match 5 |
| `python -m app.manage set-winner 5 14 --forfeit` | same, marked as forfeit/no-show |
| `python -m app.manage set-winner 5 none` | back to automatic |
| `python -m app.manage set-score 5 2-1` | force the score (slot 1 first) |
| `python -m app.manage set-score 5 none` | back to automatic |
| `python -m app.manage set-time 5 2026-10-24T23:50Z` | move a match (UTC) |

Locally, use `.venv\Scripts\python` instead of `python`.

## Production (Unraid + Cloudflare)

How a visitor gets the site:
- **girloffs.com** is Cloudflare Pages, deployed automatically from the `frontend/` folder of the `girloffs3` branch on every push.
- **api.girloffs.com** is Cloudflare in front of the app on Unraid. Cloudflare keeps `/api/state` for 5 seconds, so the server only sees a few requests per Cloudflare location no matter how many people watch. If the server is down, Cloudflare keeps serving the last state.

On Unraid the stack (`docker-compose.yml`) runs 3 containers, all with no root powers, read-only filesystems and memory limits:

| Container | What it does | Can reach |
|---|---|---|
| `girloffs` | the app (API + MCSR poller), runs as `nobody` (99:100) | only `egress` and `cloudflared`. Not your LAN, not the internet |
| `girloffs-egress` | outbound proxy (tinyproxy) | only HTTPS to the hosts in `egress/allowlist` (the MCSR API) |
| `girloffs-cloudflared` | Cloudflare Tunnel, this stack's own tunnel | Cloudflare |

No ports are published, so nothing on your LAN or router points at it. Secrets (the tunnel token) live in `.env` next to `docker-compose.yml` on the server, never in git.

### Install or update on Unraid
The stack lives in `/mnt/user/appdata/girloffs` (Compose Manager stack `girloffs`, Advanced → Stack Directory set to that path).

1. **Pack the app on Windows**, straight onto the REPO_EXPORTS share (PowerShell):
   ```powershell
   cd X:\repos\girloffs.com
   tar -czf Z:\REPO_EXPORTS\girloffs.tar.gz --exclude=backend/.venv --exclude=backend/data --exclude=backend/tests --exclude=__pycache__ --exclude=.pytest_cache docker-compose.yml .dockerignore backend frontend egress
   ```
2. **Unpack and rebuild on Unraid** (web UI → `>_` terminal):
   ```bash
   cd /mnt/user/appdata/girloffs
   tar -xzf /mnt/user/drive/REPO_EXPORTS/girloffs.tar.gz -C /mnt/user/appdata/girloffs
   rm /mnt/user/drive/REPO_EXPORTS/girloffs.tar.gz
   docker compose up -d --build
   docker compose ps    # girloffs (healthy), girloffs-egress, girloffs-cloudflared: all "Up"
   ```
   This replaces the code but never touches `data/` or `.env`. Use the terminal, not the **Compose Up** button: the button may restart the old image without rebuilding.

First time only, before `docker compose up`:
```bash
mkdir -p data && chown -R 99:100 data   # the app runs as nobody:users and must be able to write its database
nano .env                               # one line: TUNNEL_TOKEN=<token from the Cloudflare tunnel page>, then Ctrl+O, Enter, Ctrl+X
chmod 600 .env
```

### Using it
- Status: `docker compose ps` in `/mnt/user/appdata/girloffs`, or the Compose section of the Docker tab
- Logs: `docker logs -f girloffs` (poller), `docker logs girloffs-cloudflared` (tunnel; healthy = 4× "Registered tunnel connection")
- Commands: `docker exec girloffs python -m app.manage list` (all commands from the table above work this way)
- Database: `/mnt/user/appdata/girloffs/data/girloffs.db`. Stop the stack and delete it to start over from `event.py`.
- Allow another outbound host (e.g. for a new feature): add a line to `egress/allowlist` and rebuild.
