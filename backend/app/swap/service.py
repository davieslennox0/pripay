"""Sui swap flow (brief §10 + §12 step 9): quote a route via the configured
SwapVenue, then execute it through the TEE — same trust boundary as a send
(PIN verification + signing/relaying happen behind the enclave), just with a
swap's unsigned tx in place of a transfer's. No platform fee here (brief §7:
swap gas comes out of the sent amount, not charged on top)."""

from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SwapQuote, SwapRecord
from app.pin import service as pin_service
from app.swap import get_swap_venue
from app.tee import get_tee_executor
from app.tee.schemas import SwapRequest


def _bigint(value: str) -> int:
    return int(str(value).removesuffix("n"))


def quote(
    db: Session, sui_address: str, coin_in_type: str, coin_out_type: str, amount_in: str
) -> tuple[SwapQuote, dict]:
    venue = get_swap_venue()
    route = venue.quote(coin_in_type, coin_out_type, amount_in)

    amount_out = _bigint(route["coinOut"]["amount"])
    amount_out_min = int(amount_out * (1 - settings.swap_default_slippage))

    record = SwapQuote(
        sui_address=sui_address,
        coin_in_type=coin_in_type,
        coin_out_type=coin_out_type,
        amount_in=str(amount_in),
        amount_out_min=str(amount_out_min),
        route_json=json.dumps(route),
    )
    db.add(record)
    db.commit()
    return record, route


def execute(
    db: Session, sui_address: str, quote_id: int, pin: str, slippage: float | None = None
) -> SwapRecord:
    quoted = db.get(SwapQuote, quote_id)
    if quoted is None or quoted.sui_address != sui_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Swap quote not found")
    if quoted.used:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quote already used")

    venue = get_swap_venue()
    unsigned_tx = venue.build_transaction(
        sui_address, json.loads(quoted.route_json), slippage or settings.swap_default_slippage
    )

    request = SwapRequest(
        sui_address=sui_address,
        coin_in_type=quoted.coin_in_type,
        coin_out_type=quoted.coin_out_type,
        amount_in=quoted.amount_in,
        amount_out_min=quoted.amount_out_min,
        unsigned_tx=json.dumps(unsigned_tx),
        pin=pin,
    )

    tee = get_tee_executor()
    sealed = tee.seal_swap(request)
    # Only mark the quote used once the PIN has actually checked out inside
    # the enclave — a wrong PIN must not burn the quote (brief §6: PIN
    # required for swaps, but mistyping it shouldn't force a re-quote).
    result = tee.execute_swap(
        sealed,
        pin_verifier=lambda addr, p: pin_service.verify_pin(db, addr, p),
    )
    quoted.used = True
    db.commit()

    record = SwapRecord(
        sui_address=sui_address,
        coin_in_type=quoted.coin_in_type,
        coin_out_type=quoted.coin_out_type,
        amount_in=quoted.amount_in,
        amount_out_min=quoted.amount_out_min,
        status=result.status,
        tx_ref=result.tx_ref,
        tee_provider=result.attestation.provider,
        tee_attestation=result.attestation.request_digest,
    )
    db.add(record)
    db.commit()
    return record


def list_swaps(db: Session, sui_address: str) -> list[SwapRecord]:
    stmt = select(SwapRecord).where(SwapRecord.sui_address == sui_address)
    return list(db.scalars(stmt))
