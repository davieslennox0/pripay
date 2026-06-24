"""AI agent API-key auth + scoped sends (brief §9). A capped, revocable key
substitutes for both the human session and the transaction PIN on an
agent-initiated send — the cap check here is the safety mechanism instead of
a PIN, since an autonomous agent can't be prompted for one interactively.
Agent sends still pay the same fee structure and get Walrus-sealed the same
way a session send does — no special-casing beyond the auth path itself.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import AgentApiKey, SendRecord, get_db
from app.handles import service as handles_service
from app.storage import store_record
from app.storage.schemas import TransactionRecord
from app.tee import get_tee_executor
from app.tee.schemas import AgentTransferRequest


def create_key(
    db: Session,
    sui_address: str,
    label: str,
    max_tx_usdc: float | None,
    daily_volume_cap_usdc: float | None,
) -> tuple[AgentApiKey, str]:
    raw_key = secrets.token_urlsafe(32)
    record = AgentApiKey(
        sui_address=sui_address,
        key_hash=_hash(raw_key),
        key_prefix=raw_key[:8],
        label=label,
        max_tx_usdc=max_tx_usdc or settings.agent_default_max_tx_usdc,
        daily_volume_cap_usdc=daily_volume_cap_usdc or settings.agent_default_daily_cap_usdc,
    )
    db.add(record)
    db.commit()
    return record, raw_key


def list_keys(db: Session, sui_address: str) -> list[AgentApiKey]:
    stmt = select(AgentApiKey).where(AgentApiKey.sui_address == sui_address)
    return list(db.scalars(stmt))


def revoke_key(db: Session, sui_address: str, key_id: int) -> None:
    key = db.get(AgentApiKey, key_id)
    if key is None or key.sui_address != sui_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    key.revoked = True
    db.commit()


def authenticate(db: Session, raw_key: str) -> AgentApiKey:
    key = db.scalars(select(AgentApiKey).where(AgentApiKey.key_hash == _hash(raw_key))).first()
    if key is None or key.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked API key")
    key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return key


def require_agent_key(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> AgentApiKey:
    """Auth dependency for agent-facing routes — `Authorization: Bearer
    <key>`, distinct from require_session's cookie-based auth (brief §9)."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    return authenticate(db, authorization.removeprefix("Bearer "))


def send(db: Session, key: AgentApiKey, platform: str, handle: str, amount: float, token: str) -> SendRecord:
    if token != "USDC":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only USDC is supported for sends")
    if amount > key.max_tx_usdc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Amount exceeds this key's per-transaction cap of {key.max_tx_usdc} USDC",
        )
    _check_daily_cap(db, key, amount)

    bound = handles_service.resolve_handle(db, platform, handle)

    request = AgentTransferRequest(
        sender_sui_address=key.sui_address,
        recipient_platform=platform,
        recipient_handle=handle,
        recipient_sui_address=bound.sui_address if bound is not None else None,
        amount=amount,
        agent_key_id=key.id,
    )

    tee = get_tee_executor()
    sealed = tee.seal_agent_transfer(request)
    result = tee.execute_agent_transfer(sealed)

    stored = store_record(
        key.sui_address,
        result.recipient_sui_address,
        TransactionRecord(amount=result.receiver_gets, token="USDC", memo=None),
    )

    record = SendRecord(
        sender_sui_address=key.sui_address,
        recipient_platform=platform,
        recipient_handle=handle,
        recipient_sui_address=result.recipient_sui_address,
        amount=amount,
        fee=result.fee,
        receiver_gets=result.receiver_gets,
        status=result.status,
        claim_token=result.claim_token,
        tx_ref=result.tx_ref,
        tee_provider=result.attestation.provider,
        tee_attestation=result.attestation.request_digest,
        walrus_backend=stored.backend,
        walrus_blob_id=stored.blob_id,
        record_hash=stored.record_hash,
        seal_identity=stored.seal_identity,
        agent_key_id=key.id,
    )
    db.add(record)
    db.commit()
    return record


def _check_daily_cap(db: Session, key: AgentApiKey, amount: float) -> None:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = select(SendRecord).where(
        SendRecord.agent_key_id == key.id, SendRecord.created_at >= since
    )
    spent_today = sum(r.amount for r in db.scalars(stmt))
    if spent_today + amount > key.daily_volume_cap_usdc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Daily volume cap of {key.daily_volume_cap_usdc} USDC exceeded for this key "
            f"({spent_today} USDC already sent in the last 24h)",
        )


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
