import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import BoundHandle, EmailVerificationToken
from app.pin import service as pin_service

EMAIL_PLATFORM = "email"


def normalize_handle(platform: str, handle: str) -> str:
    return handle.strip().lstrip("@").lower()


def start_email_bind(db: Session, sui_address: str, email: str) -> None:
    token = secrets.token_urlsafe(24)
    db.add(
        EmailVerificationToken(
            token=token,
            sui_address=sui_address,
            email=email,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.magic_link_ttl_minutes),
        )
    )
    db.commit()
    _send_magic_link(email, token)


def confirm_email_bind(db: Session, token: str) -> BoundHandle:
    record = db.get(EmailVerificationToken, token)
    if record is None or record.consumed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already-used link")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:  # SQLite drops tzinfo on round-trip; stored as UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link has expired")

    bound = BoundHandle(
        sui_address=record.sui_address,
        platform=EMAIL_PLATFORM,
        handle_normalized=normalize_handle(EMAIL_PLATFORM, record.email),
        handle_display=record.email,
    )
    record.consumed = True
    db.add(bound)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This email is already bound to an account")
    return bound


def list_handles(db: Session, sui_address: str) -> list[BoundHandle]:
    stmt = select(BoundHandle).where(BoundHandle.sui_address == sui_address)
    return list(db.scalars(stmt))


def resolve_handle(db: Session, platform: str, handle: str) -> BoundHandle | None:
    """Exact-match lookup used by the send flow to decide bound-recipient
    (settle now) vs unbound-recipient (escrow until claimed) — distinct
    from search_handles, which does prefix matching for typeahead."""
    normalized = normalize_handle(platform, handle)
    stmt = select(BoundHandle).where(
        BoundHandle.platform == platform, BoundHandle.handle_normalized == normalized
    )
    return db.scalars(stmt).first()


def search_handles(db: Session, platform: str, query: str, limit: int = 10) -> list[BoundHandle]:
    normalized = normalize_handle(platform, query)
    stmt = (
        select(BoundHandle)
        .where(BoundHandle.platform == platform, BoundHandle.handle_normalized.startswith(normalized))
        .limit(limit)
    )
    return list(db.scalars(stmt))


def unbind_handle(db: Session, sui_address: str, platform: str, handle: str, pin: str) -> None:
    pin_service.verify_pin(db, sui_address, pin)

    normalized = normalize_handle(platform, handle)
    stmt = select(BoundHandle).where(
        BoundHandle.sui_address == sui_address,
        BoundHandle.platform == platform,
        BoundHandle.handle_normalized == normalized,
    )
    bound = db.scalars(stmt).first()
    if bound is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Handle not bound to this account")
    db.delete(bound)
    db.commit()


def _send_magic_link(email: str, token: str) -> None:
    link = f"{settings.magic_link_base_url}?token={token}"
    if not settings.smtp_host:
        print(f"[handles] SMTP not configured — magic link for {email}: {link}")
        return

    message = EmailMessage()
    message["Subject"] = "Confirm your email for Umbra"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(f"Click to confirm this email address:\n\n{link}")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
