import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import access, config, main, mcsr

from conftest import RAIN

TEAM = "girloffs-test.cloudflareaccess.com"
AUD = "test-aud-tag"
ORIGIN = {"Origin": "http://testserver"}  # TestClient's host is "testserver"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "POLL_ENABLED", False)
    monkeypatch.setattr(config, "ACCESS_TEAM_DOMAIN", None)
    monkeypatch.setattr(config, "ACCESS_AUD", None)
    monkeypatch.setattr(config, "DEV_ADMIN_EMAIL", None)
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def dev_login(monkeypatch):
    monkeypatch.setattr(config, "DEV_ADMIN_EMAIL", "dev@example.com")


@pytest.fixture
def access_key(monkeypatch):
    """Pretend to be Cloudflare Access: our own key pair, served as the team's public keys."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "k1"}
    monkeypatch.setattr(config, "ACCESS_TEAM_DOMAIN", TEAM)
    monkeypatch.setattr(config, "ACCESS_AUD", AUD)
    monkeypatch.setattr(config, "DEV_ADMIN_EMAIL", "dev@example.com")  # must be ignored once Access is set
    monkeypatch.setattr(access, "_jwks", None)
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    return key


def token(key, **claims):
    now = int(time.time())
    body = {"email": "organizer@example.com", "aud": [AUD], "iss": f"https://{TEAM}", "iat": now, "exp": now + 600}
    return jwt.encode({**body, **claims}, key, algorithm="RS256", headers={"kid": "k1"})


def as_access(t):
    return {"Cf-Access-Jwt-Assertion": t}


def test_admin_is_closed_when_nothing_is_configured(client):
    for path in ("/admin", "/admin/admin.js", "/admin/api/state"):
        assert client.get(path).status_code == 403
    assert client.post("/admin/api/matches/5", json={"best_of": 5}, headers=ORIGIN).status_code == 403


def test_valid_access_token_logs_in(client, access_key):
    r = client.get("/admin/api/state", headers=as_access(token(access_key)))
    assert r.status_code == 200
    assert r.json()["email"] == "organizer@example.com"
    assert r.headers["cache-control"] == "no-store"


def test_bad_access_tokens_are_refused(client, access_key):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad = [
        "",
        "not-a-token",
        token(other_key),                                  # signed by someone else
        token(access_key, aud=["another-app"]),            # meant for a different Access application
        token(access_key, iss="https://evil.cloudflareaccess.com"),
        token(access_key, exp=int(time.time()) - 60),      # expired
        jwt.encode({"email": "x@example.com", "aud": [AUD], "iss": f"https://{TEAM}"}, None, algorithm="none",
                   headers={"kid": "k1"}),                 # unsigned
    ]
    for t in bad:
        assert client.get("/admin/api/state", headers=as_access(t)).status_code == 403
    # no token at all: the dev email is ignored because Access is configured
    assert client.get("/admin/api/state").status_code == 403


def test_edit_match_and_audit_log(client, dev_login):
    r = client.post("/admin/api/matches/5", json={"winner_override": 14, "forfeit": True}, headers=ORIGIN)
    assert r.status_code == 200
    assert r.json()["changed"] == {"winner_override": [None, 14], "forfeit": [0, 1]}
    data = client.get("/admin/api/state").json()
    m5 = next(m for m in data["state"]["matches"] if m["number"] == 5)
    assert m5["winner"] == 14 and m5["forfeit"]
    assert data["audit"][0]["email"] == "dev@example.com"
    assert data["audit"][0]["action"] == "match 5"


def test_changes_need_the_admin_page_as_origin(client, dev_login):
    body = {"best_of": 5}
    assert client.post("/admin/api/matches/5", json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/admin/api/matches/5", json=body).status_code == 403
    # a plain-text body (what a cross-site form could send) isn't accepted as JSON
    r = client.post("/admin/api/matches/5", content='{"best_of": 5}', headers={**ORIGIN, "Content-Type": "text/plain"})
    assert r.status_code == 422


def test_bad_values_are_refused_and_not_logged(client, dev_login):
    bad = [{"score_override": "2:1"}, {"best_of": 4}, {"winner_override": 99}, {"winner_override": True},
           {"scheduled_at": "tomorrow"}, {"forfeit": "yes"}, {"number": 3}]
    for body in bad:
        assert client.post("/admin/api/matches/5", json=body, headers=ORIGIN).status_code == 400, body
    assert client.post("/admin/api/matches/99", json={"best_of": 3}, headers=ORIGIN).status_code == 400
    assert client.post("/admin/api/games/123", json={"excluded": True}, headers=ORIGIN).status_code == 400
    assert client.get("/admin/api/state").json()["audit"] == []


def test_replace_player_looks_up_uuid(client, dev_login, monkeypatch):
    async def fake_lookup(http, name):
        return (RAIN, "rain_betwixt") if name.lower() == "rain_betwixt" else None
    monkeypatch.setattr(mcsr, "lookup_user", fake_lookup)

    body = {"mc_name": "RAIN_BETWIXT", "display_name": "rain", "pronouns": "", "twitch": ""}
    r = client.post("/admin/api/players/16", json=body, headers=ORIGIN)
    assert r.status_code == 200
    player = next(p for p in client.get("/admin/api/state").json()["state"]["players"] if p["seed"] == 16)
    assert (player["uuid"], player["mc_name"], player["display_name"]) == (RAIN, "rain_betwixt", "rain")

    # same account can't be two seeds; unknown names and hand-typed UUIDs are refused
    assert client.post("/admin/api/players/17", json={"mc_name": "rain_betwixt"}, headers=ORIGIN).status_code == 400
    assert client.post("/admin/api/players/17", json={"mc_name": "nobody_here"}, headers=ORIGIN).status_code == 400
    assert client.post("/admin/api/players/17", json={"uuid": RAIN}, headers=ORIGIN).status_code == 400
    assert client.post("/admin/api/players/17", json={"mc_name": "../../x"}, headers=ORIGIN).status_code == 400


def test_page_serves_only_its_own_files(client, dev_login):
    r = client.get("/admin")
    assert r.status_code == 200 and "Girloffs admin" in r.text
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert client.get("/admin/admin.js").status_code == 200
    assert client.get("/admin/admin.css").status_code == 200
    assert client.get("/admin/index.html").status_code == 404
    assert client.get("/admin/..%2Fmain.py").status_code == 404
