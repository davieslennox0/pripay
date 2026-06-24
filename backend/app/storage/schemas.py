"""Shapes for the encrypted Walrus transaction record (brief §5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransactionRecord:
    """The sensitive fields encrypted before upload (brief §5: "encrypted
    amount, encrypted token type, encrypted memo"). Everything here becomes
    ciphertext — none of it is ever written to Walrus in the clear."""

    amount: float
    token: str
    memo: str | None


@dataclass
class StoredRecord:
    """The non-secret pointers kept after a record is stored. `record_hash`
    is the §5 "hash for audit/dispute purposes" — sha256 over the ciphertext,
    so a stored blob can be proven unmodified without decrypting it."""

    backend: str
    blob_id: str
    record_hash: str
    # sender||receiver hex — the Seal identity the blob is scoped to (matches
    # seal_policy_send.move and frontend seal.ts). Kept so the read path knows
    # which identity to authorize/decrypt under.
    seal_identity: str
