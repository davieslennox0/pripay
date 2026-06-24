"""Dashboard aggregation (brief §11): live balance overview (Sui RPC +
CoinGecko), transaction history merged across send/receive/swap with
decrypt-on-view via the Seal placeholder (app.storage), and volume stats.
"""

from __future__ import annotations

from datetime import datetime

import requests
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ReceiveRecord, SendRecord, SwapRecord
from app.handles.service import normalize_handle
from app.storage import read_record

# The only coin types this app actually deals in (brief §8/§10 scope) get a
# live USD price; any other coin sitting in the wallet just shows its raw
# on-chain balance with no conversion.
_KNOWN_COINS = {
    "0x2::sui::SUI": {"symbol": "SUI", "decimals": 9, "coingecko_id": "sui"},
}


def _known_coins() -> dict:
    return {
        **_KNOWN_COINS,
        settings.sui_usdc_address: {"symbol": "USDC", "decimals": 6, "coingecko_id": "usd-coin"},
    }


def get_balances(sui_address: str) -> list[dict]:
    known = _known_coins()

    resp = requests.post(
        settings.sui_rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "suix_getAllBalances", "params": [sui_address]},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Sui RPC error: {body['error']}")

    coingecko_ids = [known[b["coinType"]]["coingecko_id"] for b in body["result"] if b["coinType"] in known]
    prices = _fetch_prices(coingecko_ids)

    balances = []
    for b in body["result"]:
        meta = known.get(b["coinType"])
        total = int(b["totalBalance"])
        amount = total / (10 ** meta["decimals"]) if meta else None
        price = prices.get(meta["coingecko_id"]) if meta else None
        balances.append(
            {
                "coin_type": b["coinType"],
                "symbol": meta["symbol"] if meta else None,
                "balance": b["totalBalance"],
                "decimals": meta["decimals"] if meta else None,
                "amount": amount,
                "price_usd": price,
                "value_usd": amount * price if amount is not None and price is not None else None,
            }
        )
    return balances


def _fetch_prices(coingecko_ids: list[str]) -> dict[str, float]:
    ids = sorted(set(coingecko_ids))
    if not ids:
        return {}
    resp = requests.get(
        f"{settings.coingecko_api_url}/simple/price",
        params={"ids": ",".join(ids), "vs_currencies": "usd"},
        timeout=10,
    )
    resp.raise_for_status()
    return {coin_id: data["usd"] for coin_id, data in resp.json().items()}


def get_history(
    db: Session,
    sui_address: str,
    platform: str | None = None,
    handle: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Merges send/receive/swap into one feed. A platform/handle filter only
    matches sends — receive and swap records have no handle to filter on, so
    supplying either narrows the feed to sends only."""
    items: list[dict] = []

    send_stmt = select(SendRecord).where(
        (SendRecord.sender_sui_address == sui_address)
        | (SendRecord.recipient_sui_address == sui_address)
    )
    if platform is not None:
        send_stmt = send_stmt.where(SendRecord.recipient_platform == platform)
    if handle is not None:
        normalized = normalize_handle(platform or "", handle)
        send_stmt = send_stmt.where(SendRecord.recipient_handle == normalized)
    if since is not None:
        send_stmt = send_stmt.where(SendRecord.created_at >= since)
    if until is not None:
        send_stmt = send_stmt.where(SendRecord.created_at <= until)
    for r in db.scalars(send_stmt):
        items.append(
            {
                "kind": "send",
                "direction": "out" if r.sender_sui_address == sui_address else "in",
                "record_id": r.id,
                "counterparty": f"{r.recipient_platform}:{r.recipient_handle}",
                "status": r.status,
                "created_at": r.created_at,
                "can_decrypt": r.walrus_blob_id is not None,
            }
        )

    if platform is None and handle is None:
        receive_stmt = select(ReceiveRecord).where(ReceiveRecord.to_sui_address == sui_address)
        if since is not None:
            receive_stmt = receive_stmt.where(ReceiveRecord.created_at >= since)
        if until is not None:
            receive_stmt = receive_stmt.where(ReceiveRecord.created_at <= until)
        for r in db.scalars(receive_stmt):
            items.append(
                {
                    "kind": "receive",
                    "direction": "in",
                    "record_id": r.id,
                    "counterparty": r.from_chain,
                    "status": r.status,
                    "created_at": r.created_at,
                    "can_decrypt": False,
                }
            )

        swap_stmt = select(SwapRecord).where(SwapRecord.sui_address == sui_address)
        if since is not None:
            swap_stmt = swap_stmt.where(SwapRecord.created_at >= since)
        if until is not None:
            swap_stmt = swap_stmt.where(SwapRecord.created_at <= until)
        for r in db.scalars(swap_stmt):
            items.append(
                {
                    "kind": "swap",
                    "direction": None,
                    "record_id": r.id,
                    "counterparty": r.coin_out_type,
                    "status": r.status,
                    "created_at": r.created_at,
                    "can_decrypt": False,
                }
            )

    items.sort(key=lambda i: i["created_at"], reverse=True)
    return items[offset : offset + limit]


def decrypt_history_item(db: Session, sui_address: str, record_id: int) -> dict:
    """Decrypt-on-view (brief §11) for a send record's Walrus blob — the only
    record kind that's actually Seal-sealed today (receive/swap don't
    persist amounts off-chain)."""
    record = db.get(SendRecord, record_id)
    owns = record is not None and sui_address in (
        record.sender_sui_address,
        record.recipient_sui_address,
    )
    if not owns:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found")
    if record.walrus_blob_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to decrypt for this record")

    return read_record(
        record.sender_sui_address, record.recipient_sui_address, record.walrus_blob_id
    )


def get_personal_volume(db: Session, sui_address: str) -> dict:
    sent = list(db.scalars(select(SendRecord).where(SendRecord.sender_sui_address == sui_address)))
    received = list(
        db.scalars(select(SendRecord).where(SendRecord.recipient_sui_address == sui_address))
    )
    swap_count = len(
        list(db.scalars(select(SwapRecord).where(SwapRecord.sui_address == sui_address)))
    )
    return {
        "total_sent": sum(r.amount for r in sent),
        "total_received": sum(r.receiver_gets for r in received),
        "swap_count": swap_count,
    }


def get_platform_volume(db: Session) -> dict:
    """Public growth stat (brief §11: "platform-wide aggregate ... if you
    want a growth stat publicly") — no auth required, intentionally not
    scoped to a caller."""
    sends = list(db.scalars(select(SendRecord)))
    return {
        "total_volume": sum(r.amount for r in sends),
        "total_fees": sum(r.fee for r in sends),
        "send_count": len(sends),
    }
