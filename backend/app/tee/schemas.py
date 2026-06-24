"""Data crossing the TEE boundary (brief §4).

`TransferRequest` is plaintext — it only ever exists *inside* the enclave (or
in the caller right before it's sealed). `SealedRequest` is what travels over
the wire: in the mock it's reversible base64 JSON, but it models the real
contract where the request is encrypted to the enclave's attested public key
so the plaintext amount + PIN never touch a regular server process.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TransferRequest:
    """The sender's PIN-protected transfer request. The enclave is the only
    place this is ever seen in the clear."""

    sender_sui_address: str
    recipient_platform: str
    recipient_handle: str
    # None when the handle isn't bound yet -> the enclave relays to escrow
    # instead of a direct transfer (§3 step 10).
    recipient_sui_address: str | None
    amount: float
    pin: str


@dataclass
class SealedRequest:
    """A `TransferRequest` encrypted to the enclave. Opaque to the regular
    server; only the enclave (real or mock) can open it."""

    provider: str
    # base64(ciphertext). In the mock this is reversible; a real Nitro/Phala
    # build replaces it with a hybrid-encrypted blob keyed to the attested
    # enclave public key.
    ciphertext: str


@dataclass
class TeeAttestation:
    """Proof the work ran inside the (claimed) enclave. A real attestation is
    a signed document chaining the enclave measurement to a hardware root of
    trust; the mock carries the same shape so the verify path is real."""

    provider: str
    enclave_measurement: str
    # Binds the attestation to this specific transfer so it can't be replayed
    # against a different record — sha256 over the request's settled outcome.
    request_digest: str
    signed_at: datetime


@dataclass
class TransferResult:
    """What the enclave returns after validating + signing/relaying. The
    plaintext PIN is deliberately absent — it never leaves the enclave."""

    status: str
    fee: float
    receiver_gets: float
    recipient_sui_address: str | None
    tx_ref: str | None
    claim_token: str | None
    attestation: TeeAttestation


@dataclass
class SwapRequest:
    """The sender's PIN-protected swap request (brief §10). `unsigned_tx` is
    the base64 transaction the swap venue (e.g. Aftermath) already built for
    `amount_in` of `coin_in_type` -> `coin_out_type` — opaque to the enclave,
    which only signs/relays it after the PIN checks out, the same trust
    boundary as a transfer."""

    sui_address: str
    coin_in_type: str
    coin_out_type: str
    amount_in: str  # base units, decimal string (exceeds float precision)
    amount_out_min: str
    unsigned_tx: str
    pin: str


@dataclass
class SwapResult:
    """What the enclave returns after signing/relaying a swap. No fee field —
    brief §7: swap gas comes out of the sent amount, no separate platform
    fee on top."""

    status: str
    tx_ref: str | None
    attestation: TeeAttestation


@dataclass
class AgentTransferRequest:
    """An agent-initiated transfer (brief §9). No PIN — the scoped, revocable
    API key already authorized this and had its caps checked (app/agent)
    before it ever gets sealed; the key *is* the credential here, by design
    ("instead of a human OAuth session"). Still re-validated against the fee
    spec inside the enclave exactly like a session-initiated transfer."""

    sender_sui_address: str
    recipient_platform: str
    recipient_handle: str
    recipient_sui_address: str | None
    amount: float
    agent_key_id: int


@dataclass
class AgentTransferResult:
    status: str
    fee: float
    receiver_gets: float
    recipient_sui_address: str | None
    tx_ref: str | None
    claim_token: str | None
    attestation: TeeAttestation
