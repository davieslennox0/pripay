"""Walrus encrypted-blob storage (brief §5 + §12 step 7). `get_walrus_client()`
mirrors `app.tee.get_tee_executor()` — the backend it returns is selected by
`settings.walrus_backend`, so swapping local-disk for the real testnet HTTP
API is a config change, not a code change.

`store_record`/`read_record`/`rebind_record` are the only entry points the
rest of the app should use — they keep encrypt-then-store (and the
record_hash/seal_identity bookkeeping) atomic so callers never handle raw
ciphertext.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

from app.config import settings
from app.storage.encryption import decrypt_record, encrypt_record
from app.storage.schemas import StoredRecord, TransactionRecord
from app.storage.walrus import HttpWalrusClient, LocalWalrusClient, WalrusClient

_CLIENTS: dict[str, type[WalrusClient]] = {
    LocalWalrusClient.backend: LocalWalrusClient,
    HttpWalrusClient.backend: HttpWalrusClient,
}


@lru_cache(maxsize=1)
def get_walrus_client() -> WalrusClient:
    try:
        return _CLIENTS[settings.walrus_backend]()
    except KeyError:
        raise ValueError(
            f"Unknown walrus_backend '{settings.walrus_backend}'. "
            f"Available: {', '.join(sorted(_CLIENTS))}"
        )


def store_record(
    sender_address: str, receiver_address: str | None, record: TransactionRecord
) -> StoredRecord:
    """Encrypt + upload a transaction record (brief §5)."""
    ciphertext, identity = encrypt_record(sender_address, receiver_address, record.__dict__)
    client = get_walrus_client()
    blob_id = client.store(ciphertext)
    return StoredRecord(
        backend=client.backend,
        blob_id=blob_id,
        record_hash=hashlib.sha256(ciphertext).hexdigest(),
        seal_identity=identity,
    )


def read_record(sender_address: str, receiver_address: str | None, blob_id: str) -> dict:
    """Fetch + decrypt a previously stored record. Raises if `blob_id` wasn't
    sealed under (sender_address, receiver_address)."""
    ciphertext = get_walrus_client().read(blob_id)
    return decrypt_record(sender_address, receiver_address, ciphertext)


def rebind_record(
    sender_address: str, old_blob_id: str, new_receiver_address: str
) -> StoredRecord:
    """Re-seal an escrow record (sealed under sender||sender, since the
    receiver wasn't known yet) to the real sender||receiver identity once a
    claim resolves it (see app/storage/encryption.py::seal_identity). Stores a
    new blob under the new identity; the old one is left as-is since Walrus
    blobs aren't mutated in place."""
    payload = read_record(sender_address, None, old_blob_id)
    return store_record(
        sender_address, new_receiver_address, TransactionRecord(**payload)
    )


__all__ = [
    "get_walrus_client",
    "store_record",
    "read_record",
    "rebind_record",
    "WalrusClient",
]
