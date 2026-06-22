from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SendRecord
from app.handles import service as handles_service
from app.pin import service as pin_service
from app.tee import get_tee_executor
from app.tee.schemas import TransferRequest


def validate_send_amount(amount: float) -> float:
    """Quote-time preview of the fee check (brief §7). The *authoritative*
    enforcement happens inside the TEE (app/tee/mock.py::_validate), which
    re-derives this rather than trusting the host — this copy only powers the
    /send/quote preview, so the two are kept in sync manually."""
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
    """Assemble the transfer request, seal it, and hand it to the TEE (brief
    §4). PIN verification, fee re-validation, and signing/relaying all happen
    behind the enclave boundary — this function never sees the cleartext
    amount validated, never holds the signing path, and discards the PIN into
    the sealed envelope. It only persists the attested result."""
    bound = handles_service.resolve_handle(db, platform, handle)

    request = TransferRequest(
        sender_sui_address=sender_sui_address,
        recipient_platform=platform,
        recipient_handle=handle,
        recipient_sui_address=bound.sui_address if bound is not None else None,
        amount=amount,
        pin=pin,
    )

    tee = get_tee_executor()
    sealed = tee.seal(request)
    result = tee.execute_transfer(
        sealed,
        pin_verifier=lambda addr, p: pin_service.verify_pin(db, addr, p),
    )

    record = SendRecord(
        sender_sui_address=sender_sui_address,
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
    )
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
