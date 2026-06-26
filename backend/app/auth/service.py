import json
import secrets
import subprocess
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SignInNonce

VERIFIER_SCRIPT = Path(__file__).resolve().parent.parent.parent / "verifier" / "verify.mjs"

SIGNIN_MESSAGE_TEMPLATE = "Sign in to Umbra\n\nNonce: {nonce}"


def signin_message(nonce: str) -> bytes:
    """The exact bytes a wallet must sign for a given nonce — built
    server-side from the nonce alone so a client can never substitute
    different message text for a nonce it didn't generate."""
    return SIGNIN_MESSAGE_TEMPLATE.format(nonce=nonce).encode()


def create_nonce(db: Session) -> str:
    nonce = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.signin_nonce_ttl_minutes)
    db.add(SignInNonce(nonce=nonce, expires_at=expires_at))
    db.commit()
    return nonce


def consume_nonce(db: Session, nonce: str) -> None:
    """One-time use: fetch + delete in the same call, so a nonce can never be
    redeemed twice (replay protection)."""
    record = db.get(SignInNonce, nonce)
    if record is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or already-used nonce")
    db.delete(record)
    db.commit()
    expires_at = record.expires_at
    if expires_at.tzinfo is None:  # SQLite drops tzinfo on round-trip; stored as UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nonce expired")


def verify_wallet_signature(message: bytes, signature: str, address: str) -> bool:
    """Verifies a Sui wallet signature over `message`, for either a plain
    keypair account or a zkLogin account (e.g. Slush's "Continue with
    Google" login) — both schemes are handled uniformly by `@mysten/sui`'s
    isValidPersonalMessageSignature. Python has no maintained Groth16/zkLogin
    verifier, so this shells out to the small Node helper in backend/verifier
    instead of reimplementing that cryptography here.
    """
    payload = {
        "message_b64": b64encode(message).decode(),
        "signature": signature,
        "address": address,
        "rpc_url": settings.sui_rpc_url,
    }
    try:
        result = subprocess.run(
            ["node", str(VERIFIER_SCRIPT)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Signature verification timed out"
        )

    if result.returncode != 0:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Signature verifier failed: {result.stderr.strip()}",
        )

    try:
        return bool(json.loads(result.stdout)["valid"])
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Signature verifier returned malformed output"
        )


def create_session_token(sui_address: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes)
    payload = {"sui_address": sui_address, "exp": expires_at}
    return jwt.encode(payload, settings.session_secret, algorithm="HS256")


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")


def require_session(
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> dict:
    """Shared auth dependency for any route that needs a logged-in user —
    PIN and handle-binding routes both depend on this rather than re-reading
    the cookie themselves."""
    if session_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return decode_session_token(session_token)
