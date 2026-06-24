import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import PinCredential, PinResetToken

_hasher = PasswordHasher()


def is_set(db: Session, sui_address: str) -> bool:
    return db.get(PinCredential, sui_address) is not None


def set_pin(db: Session, sui_address: str, pin: str) -> None:
    """Sets or overwrites the PIN. Re-setting while locked out is blocked —
    brief §6 ties PIN reset to zkLogin re-auth, not a bypass for lockout."""
    credential = db.get(PinCredential, sui_address)
    if credential is not None and _is_locked(credential):
        raise HTTPException(status.HTTP_423_LOCKED, "PIN is locked — try again later")

    pin_hash = _hasher.hash(pin)
    if credential is None:
        db.add(PinCredential(sui_address=sui_address, pin_hash=pin_hash))
    else:
        credential.pin_hash = pin_hash
        credential.failed_attempts = 0
        credential.locked_until = None
    db.commit()


def verify_pin(db: Session, sui_address: str, pin: str) -> None:
    """Raises 401 on a wrong PIN, 423 if locked out, 400 if no PIN is set.
    Returns normally (no value) when the PIN is correct."""
    credential = db.get(PinCredential, sui_address)
    if credential is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No PIN set for this account")

    if _is_locked(credential):
        raise HTTPException(status.HTTP_423_LOCKED, "PIN is locked — try again later")

    try:
        _hasher.verify(credential.pin_hash, pin)
    except VerifyMismatchError:
        _record_failure(db, credential)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect PIN")

    credential.failed_attempts = 0
    credential.locked_until = None
    db.commit()


def request_reset(
    db: Session, sui_address: str, expected_google_sub: str, id_token: str
) -> tuple[str, datetime]:
    """Step 1 of a PIN reset (brief §6) — requires a *fresh* Google re-auth,
    not just the existing session cookie, so a hijacked session alone can't
    reset the PIN. Works even while locked out (that's the whole point of a
    reset path); returns a token (+ when it unlocks) that only unlocks after
    a cooldown."""
    from app.auth.service import verify_google_id_token  # local import avoids an import cycle

    google_sub = verify_google_id_token(id_token)
    if google_sub != expected_google_sub:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Re-auth doesn't match the current session"
        )

    token = secrets.token_urlsafe(24)
    available_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.pin_reset_cooldown_minutes
    )
    db.add(PinResetToken(token=token, sui_address=sui_address, available_at=available_at))
    db.commit()
    return token, available_at


def confirm_reset(db: Session, token: str, new_pin: str) -> None:
    """Step 2, called after the cooldown — sets the new PIN and clears any
    lockout. Bypasses the locked-out check in `set_pin`: a fresh re-auth is
    a stronger signal than the lockout it's meant to clear."""
    reset = db.get(PinResetToken, token)
    if reset is None or reset.consumed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already-used reset token")

    available_at = reset.available_at
    if available_at.tzinfo is None:  # SQLite drops tzinfo on round-trip; stored as UTC
        available_at = available_at.replace(tzinfo=timezone.utc)
    if available_at > datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset cooldown hasn't elapsed yet")

    pin_hash = _hasher.hash(new_pin)
    credential = db.get(PinCredential, reset.sui_address)
    if credential is None:
        db.add(PinCredential(sui_address=reset.sui_address, pin_hash=pin_hash))
    else:
        credential.pin_hash = pin_hash
        credential.failed_attempts = 0
        credential.locked_until = None
    reset.consumed = True
    db.commit()


def _is_locked(credential: PinCredential) -> bool:
    locked_until = credential.locked_until
    if locked_until is None:
        return False
    # SQLite drops tzinfo on round-trip; values are always stored as UTC.
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > datetime.now(timezone.utc)


def _record_failure(db: Session, credential: PinCredential) -> None:
    credential.failed_attempts += 1
    if credential.failed_attempts >= settings.pin_max_attempts:
        overshoot = credential.failed_attempts - settings.pin_max_attempts
        lockout_minutes = min(
            settings.pin_lockout_base_minutes * (2**overshoot),
            settings.pin_lockout_max_minutes,
        )
        credential.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
    db.commit()
