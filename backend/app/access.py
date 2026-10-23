"""Admin login. Cloudflare Access does the actual login (organizer emails + one-time code) and then sends
every request it lets through with a signed token. We check that signature against Cloudflare's public
keys too, so admin stays closed even if the Access setup in the dashboard is ever removed or misconfigured."""

import logging
from urllib.parse import urlsplit

import jwt
from fastapi import HTTPException, Request

from . import config

log = logging.getLogger("access")
_jwks = None


def _signing_keys():
    global _jwks
    if _jwks is None:
        # Cloudflare's public keys, fetched through the egress proxy and cached (refetched when they rotate)
        _jwks = jwt.PyJWKClient(f"https://{config.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs", timeout=10)
    return _jwks


def verify(token):
    """The email inside a valid Access token, or None."""
    if not (config.ACCESS_TEAM_DOMAIN and config.ACCESS_AUD):
        return None
    try:
        key = _signing_keys().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=config.ACCESS_AUD,
            issuer=f"https://{config.ACCESS_TEAM_DOMAIN}", options={"require": ["exp", "iat", "aud", "iss"]},
        )
    except jwt.PyJWTError as e:
        log.warning("admin request refused: %s", type(e).__name__)
        return None
    return claims.get("email")


def admin_email(request: Request):
    """FastAPI dependency for every admin route: returns who is logged in, or refuses with 403."""
    if config.ACCESS_TEAM_DOMAIN or config.ACCESS_AUD:
        email = verify(request.headers.get("Cf-Access-Jwt-Assertion", ""))
    else:
        email = config.DEV_ADMIN_EMAIL  # local testing only; ignored as soon as either Access setting exists
    if not email:
        raise HTTPException(403, "not logged in")
    if request.method != "GET":
        # changes must come from the admin page itself, not from another site the organizer has open
        origin = request.headers.get("origin", "")
        if urlsplit(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "bad origin")
    return email
