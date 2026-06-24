"""Cross-chain receive aggregator (brief §8 + §12 step 8). `BridgeAggregator`
mirrors the TeeExecutor/WalrusClient pattern elsewhere in this app: swapping
LI.FI for deBridge, or adding Wormhole as a Sui-native fallback, means
implementing this interface, not touching app/receive/service.py.

LI.FI already lists Sui as a destination chain (chain key "SUI"), so the
brief's "Wormhole as a fallback for Sui-specific routes" isn't needed yet —
noted here in case that coverage regresses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from app.config import settings


class BridgeAggregator(ABC):
    name: str

    @abstractmethod
    def quote(
        self,
        from_chain: str,
        from_token: str,
        from_amount: str,
        from_address: str,
        to_sui_address: str,
    ) -> dict:
        """Raw aggregator quote: route, estimated output, and the
        transaction request the source-chain wallet signs to execute it."""

    @abstractmethod
    def status(self, from_tx_hash: str, tool: str, from_chain: str) -> dict:
        """Raw aggregator status for an in-flight or completed bridge tx."""


class LiFiAggregator(BridgeAggregator):
    """The real LI.FI testnet/mainnet HTTP API (https://li.quest/v1)."""

    name = "lifi"

    def quote(
        self,
        from_chain: str,
        from_token: str,
        from_amount: str,
        from_address: str,
        to_sui_address: str,
    ) -> dict:
        resp = requests.get(
            f"{settings.lifi_api_url}/quote",
            params={
                "fromChain": from_chain,
                "toChain": "SUI",
                "fromToken": from_token,
                "toToken": settings.sui_usdc_address,
                "fromAddress": from_address,
                "toAddress": to_sui_address,
                "fromAmount": from_amount,
                "integrator": settings.lifi_integrator,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def status(self, from_tx_hash: str, tool: str, from_chain: str) -> dict:
        resp = requests.get(
            f"{settings.lifi_api_url}/status",
            params={
                "txHash": from_tx_hash,
                "bridge": tool,
                "fromChain": from_chain,
                "toChain": "SUI",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
