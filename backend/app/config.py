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


settings = Settings()
