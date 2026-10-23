import os
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "data/girloffs.db")
POLL_ENABLED = os.environ.get("POLL_ENABLED", "1") == "1"
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "10"))
MCSR_SEASON = os.environ.get("MCSR_SEASON") or None  # None = current season
SERVE_FRONTEND = os.environ.get("SERVE_FRONTEND", "1") == "1"
FRONTEND_DIR = os.environ.get("FRONTEND_DIR", str(Path(__file__).resolve().parents[2] / "frontend"))
FAKE_NOW = os.environ.get("FAKE_NOW")  # e.g. "2026-04-11T20:45:00Z", for replay testing only

# Admin panel login (Cloudflare Access). Empty values count as unset: compose passes "" for missing .env entries.
ACCESS_TEAM_DOMAIN = os.environ.get("ACCESS_TEAM_DOMAIN", "").strip() or None  # e.g. "myteam.cloudflareaccess.com"
ACCESS_AUD = os.environ.get("ACCESS_AUD", "").strip() or None                  # the Access application's AUD tag
DEV_ADMIN_EMAIL = os.environ.get("DEV_ADMIN_EMAIL", "").strip() or None        # local testing only, ignored when Access is set


def now():
    if FAKE_NOW:
        return datetime.fromisoformat(FAKE_NOW)
    return datetime.now(timezone.utc)
