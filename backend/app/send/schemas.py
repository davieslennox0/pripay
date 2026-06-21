from datetime import datetime

from pydantic import BaseModel


class SendQuoteRequest(BaseModel):
    platform: str
    handle: str
    amount: float


class SendQuoteResponse(BaseModel):
    is_bound: bool
    fee: float
    receiver_gets: float


class SendExecuteRequest(BaseModel):
    platform: str
    handle: str
    amount: float
    pin: str


class SendExecuteResponse(BaseModel):
    status: str
    receiver_gets: float
    claim_token: str | None
    tx_ref: str | None


class ClaimRequest(BaseModel):
    claim_token: str


class SendRecordOut(BaseModel):
    recipient_platform: str
    recipient_handle: str
    amount: float
    fee: float
    receiver_gets: float
    status: str
    created_at: datetime
