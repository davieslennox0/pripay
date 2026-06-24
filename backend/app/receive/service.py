"""Multi-chain receiving (brief §8 + §12 step 8): quote an inbound bridge
from any supported source chain into USDC landing at the user's own Sui
address via the configured aggregator, then track it through to settlement.

Umbra never custodies the inbound funds or signs anything here — the
depositor's own source-chain wallet signs the `transactionRequest` the
aggregator returns; this module only quotes the route and polls its status.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import ReceiveRecord
from app.receive import get_aggregator

# MVP scope (brief §8): Sui + EVM (Ethereum/Base/Arbitrum) + Solana, keyed by
# the aggregator's chain identifiers.
SUPPORTED_CHAINS = {
    "ETH": "Ethereum",
    "ARB": "Arbitrum",
    "BAS": "Base",
    "SOL": "Solana",
}


def list_chains() -> list[dict]:
    return [{"key": key, "name": name} for key, name in SUPPORTED_CHAINS.items()]


def quote(
    db: Session,
    to_sui_address: str,
    from_chain: str,
    from_token: str,
    from_amount: str,
    from_address: str,
) -> tuple[ReceiveRecord, dict]:
    if from_chain not in SUPPORTED_CHAINS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported source chain '{from_chain}'. Supported: {', '.join(SUPPORTED_CHAINS)}",
        )

    raw = get_aggregator().quote(from_chain, from_token, from_amount, from_address, to_sui_address)
    estimate = raw["estimate"]

    record = ReceiveRecord(
        to_sui_address=to_sui_address,
        from_chain=from_chain,
        from_token=from_token,
        from_amount=from_amount,
        to_amount_min=estimate["toAmountMin"],
        tool=raw["tool"],
        quote_id=raw["id"],
        status="quoted",
    )
    db.add(record)
    db.commit()
    return record, raw


def mark_submitted(
    db: Session, record_id: int, to_sui_address: str, from_tx_hash: str
) -> ReceiveRecord:
    """Called once the depositor's source-chain wallet has broadcast the
    signed transactionRequest, so we know what to poll for settlement."""
    record = _get_owned(db, record_id, to_sui_address)
    record.from_tx_hash = from_tx_hash
    record.status = "pending"
    db.commit()
    return record


def refresh_status(db: Session, record_id: int, to_sui_address: str) -> tuple[ReceiveRecord, dict]:
    record = _get_owned(db, record_id, to_sui_address)
    if record.from_tx_hash is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No source-chain tx submitted yet")

    raw = get_aggregator().status(record.from_tx_hash, record.tool, record.from_chain)
    aggregator_status = raw["status"]
    if aggregator_status == "DONE":
        record.status = "settled"
        record.receiving_tx_hash = raw.get("receiving", {}).get("txHash")
    elif aggregator_status in ("FAILED", "INVALID", "NOT_FOUND"):
        record.status = "failed"
    db.commit()
    return record, raw


def list_received(db: Session, to_sui_address: str) -> list[ReceiveRecord]:
    stmt = select(ReceiveRecord).where(ReceiveRecord.to_sui_address == to_sui_address)
    return list(db.scalars(stmt))


def _get_owned(db: Session, record_id: int, to_sui_address: str) -> ReceiveRecord:
    record = db.get(ReceiveRecord, record_id)
    if record is None or record.to_sui_address != to_sui_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receive record not found")
    return record
