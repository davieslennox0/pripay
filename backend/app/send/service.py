import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SendRecord
from app.handles import service as handles_service
from app.pin import service as pin_service


def validate_send_amount(amount: float) -> float:
    """Mirrors revenue_vault.move's collect_fee exactly (brief §7) — kept
    in sync manually since this is a Python preview of an on-chain check."""
    if amount < settings.min_send_usdc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Minimum send is {settings.min_send_usdc} USDC"
        )
    return round(amount - settings.platform_fee_usdc, 6)


def quote(db: Session, platform: str, handle: str, amount: float) -> tuple[bool, float, float]:
    receiver_gets = validate_send_amount(amount)
    bound = handles_service.resolve_handle(db, platform, handle)
    return bound is not None, settings.platform_fee_usdc, receiver_gets


def execute(
    db: Session, sender_sui_address: str, platform: str, handle: str, amount: float, pin: str
) -> SendRecord:
    pin_service.verify_pin(db, sender_sui_address, pin)
    receiver_gets = validate_send_amount(amount)
    bound = handles_service.resolve_handle(db, platform, handle)

    record = SendRecord(
        sender_sui_address=sender_sui_address,
        recipient_platform=platform,
        recipient_handle=handle,
        amount=amount,
        fee=settings.platform_fee_usdc,
        receiver_gets=receiver_gets,
        status="",
    )

    if bound is not None:
        record.recipient_sui_address = bound.sui_address
        record.status = "settled_stub"
        record.tx_ref = _stub_submit_transfer(sender_sui_address, bound.sui_address, receiver_gets)
    else:
        record.status = "escrowed_stub"
        record.claim_token = secrets.token_urlsafe(24)

    db.add(record)
    db.commit()
    return record


def claim(db: Session, claim_token: str, claimer_sui_address: str) -> SendRecord:
    stmt = select(SendRecord).where(SendRecord.claim_token == claim_token)
    record = db.scalars(stmt).first()
    if record is None or record.status != "escrowed_stub":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already-claimed link")

    record.recipient_sui_address = claimer_sui_address
    record.status = "claimed_stub"
    db.commit()
    return record


def list_sent(db: Session, sender_sui_address: str) -> list[SendRecord]:
    stmt = select(SendRecord).where(SendRecord.sender_sui_address == sender_sui_address)
    return list(db.scalars(stmt))


def _stub_submit_transfer(sender: str, receiver: str, amount: float) -> str:
    """Stands in for calling revenue_vault::collect_fee + transferring the
    remainder on-chain. Real implementation needs: (1) the Move package
    deployed to testnet (Sui CLI install was deferred to another server),
    and (2) a tx signed via the zkLogin ZK proof, which needs the TEE/prover
    path the build order defers to step 6. Mirrors the brief's own "stub
    the TEE interface" pattern so the rest of the system isn't blocked.
    """
    print(f"[send] STUB on-chain transfer: {sender} -> {receiver} ({amount} USDC)")
    return f"stub-{secrets.token_hex(16)}"
