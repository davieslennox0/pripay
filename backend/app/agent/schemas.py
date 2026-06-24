"""Shapes for AI agent API-key auth + sends (brief §9)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentKeyCreateRequest(BaseModel):
    label: str
    max_tx_usdc: float | None = None  # defaults to settings.agent_default_max_tx_usdc
    daily_volume_cap_usdc: float | None = None  # defaults to settings.agent_default_daily_cap_usdc
    pin: str  # creating a money-moving credential is at least as sensitive as a send


class AgentKeyCreateResponse(BaseModel):
    id: int
    key: str  # shown once — never retrievable again, only its hash is stored
    key_prefix: str
    max_tx_usdc: float
    daily_volume_cap_usdc: float


class AgentKeyOut(BaseModel):
    id: int
    label: str
    key_prefix: str
    max_tx_usdc: float
    daily_volume_cap_usdc: float
    revoked: bool
    created_at: datetime
    last_used_at: datetime | None


class AgentKeyRevokeRequest(BaseModel):
    pin: str


class AgentSendRequest(BaseModel):
    platform: str
    handle: str
    amount: float
    # Accepted for SDK signature symmetry (umbra.send(handle, platform,
    # amount, token)) — USDC is the only token this app deals in for MVP, so
    # anything else is rejected rather than silently ignored.
    token: str = "USDC"


class AgentSendResponse(BaseModel):
    status: str
    receiver_gets: float
    claim_token: str | None
    tx_ref: str | None
