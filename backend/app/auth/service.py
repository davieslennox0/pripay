import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import GoogleIdentity

_google_request = google_requests.Request()


def verify_google_id_token(token: str) -> str:
    """Verifies signature + claims against Google's JWKS and returns `sub`.

    Raises 401 on any verification failure — never trust a client-supplied
    sub/email without this check, since it determines the zkLogin salt
    lookup and therefore the derived Sui address.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "GOOGLE_CLIENT_ID is not configured on the backend",
        )
    try:
        claims = google_id_token.verify_oauth2_token(
            token, _google_request, settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid Google ID token: {exc}")

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unexpected token issuer")

    return claims["sub"]


def get_or_create_salt(db: Session, google_sub: str) -> str:
    """zkLogin requires a stable per-user salt to deterministically derive
    the same Sui address across logins. Once issued, this must never change
    for a given google_sub or the user loses access to their address."""
    identity = db.get(GoogleIdentity, google_sub)
    if identity is not None:
        return identity.salt

    salt = secrets.token_hex(16)
    db.add(GoogleIdentity(google_sub=google_sub, salt=salt))
    db.commit()
    return salt


def bind_sui_address(db: Session, google_sub: str, sui_address: str) -> None:
    identity = db.get(GoogleIdentity, google_sub)
    if identity is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No salt issued for this google_sub — call /auth/google/verify first",
        )
    identity.sui_address = sui_address
    db.commit()


def create_session_token(google_sub: str, sui_address: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes)
    payload = {"sub": google_sub, "sui_address": sui_address, "exp": expires_at}
    return jwt.encode(payload, settings.session_secret, algorithm="HS256")


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
