"""Shapes for the multi-chain receive flow (brief §8)."""

from __future__ import annotations

from pydantic import BaseModel


class ReceiveChain(BaseModel):
    key: str
    name: str


class ReceiveQuoteRequest(BaseModel):
    from_chain: str  # LI.FI chain key, e.g. "ETH", "ARB", "BAS", "SOL"
    from_token: str  # token contract address on the source chain
    from_amount: str  # base-unit integer string, in the source token's decimals
    from_address: str  # the depositor's address on the source chain


class ReceiveQuoteResponse(BaseModel):
    record_id: int
    tool: str
    to_amount: str
    to_amount_min: str
    estimated_duration_seconds: int
    # The unsigned tx the depositor's source-chain wallet must sign + send to
    # actually execute the bridge. Umbra never holds or signs this.
    transaction_request: dict | None


class ReceiveSubmitRequest(BaseModel):
    from_tx_hash: str


class ReceiveStatusResponse(BaseModel):
    status: str
    sub_status: str | None
    sub_status_message: str | None
    receiving_tx_hash: str | None


class ReceiveRecordOut(BaseModel):
    record_id: int
    from_chain: str
    from_amount: str
    to_amount_min: str
    tool: str
    status: str
    receiving_tx_hash: str | None
