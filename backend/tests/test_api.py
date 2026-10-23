from fastapi.testclient import TestClient

from app import config, main


def test_state_is_cacheable_and_public(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "POLL_ENABLED", False)
    with TestClient(main.app) as client:
        r = client.get("/api/state", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=5, stale-if-error=86400"
    # sent even without an Origin header, because Cloudflare's cached copy is shared by every site that reads it
    assert r.headers["access-control-allow-origin"] == "*"
    assert r.headers["content-encoding"] == "gzip"
    assert len(r.json()["matches"]) == 22


def test_no_api_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "POLL_ENABLED", False)
    with TestClient(main.app) as client:
        assert client.get("/openapi.json").status_code == 404
