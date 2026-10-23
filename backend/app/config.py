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


def now():
    if FAKE_NOW:
        return datetime.fromisoformat(FAKE_NOW)
    return datetime.now(timezone.utc)
