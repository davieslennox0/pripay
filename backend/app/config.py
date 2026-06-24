import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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


settings = Settings()
