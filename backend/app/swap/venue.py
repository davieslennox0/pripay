"""Sui swap venue (brief §10 + §12 step 9). `SwapVenue` mirrors the
BridgeAggregator/TeeExecutor/WalrusClient pattern used elsewhere in this app
— adding Uniswap (EVM), Jupiter (Solana), THORChain (cross-chain native), or
LI.FI/1inch as a meta-aggregator fallback (the other rows in brief §10's
table) means a new implementation of this interface, not a service rewrite.

Aftermath has no Python SDK — `aftermath-ts-sdk` is TS-only (the same gap
noted for Seal in app/storage/encryption.py) — but the REST API underneath
it is plain JSON, reachable directly with `requests`. The one quirk: amounts
that are BigInt in the TS SDK get serialized over the wire as `"<digits>n"`
strings; `_to_bigint_str` replicates that convention so Aftermath's backend
parses our requests the same way it parses the SDK's.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from app.config import settings


def _to_bigint_str(amount: str) -> str:
    return f"{amount}n"


class SwapVenue(ABC):
    name: str

    @abstractmethod
    def quote(self, coin_in_type: str, coin_out_type: str, amount_in: str) -> dict:
        """Best-price route (possibly multi-hop, multi-protocol) for
        swapping `amount_in` base units of coin_in_type into coin_out_type."""

    @abstractmethod
    def build_transaction(self, wallet_address: str, route: dict, slippage: float) -> str:
        """The unsigned transaction (base64) executing a previously quoted
        route, ready for the sender's wallet to sign."""


class AftermathSwapVenue(SwapVenue):
    name = "aftermath"

    def quote(self, coin_in_type: str, coin_out_type: str, amount_in: str) -> dict:
        resp = requests.post(
            f"{settings.aftermath_api_url}/router/trade-route",
            json={
                "coinInType": coin_in_type,
                "coinOutType": coin_out_type,
                "coinInAmount": _to_bigint_str(amount_in),
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def build_transaction(self, wallet_address: str, route: dict, slippage: float) -> str:
        resp = requests.post(
            f"{settings.aftermath_api_url}/router/transactions/trade",
            json={
                "walletAddress": wallet_address,
                "completeRoute": route,
                "slippage": slippage,
            },
            timeout=30,
        )
        resp.raise_for_status()
        # Real shape: a base64-encoded serialized Sui transaction, opaque to
        # us — passed straight through to the enclave/wallet to sign.
        return resp.json()
