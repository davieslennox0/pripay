"""Minimal Python SDK for the Umbra AI agent API (brief §9).

    from umbra_sdk import UmbraClient

    client = UmbraClient(api_key="...", base_url="https://api.umbra.example")
    result = client.send(handle="bob@x.com", platform="email", amount=5.0)

Zero dependencies beyond the standard library, so it drops into any agent
runtime without forcing a `requests` pin.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class UmbraApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"Umbra API error {status}: {detail}")
        self.status = status
        self.detail = detail


class UmbraClient:
    def __init__(self, api_key: str, base_url: str = "https://api.umbra.example"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def send(self, handle: str, platform: str, amount: float, token: str = "USDC") -> dict:
        """Sends `amount` of `token` to `handle` on `platform` (brief §9:
        umbra.send(handle, platform, amount, token)). Raises UmbraApiError
        on a 4xx/5xx — e.g. over the key's per-tx or daily cap, or a revoked
        key."""
        return self._post(
            "/agent/send",
            {"platform": platform, "handle": handle, "amount": amount, "token": token},
        )

    def _post(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body_text = exc.read()
            try:
                detail = json.loads(body_text).get("detail", exc.reason)
            except (json.JSONDecodeError, AttributeError):
                detail = exc.reason
            raise UmbraApiError(exc.code, detail) from exc
