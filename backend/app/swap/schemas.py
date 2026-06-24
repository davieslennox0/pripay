"""Shapes for the swap flow (brief §10)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SwapQuoteRequest(BaseModel):
    coin_in_type: str
    coin_out_type: str
    amount_in: str  # base units, decimal string


class SwapQuoteResponse(BaseModel):
    quote_id: int
    amount_in: str
    amount_out: str
    spot_price: float
    net_trade_fee_percentage: float


class SwapExecuteRequest(BaseModel):
    quote_id: int
    pin: str
    slippage: float | None = None  # defaults to settings.swap_default_slippage


class SwapExecuteResponse(BaseModel):
    status: str
    tx_ref: str | None
    tee_provider: str | None
    tee_attestation: str | None


class SwapRecordOut(BaseModel):
    coin_in_type: str
    coin_out_type: str
    amount_in: str
    amount_out_min: str
    status: str
    tx_ref: str | None
    created_at: datetime
