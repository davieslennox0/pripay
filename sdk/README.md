# Umbra agent SDKs (brief §9)

Two minimal, zero-dependency clients for the Umbra AI agent API — a scoped,
revocable API key credential distinct from the human zkLogin session the
web app uses. Agent accounts still require a bound Sui address and pay the
same fee structure as a human send; the API key just substitutes for the
human session + transaction PIN, with per-transaction and daily-volume caps
as the safety mechanism instead.

## Getting a key

A human account holder creates a key from their own session (PIN-gated,
since issuing a money-moving credential is at least as sensitive as a
send):

```
POST /agent/keys
{ "label": "my-trading-bot", "max_tx_usdc": 50, "daily_volume_cap_usdc": 200, "pin": "1234" }
-> { "id": 1, "key": "<shown once>", "key_prefix": "...", "max_tx_usdc": 50, "daily_volume_cap_usdc": 200 }
```

Store the `key` value securely — it is never retrievable again, only its
hash is stored server-side. `max_tx_usdc` and `daily_volume_cap_usdc` are
enforced on every send from that key; revoke a leaked key any time via
`POST /agent/keys/{id}/revoke` (also PIN-gated).

## Python — `sdk/python/umbra_sdk.py`

```python
from umbra_sdk import UmbraClient

client = UmbraClient(api_key="...", base_url="https://api.umbra.example")
result = client.send(handle="bob@x.com", platform="email", amount=5.0)
```

## JavaScript — `sdk/js/umbra-sdk.js`

```js
import { UmbraClient } from "./umbra-sdk.js";

const client = new UmbraClient({ apiKey: "...", baseUrl: "https://api.umbra.example" });
const result = await client.send({ handle: "bob@x.com", platform: "email", amount: 5 });
```

Both raise/throw on a 4xx/5xx response — e.g. exceeding the key's
per-transaction or daily cap, or a revoked key. USDC is the only token
Umbra supports today; passing anything else for `token` is rejected rather
than silently ignored.
