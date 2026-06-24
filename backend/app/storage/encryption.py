"""Record-at-rest encryption — the PLACEHOLDER for Seal (brief §5).

Seal is the intended scheme: threshold encryption where decryption is gated
by an identity-based access policy (seal_policy_send.move), so only the
sender or receiver Sui address can ever obtain a decryption key. That's
blocked on the same unpublished-Move-package step as phases 4/5, and there's
no Python Seal SDK (real Seal-encrypt is a client/TEE-side TS operation, see
frontend/src/lib/seal.ts).

Until then this provides *real* confidentiality at rest in Walrus with
AES-256-GCM, and — critically — uses the exact same identity construction as
Seal will: `sender_hex || receiver_hex` (matching seal.ts::addressToHex and
the BCS layout seal_policy_send::seal_approve reads). The identity is bound
into the ciphertext as GCM additional-authenticated-data, so a blob can't be
decrypted under, or relabeled to, a different (sender, receiver) pair. When
Seal is unblocked, only this module changes; the identity contract is already
right.

Caveat vs. real Seal: confidentiality here rests on a server/TEE-held
symmetric key, not on the sender/receiver's own keys — so it is NOT yet the
"only sender+receiver can decrypt" guarantee, just "not readable from the
Walrus blob alone." That gap closes when Seal lands.
"""

from __future__ import annotations

import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def seal_identity(sender_address: str, receiver_address: str | None) -> str:
    """sender||receiver as 32-byte hex halves (brief §5 scoping). For an
    unbound recipient (escrow), the receiver isn't known yet, so the record is
    scoped to the sender alone until a claim rebinds it."""
    receiver_address = receiver_address or sender_address
    return _to_hex(sender_address) + _to_hex(receiver_address)


def encrypt_record(
    sender_address: str, receiver_address: str | None, payload: dict
) -> tuple[bytes, str]:
    """Returns (ciphertext, seal_identity). Layout: 12-byte nonce || GCM
    ciphertext, with the identity bound in as AAD."""
    identity = seal_identity(sender_address, receiver_address)
    aesgcm = AESGCM(_key())
    nonce = os.urandom(12)  # GCM nonces must never repeat under the same key
    plaintext = json.dumps(payload, sort_keys=True).encode()
    ct = aesgcm.encrypt(nonce, plaintext, identity.encode())
    return nonce + ct, identity


def decrypt_record(
    sender_address: str, receiver_address: str | None, ciphertext: bytes
) -> dict:
    """Inverse of encrypt_record. The identity must match what the blob was
    sealed under (enforced by GCM via the AAD) or this raises."""
    identity = seal_identity(sender_address, receiver_address)
    aesgcm = AESGCM(_key())
    nonce, ct = ciphertext[:12], ciphertext[12:]
    plaintext = aesgcm.decrypt(nonce, ct, identity.encode())
    return json.loads(plaintext)


def _key() -> bytes:
    key = bytes.fromhex(settings.record_encryption_key)
    if len(key) != 32:
        raise ValueError("RECORD_ENCRYPTION_KEY must be 32 bytes (64 hex chars)")
    return key


def _to_hex(address: str) -> str:
    return address.removeprefix("0x").rjust(64, "0")
