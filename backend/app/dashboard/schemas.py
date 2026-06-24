"""Shapes for the dashboard (brief §11)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BalanceOut(BaseModel):
    coin_type: str
    symbol: str | None
    balance: str  # base units, exact
    decimals: int | None
    amount: float | None  # human units, if decimals are known
    price_usd: float | None
    value_usd: float | None


class HistoryItem(BaseModel):
    kind: str  # "send" | "receive" | "swap"
    direction: str | None  # "out" | "in" | None (swaps have no direction)
    record_id: int
    counterparty: str | None
    status: str
    created_at: datetime
    # Whether `/dashboard/history/{record_id}/decrypt` has anything to show —
    # only Walrus-sealed send records do today.
    can_decrypt: bool


class HistoryDecrypted(BaseModel):
    amount: float
    token: str
    memo: str | None


class PersonalVolumeOut(BaseModel):
    total_sent: float
    total_received: float
    swap_count: int


class PlatformVolumeOut(BaseModel):
    total_volume: float
    total_fees: float
    send_count: int
