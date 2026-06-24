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
    memo: str | None = None


class SendExecuteResponse(BaseModel):
    status: str
    receiver_gets: float
    claim_token: str | None
    tx_ref: str | None
    # Which enclave settled this send + the attestation digest it returned
    # (brief §4/§5). Lets the client show "settled in <provider> enclave".
    tee_provider: str | None
    tee_attestation: str | None
    # Walrus audit hash for the encrypted record (brief §5) — sha256 over the
    # ciphertext, provable without decrypting it.
    record_hash: str | None


class ClaimRequest(BaseModel):
    claim_token: str


class SendRecordOut(BaseModel):
    recipient_platform: str
    recipient_handle: str
    amount: float
    fee: float
    receiver_gets: float
    status: str
    record_hash: str | None
    created_at: datetime
