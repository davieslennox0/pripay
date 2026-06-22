"""The TEE executor interface (brief §4 + §12 step 6).

Everything from PIN verification through signing/relaying to Sui happens
behind this boundary, so the plaintext amount + handle mapping + PIN never
touch a regular server process. The send service only ever holds a
`SealedRequest` and a `TransferResult` — it cannot see the cleartext request.

A real provider (AWS Nitro Enclaves / Oasis ROFL / Phala — still an open
flag in the brief) implements the same two methods; swapping it in is a
config change (`settings.tee_provider`), not a send-flow rewrite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from app.tee.schemas import SealedRequest, TransferRequest, TransferResult

# (sui_address, pin) -> None on success, raises (HTTPException) on a wrong /
# locked / unset PIN. Injected so the enclave can verify the PIN against the
# stored Argon2id hash without the `tee` package importing the DB layer. In a
# real enclave this maps to PIN material released to the enclave only after a
# successful attestation handshake (e.g. Nitro KMS attestation), never to the
# host process.
PinVerifier = Callable[[str, str], None]


class TeeExecutor(ABC):
    #: Stable identifier surfaced in attestations and config (e.g. "mock",
    #: "nitro", "phala").
    provider: str

    @abstractmethod
    def seal(self, request: TransferRequest) -> SealedRequest:
        """Encrypt a plaintext request to the enclave. Runs on the caller
        side, before the request crosses the boundary."""

    @abstractmethod
    def execute_transfer(
        self, sealed: SealedRequest, pin_verifier: PinVerifier
    ) -> TransferResult:
        """Open the sealed request inside the enclave, verify the PIN,
        re-validate the transfer against the fee spec (never trusting the
        caller), sign + relay to Sui, and return a result with attestation."""
