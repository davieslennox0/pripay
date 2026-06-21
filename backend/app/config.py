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


settings = Settings()
