"""Walrus blob storage (brief §5 + §12 step 7).

Walrus is content-addressed: a blob's id is derived from its bytes, so the
same ciphertext always maps to the same id. Both backends below honor that.
Neither ever sees plaintext — the record is already encrypted by the time it
reaches `store()` (see app/storage/encryption.py).
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from app.config import settings


class WalrusClient(ABC):
    backend: str

    @abstractmethod
    def store(self, ciphertext: bytes) -> str:
        """Upload an (already-encrypted) blob, return its blob id."""

    @abstractmethod
    def read(self, blob_id: str) -> bytes:
        """Fetch a blob's bytes by id (still ciphertext)."""


class LocalWalrusClient(WalrusClient):
    """Filesystem-backed stand-in for Walrus — content-addressed like the real
    thing (blob_id = sha256 of the bytes), so swapping in the HTTP backend
    doesn't change id semantics. Lets the whole encrypt -> store -> read ->
    decrypt path run offline and in tests."""

    backend = "local"

    def __init__(self) -> None:
        self._dir = Path(settings.walrus_local_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def store(self, ciphertext: bytes) -> str:
        blob_id = hashlib.sha256(ciphertext).hexdigest()
        (self._dir / blob_id).write_bytes(ciphertext)
        return blob_id

    def read(self, blob_id: str) -> bytes:
        path = self._dir / blob_id
        if not path.exists():
            raise FileNotFoundError(f"No Walrus blob {blob_id} in {self._dir}")
        return path.read_bytes()


class HttpWalrusClient(WalrusClient):
    """Real Walrus testnet via the public publisher/aggregator HTTP API.

    PUT {publisher}/v1/blobs?epochs=N -> JSON describing a newly created or
    already-certified blob; GET {aggregator}/v1/blobs/{id} -> the bytes.
    """

    backend = "http"

    def store(self, ciphertext: bytes) -> str:
        resp = requests.put(
            f"{settings.walrus_publisher_url}/v1/blobs",
            params={"epochs": settings.walrus_epochs},
            data=ciphertext,
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        # The publisher returns one of two shapes depending on whether this
        # exact blob was already stored by someone else.
        if "newlyCreated" in body:
            return body["newlyCreated"]["blobObject"]["blobId"]
        if "alreadyCertified" in body:
            return body["alreadyCertified"]["blobId"]
        raise RuntimeError(f"Unexpected Walrus publisher response: {body}")

    def read(self, blob_id: str) -> bytes:
        resp = requests.get(
            f"{settings.walrus_aggregator_url}/v1/blobs/{blob_id}", timeout=60
        )
        resp.raise_for_status()
        return resp.content
