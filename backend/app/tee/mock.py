"""In-process simulated enclave (brief §12 step 6: "start with a stub/mock
TEE interface so the rest of the system doesn't block on infra decisions").

This deliberately runs in the same process as the server — it is NOT a
security boundary. What it *is* faithful about is the control flow and the
trust model: the request is sealed before it crosses in, the enclave
re-validates everything rather than trusting the caller, the PIN is verified
and then discarded inside, and an attestation binds the signed outcome to the
enclave's measurement. A real provider keeps this exact shape but moves the
body into actual isolated/attested hardware.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.config import settings
from app.tee.base import PinVerifier, TeeExecutor
from app.tee.schemas import (
    SealedRequest,
    TeeAttestation,
    TransferRequest,
    TransferResult,
)


class MockTeeExecutor(TeeExecutor):
    provider = "mock"

    def seal(self, request: TransferRequest) -> SealedRequest:
        # Reversible stand-in for encrypting to the enclave's attested public
        # key. A real build replaces this with hybrid encryption; nothing else
        # in the send flow changes.
        blob = json.dumps(asdict(request)).encode()
        return SealedRequest(
            provider=self.provider,
            ciphertext=base64.b64encode(blob).decode(),
        )

    def execute_transfer(
        self, sealed: SealedRequest, pin_verifier: PinVerifier
    ) -> TransferResult:
        if sealed.provider != self.provider:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Sealed request is for provider '{sealed.provider}', not '{self.provider}'",
            )

        # ---- everything below is "inside the enclave" ----
        request = self._open(sealed)

        # 1. Verify the PIN (brief §4: "decrypting the sender's PIN-protected
        #    request"). The cleartext PIN exists only in this scope.
        pin_verifier(request.sender_sui_address, request.pin)

        # 2. Re-validate the transfer against the fee spec. The enclave is the
        #    authority — it never trusts an amount/fee computed by the host.
        fee, receiver_gets = self._validate(request.amount)

        # 3. Sign + relay to Sui. Still stubbed: the Move package isn't
        #    published yet (shared unblock step with phases 4 & 5), so there's
        #    no real zkLogin-signed tx to broadcast. The branching that a real
        #    enclave would do — direct transfer vs. escrow deposit — lives
        #    here, not in the host.
        if request.recipient_sui_address is not None:
            tx_ref = self._sign_and_relay_transfer(
                request.sender_sui_address, request.recipient_sui_address, receiver_gets
            )
            status_str = "settled_stub"
            claim_token = None
        else:
            tx_ref = self._sign_and_relay_escrow(
                request.sender_sui_address,
                request.recipient_platform,
                request.recipient_handle,
                receiver_gets,
            )
            status_str = "escrowed_stub"
            claim_token = secrets.token_urlsafe(24)

        attestation = self._attest(
            request, status_str, receiver_gets, tx_ref, claim_token
        )
        # `request` (and its PIN) goes out of scope here — never returned,
        # never logged.
        return TransferResult(
            status=status_str,
            fee=fee,
            receiver_gets=receiver_gets,
            recipient_sui_address=request.recipient_sui_address,
            tx_ref=tx_ref,
            claim_token=claim_token,
            attestation=attestation,
        )

    # --- enclave-internal helpers ---

    def _open(self, sealed: SealedRequest) -> TransferRequest:
        data = json.loads(base64.b64decode(sealed.ciphertext))
        return TransferRequest(**data)

    def _validate(self, amount: float) -> tuple[float, float]:
        """Authoritative copy of the fee check (brief §7). Intentionally does
        not reuse send/service.validate_send_amount: the enclave must not
        depend on host-side code for the rule it's enforcing."""
        if amount < settings.min_send_usdc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Minimum send is {settings.min_send_usdc} USDC",
            )
        receiver_gets = round(amount - settings.platform_fee_usdc, 6)
        return settings.platform_fee_usdc, receiver_gets

    def _sign_and_relay_transfer(self, sender: str, receiver: str, amount: float) -> str:
        # Real: build a PTB calling revenue_vault::collect_fee + transferring
        # the remainder, sign with the sender's zkLogin credential, broadcast.
        print(f"[tee:{self.provider}] STUB sign+relay transfer: {sender} -> {receiver} ({amount} USDC)")
        return f"stub-tx-{secrets.token_hex(16)}"

    def _sign_and_relay_escrow(
        self, sender: str, platform: str, handle: str, amount: float
    ) -> str:
        # Real: deposit into escrow::EscrowVault keyed by the same
        # hash(platform || normalized_handle) the on-chain modules use, so the
        # eventual claim resolves from the hash alone — plaintext handle never
        # goes on-chain.
        handle_hash = hashlib.sha256(f"{platform}:{handle}".encode()).hexdigest()
        print(
            f"[tee:{self.provider}] STUB sign+relay escrow deposit: {sender} -> "
            f"handle_hash {handle_hash[:16]}… ({amount} USDC)"
        )
        return f"stub-escrow-{secrets.token_hex(16)}"

    def _attest(
        self,
        request: TransferRequest,
        status_str: str,
        receiver_gets: float,
        tx_ref: str | None,
        claim_token: str | None,
    ) -> TeeAttestation:
        # Bind the attestation to the settled outcome (not the PIN) so it can't
        # be replayed against a different record.
        digest_material = json.dumps(
            {
                "sender": request.sender_sui_address,
                "platform": request.recipient_platform,
                "handle": request.recipient_handle,
                "status": status_str,
                "receiver_gets": receiver_gets,
                "tx_ref": tx_ref,
                "claim_token": claim_token,
            },
            sort_keys=True,
        ).encode()
        return TeeAttestation(
            provider=self.provider,
            enclave_measurement=settings.tee_enclave_measurement,
            request_digest=hashlib.sha256(digest_material).hexdigest(),
            signed_at=datetime.now(timezone.utc),
        )
