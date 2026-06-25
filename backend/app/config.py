import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_client_id: str = ""

    database_url: str = "sqlite:///./umbra.db"

    session_secret: str = secrets.token_hex(32)
    session_cookie_name: str = "umbra_session"
    session_ttl_minutes: int = 60 * 24 * 7

    frontend_origin: str = "http://localhost:5173"

    # PIN (brief §6): lock after this many consecutive failures, then back off.
    pin_max_attempts: int = 5
    pin_lockout_base_minutes: int = 1
    pin_lockout_max_minutes: int = 60
    # PIN reset (brief §6: "only resettable via zkLogin re-auth + cooldown
    # period") — separate from pin_lockout_*, which governs failed-attempt
    # backoff on the existing PIN, not a deliberate reset.
    pin_reset_cooldown_minutes: int = 10

    # Email magic-link handle binding (brief §1B). If smtp_host is unset, the
    # link is logged to the console instead of emailed — lets bind/verify be
    # tested locally before real SMTP credentials are configured.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@umbra.local"
    magic_link_base_url: str = "http://localhost:5173/verify-email"
    magic_link_ttl_minutes: int = 30

    # Fee spec (brief §7) — must match move-contracts/umbra/sources/revenue_vault.move
    # exactly (PLATFORM_FEE_BASE_UNITS / MIN_SEND_BASE_UNITS) since that contract
    # is the actual on-chain enforcement once settlement is no longer stubbed.
    platform_fee_usdc: float = 0.10
    min_send_usdc: float = 0.15

    # TEE execution layer (brief §4 + §12 step 6). Selects which TeeExecutor
    # the send path relays through. "mock" is the in-process simulated enclave
    # (app/tee/mock.py) — the build order explicitly starts here so the rest of
    # the system isn't blocked on the Nitro Enclaves / Oasis ROFL / Phala
    # infra decision (still an open flag in the brief). A real provider plugs
    # in behind the same TeeExecutor interface.
    tee_provider: str = "mock"
    # Stands in for the enclave image measurement (e.g. Nitro PCR0) that a
    # client/relayer pins before sealing a request to the enclave. The mock
    # echoes it back in its attestation so the attestation-verify path is
    # exercised end-to-end ahead of real attestation docs.
    tee_enclave_measurement: str = "mock-enclave-pcr0-0000000000000000"

    # Walrus encrypted-blob storage (brief §5 + §12 step 7). Walrus only ever
    # stores ciphertext — the record is encrypted (see record_encryption_key)
    # before upload.
    #   "local" — content-addressed filesystem store (walrus_local_dir),
    #             the default so the flow works offline / in tests.
    #   "http"  — real Walrus publisher/aggregator HTTP API (testnet URLs
    #             below). Same WalrusClient interface, config swap only.
    walrus_backend: str = "local"
    walrus_local_dir: str = "./_walrus_blobs"
    walrus_publisher_url: str = "https://publisher.walrus-testnet.walrus.space"
    walrus_aggregator_url: str = "https://aggregator.walrus-testnet.walrus.space"
    walrus_epochs: int = 1  # storage duration for the http backend

    # Record encryption key (32-byte hex) for the AES-256-GCM that protects
    # transaction records at rest in Walrus. This is the PLACEHOLDER for Seal
    # (brief §5): Seal's threshold/identity scheme scopes decryption to the
    # sender + receiver Sui addresses via key servers + seal_approve, and is
    # blocked on the same unpublished-package step as phases 4/5 (plus the
    # lack of a Python Seal SDK — real Seal-encrypt happens client/TEE-side in
    # TS). Until then this gives real confidentiality at rest using the same
    # sender||receiver identity binding, so the swap to Seal is localized to
    # app/storage/encryption.py. Auto-generated per process if unset (fine for
    # dev; set a stable key in prod or blobs become unreadable across restarts).
    record_encryption_key: str = secrets.token_hex(32)

    # Multi-chain receiving (brief §8 + §12 step 8). Umbra never custodies the
    # inbound funds — the aggregator quotes a route that lands USDC directly
    # at the user's own Sui address; the depositor's source-chain wallet signs
    # the relay tx LI.FI returns. "lifi" is the only aggregator wired up so
    # far (it already supports Sui as a destination chain); deBridge/Wormhole
    # can be added later behind the same BridgeAggregator interface.
    receive_aggregator: str = "lifi"
    lifi_api_url: str = "https://li.quest/v1"
    lifi_integrator: str = "umbra"
    # Native Circle USDC on Sui mainnet — the only landing token for MVP
    # (brief §8: "settles as USDC ... on Sui").
    sui_usdc_address: str = (
        "0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7::usdc::USDC"
    )

    # Swap module (brief §10 + §12 step 9). Aftermath is Sui-native and the
    # only venue wired up for MVP ("start with Aftermath since you're already
    # deep in Sui") — Uniswap (EVM) / Jupiter (Solana) / THORChain (native
    # cross-chain) / LI.FI-or-1inch (fallback) come later behind the same
    # SwapVenue interface. No Python SDK exists for Aftermath (same gap as
    # Seal) so this talks to its REST API directly, same approach as LI.FI.
    swap_venue: str = "aftermath"
    aftermath_api_url: str = "https://aftermath.finance/api"
    swap_default_slippage: float = 0.01

    # Dashboard (brief §11). Sui network matches the frontend's
    # VITE_SUI_NETWORK default (testnet — brief §12 step 4: "happy path on
    # testnet"). CoinGecko needs no key for the public simple-price endpoint.
    sui_rpc_url: str = "https://fullnode.testnet.sui.io:443"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"

    # AI agent API keys (brief §9 + §12 step 11). A scoped, revocable key
    # substitutes for both the human session and the PIN for agent-initiated
    # sends — these are the defaults applied when a key is created without
    # explicit overrides, not hard ceilings.
    agent_default_max_tx_usdc: float = 50.0
    agent_default_daily_cap_usdc: float = 200.0


settings = Settings()
